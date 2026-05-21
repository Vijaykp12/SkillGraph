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
