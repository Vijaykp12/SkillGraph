import asyncio
import json
import logging
import httpx
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db, async_session
from app.models.models import User, UserProfile
from app.schemas.schemas import ChatRequest, ChatResponse, ChatMessage
from app.core.security import get_current_user
from jose import jwt
from app.core.config import settings
from app.ai.recommender import recommender

logger = logging.getLogger(__name__)
router = APIRouter()

def get_agent_response(user_message: str, profile_summary: str) -> str:
    """
    Agentic response builder matching user query against profile context.
    Simulates multi-agent reasoning.
    """
    msg = user_message.lower()
    
    if "twin" in msg or "simulate" in msg or "path" in msg:
        return (
            f"Based on your profile ({profile_summary}), I have initiated the Career Twin Simulator. "
            "I suggest target steps leading to your desired goal. If you are starting as a developer, "
            "a typical transition pathway goes: Developer -> Full-Stack Developer -> Machine Learning Engineer. "
            "I've updated your simulation tab with the latest transition momentum indicators!"
        )
    elif "gap" in msg or "skills" in msg or "dna" in msg:
        return (
            f"Analyzing your Skill DNA: I see you have solid foundational technical experience. "
            "However, you have gaps in Graph ML and Large Language Models. I highly recommend taking "
            "the 'Coursera: Graph Neural Networks in Practice' course to boost your score by 15%."
        )
    elif "salary" in msg or "market" in msg:
        return (
            "Looking at the labor market demand nodes in the graph: Machine Learning Engineers "
            "currently command a base salary of $135k+, with a high hiring index at companies like OpenAI and Google. "
            "Focusing on PyTorch and Kubernetes increases salary leverage by up to 22%."
        )
        
    return (
        f"Hello! I am your SkillGraph AI Career Coach. I analyzed your profile ({profile_summary}). "
        "I can help you simulate future career steps, run skill gap analyses, map your Skill DNA, "
        "and find the best courses. Try asking: 'What is my skill gap?' or 'Simulate a career path to ML Engineer'."
    )

async def call_gemini_non_stream(messages: list[ChatMessage], profile_summary: str, api_key: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    
    contents = []
    for msg in messages:
        role = "user" if msg.role == "user" else "model"
        if not msg.content.strip():
            continue
        if contents and contents[-1]["role"] == role:
            contents[-1]["parts"][0]["text"] += "\n" + msg.content
        else:
            contents.append({
                "role": role,
                "parts": [{"text": msg.content}]
            })
            
    system_instruction = (
        "You are the SkillGraph AI Career Coach, a premium, helpful career mentor. "
        "You help professionals analyze their Skill DNA, simulate career paths (e.g. from developer to ML engineer), "
        "calculate skill gaps, recommend learning resources, and explain salary trends. "
        f"The user's current profile details: {profile_summary}. "
        "Use this profile context to personalize all responses. "
        "Be encouraging, highly professional, and provide structured, actionable suggestions. "
        "Keep your formatting beautiful with markdown (bullet points, bold text)."
    )
    
    payload = {
        "contents": contents,
        "systemInstruction": {
            "parts": [{"text": system_instruction}]
        }
    }
    headers = {"Content-Type": "application/json"}
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers, timeout=30.0)
        response.raise_for_status()
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]

async def call_gemini_stream(messages: list[ChatMessage], profile_summary: str, api_key: str):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:streamGenerateContent?key={api_key}&alt=sse"
    
    contents = []
    for msg in messages:
        role = "user" if msg.role == "user" else "model"
        if not msg.content.strip():
            continue
        if contents and contents[-1]["role"] == role:
            contents[-1]["parts"][0]["text"] += "\n" + msg.content
        else:
            contents.append({
                "role": role,
                "parts": [{"text": msg.content}]
            })
            
    system_instruction = (
        "You are the SkillGraph AI Career Coach, a premium, helpful career mentor. "
        "You help professionals analyze their Skill DNA, simulate career paths (e.g. from developer to ML engineer), "
        "calculate skill gaps, recommend learning resources, and explain salary trends. "
        f"The user's current profile details: {profile_summary}. "
        "Use this profile context to personalize all responses. "
        "Be encouraging, highly professional, and provide structured, actionable suggestions. "
        "Keep your formatting beautiful with markdown (bullet points, bold text)."
    )
    
    payload = {
        "contents": contents,
        "systemInstruction": {
            "parts": [{"text": system_instruction}]
        }
    }
    headers = {"Content-Type": "application/json"}
    
    async with httpx.AsyncClient() as client:
        async with client.stream("POST", url, json=payload, headers=headers, timeout=30.0) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    try:
                        json_str = line[len("data: "):]
                        chunk_data = json.loads(json_str)
                        candidates = chunk_data.get("candidates", [])
                        if candidates:
                            content = candidates[0].get("content", {})
                            parts = content.get("parts", [])
                            if parts:
                                text_chunk = parts[0].get("text", "")
                                if text_chunk:
                                    yield text_chunk
                    except Exception:
                        continue

@router.post("/chat", response_model=ChatResponse)
async def chat_assistant(
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    HTTP POST route for chatbot queries.
    """
    res = await db.execute(select(UserProfile).where(UserProfile.user_id == current_user.id))
    profile = res.scalars().first()
    
    skills = profile.parsed_skills if profile else []
    occ = profile.current_occupation if profile else "Software Developer"
    target = profile.target_occupation if profile else "Data Scientist"
    profile_summary = f"Current: {occ}, Target: {target}, Skills: {', '.join(skills[:4])}"
    
    new_history = list(req.history)
    new_history.append(ChatMessage(role="user", content=req.message))
    
    if settings.GEMINI_API_KEY:
        try:
            bot_reply = await call_gemini_non_stream(new_history, profile_summary, settings.GEMINI_API_KEY)
        except Exception as e:
            logger.error(f"Error in Gemini non-stream call: {e}")
            bot_reply = f"Error: I had trouble communicating with my Gemini brain ({str(e)}). Please verify your API key."
    else:
        sim_reply = get_agent_response(req.message, profile_summary)
        bot_reply = f"[DEMO MODE: GEMINI_API_KEY not set - Showing Simulated Response]\n\n{sim_reply}"
        
    new_history.append(ChatMessage(role="assistant", content=bot_reply))
    
    return ChatResponse(response=bot_reply, history=new_history)

@router.websocket("/ws/chat")
async def websocket_chat_assistant(websocket: WebSocket):
    """
    WebSocket endpoint supporting token auth, session parsing,
    and live streaming from Gemini with session history.
    """
    await websocket.accept()
    
    try:
        # Step 1: Wait for auth handshake
        auth_data = await websocket.receive_text()
        token_payload = json.loads(auth_data)
        token = token_payload.get("token")
        
        # Verify JWT
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
        
        async with async_session() as db:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalars().first()
            if not user:
                await websocket.send_text(json.dumps({"error": "Unauthorized"}))
                await websocket.close()
                return
                
            res = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
            profile = res.scalars().first()
            
        skills = profile.parsed_skills if profile else []
        occ = profile.current_occupation if profile else "Software Developer"
        target = profile.target_occupation if profile else "Data Scientist"
        profile_summary = f"Current: {occ}, Target: {target}, Skills: {', '.join(skills[:4])}"
        
        await websocket.send_text(json.dumps({"status": "authenticated", "message": f"Connected as {user.full_name or user.email}"}))
        
        # Step 2: Chat loop with connection-level history
        chat_history = []
        while True:
            data = await websocket.receive_text()
            message_payload = json.loads(data)
            user_msg = message_payload.get("message", "")
            
            chat_history.append(ChatMessage(role="user", content=user_msg))
            
            if settings.GEMINI_API_KEY:
                try:
                    cumulative_text = ""
                    async for chunk in call_gemini_stream(chat_history, profile_summary, settings.GEMINI_API_KEY):
                        cumulative_text += chunk
                        await websocket.send_text(json.dumps({
                            "type": "chunk",
                            "content": cumulative_text,
                            "done": False
                        }))
                        await asyncio.sleep(0.01)
                        
                    # Send final completion chunk
                    await websocket.send_text(json.dumps({
                        "type": "chunk",
                        "content": cumulative_text,
                        "done": True
                    }))
                    chat_history.append(ChatMessage(role="assistant", content=cumulative_text))
                except Exception as e:
                    logger.error(f"Error in live Gemini stream: {e}")
                    error_msg = f"Error: I had trouble communicating with my Gemini brain ({str(e)}). Please verify your API key."
                    await websocket.send_text(json.dumps({
                        "type": "chunk",
                        "content": error_msg,
                        "done": True
                    }))
                    chat_history.append(ChatMessage(role="assistant", content=error_msg))
            else:
                # Fallback simulated response
                bot_reply = get_agent_response(user_msg, profile_summary)
                demo_reply = f"[DEMO MODE: GEMINI_API_KEY not set - Showing Simulated Response]\n\n{bot_reply}"
                
                # Stream response character by character to create realistic generative feel
                for i in range(1, len(demo_reply) + 1, 3):
                    chunk = demo_reply[:i]
                    await websocket.send_text(json.dumps({
                        "type": "chunk",
                        "content": chunk,
                        "done": False
                    }))
                    await asyncio.sleep(0.02)
                    
                # Final complete chunk
                await websocket.send_text(json.dumps({
                    "type": "chunk",
                    "content": demo_reply,
                    "done": True
                }))
                chat_history.append(ChatMessage(role="assistant", content=demo_reply))
                
    except WebSocketDisconnect:
        print("Chat WebSocket disconnected.")
    except Exception as e:
        try:
            await websocket.send_text(json.dumps({"error": f"Error: {e}"}))
            await websocket.close()
        except Exception:
            pass
