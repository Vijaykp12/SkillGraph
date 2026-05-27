from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db.database import Base, engine, close_neo4j_driver, close_redis_client
from app.api.endpoints import auth, skills, recommendations, assistant

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# CORS Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup DB Event
@app.on_event("startup")
async def startup_event():
    print("Starting up SkillGraph API Server...")
    # Automatically initialize SQL tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("PostgreSQL tables successfully verified/created.")

# Shutdown Event
@app.on_event("shutdown")
async def shutdown_event():
    print("Shutting down SkillGraph API Server...")
    await close_neo4j_driver()
    await close_redis_client()
    print("Database connections closed.")

# Include Endpoint Routers
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["Authentication"])
app.include_router(skills.router, prefix=f"{settings.API_V1_STR}/skills", tags=["Skills & Graph Explorer"])
app.include_router(recommendations.router, prefix=f"{settings.API_V1_STR}/recs", tags=["AI Recommendations"])
app.include_router(assistant.router, prefix=f"{settings.API_V1_STR}/assistant", tags=["Career Coach Chatbot"])

@app.get("/")
def read_root():
    return {"status": "online", "service": "SkillGraph Workforce Intelligence API"}

@app.get("/debug")
def debug_status():
    from app.ai.recommender import recommender
    from app.ai.embedder import embedder_instance
    import os
    
    cwd_files = os.listdir(".") if os.path.exists(".") else []
    data_files = os.listdir("data") if os.path.exists("data") else []
    
    return {
        "cwd": os.getcwd(),
        "cwd_files": cwd_files,
        "data_files": data_files,
        "recommender_model": str(recommender.model),
        "has_fused_embeddings": recommender.fused_embeddings is not None,
        "has_skill_map": recommender.skill_map is not None,
        "has_occ_map": recommender.occ_map is not None,
        "fused_embeddings_keys": list(recommender.fused_embeddings.keys()) if recommender.fused_embeddings else None,
        "occ_map_keys_count": len(recommender.occ_map["to_idx"]) if recommender.occ_map else 0,
        "skill_map_keys_count": len(recommender.skill_map["to_idx"]) if recommender.skill_map else 0,
        "embedder_has_index": embedder_instance.index is not None,
        "embedder_index_count": embedder_instance.index.ntotal if embedder_instance.index else 0,
        "embedder_metadata_count": len(embedder_instance.metadata) if embedder_instance.metadata else 0,
    }
