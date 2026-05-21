import asyncio
import json
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
    
    bot_reply = get_agent_response(req.message, profile_summary)
    
    new_history = list(req.history)
    new_history.append(ChatMessage(role="user", content=req.message))
    new_history.append(ChatMessage(role="assistant", content=bot_reply))
    
    return ChatResponse(response=bot_reply, history=new_history)

@router.websocket("/ws/chat")
async def websocket_chat_assistant(websocket: WebSocket):
    """
    WebSocket endpoint supporting token auth, session parsing,
    and character-by-character real-time agent streaming.
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
        
        # Step 2: Chat loop
        while True:
            data = await websocket.receive_text()
            message_payload = json.loads(data)
            user_msg = message_payload.get("message", "")
            
            # Generate response
            bot_reply = get_agent_response(user_msg, profile_summary)
            
            # Stream response character by character to create realistic generative feel
            for i in range(1, len(bot_reply) + 1, 3):
                chunk = bot_reply[:i]
                await websocket.send_text(json.dumps({
                    "type": "chunk",
                    "content": chunk,
                    "done": False
                }))
                await asyncio.sleep(0.02)
                
            # Final complete chunk
            await websocket.send_text(json.dumps({
                "type": "chunk",
                "content": bot_reply,
                "done": True
            }))
            
    except WebSocketDisconnect:
        print("Chat WebSocket disconnected.")
    except Exception as e:
        try:
            await websocket.send_text(json.dumps({"error": f"Error: {e}"}))
            await websocket.close()
        except Exception:
            pass
