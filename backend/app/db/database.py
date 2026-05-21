from contextlib import asynccontextmanager
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from neo4j import GraphDatabase, AsyncGraphDatabase, AsyncDriver
import redis.asyncio as aioredis
from app.core.config import settings

# --- PostgreSQL Setup ---
engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)
async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)
Base = declarative_base()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

# --- Neo4j Setup ---
neo4j_driver: AsyncDriver = None

def get_neo4j_driver() -> AsyncDriver:
    global neo4j_driver
    if neo4j_driver is None:
        neo4j_driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )
    return neo4j_driver

async def close_neo4j_driver():
    global neo4j_driver
    if neo4j_driver is not None:
        await neo4j_driver.close()
        neo4j_driver = None

async def get_neo4j() -> AsyncGenerator[AsyncDriver, None]:
    driver = get_neo4j_driver()
    yield driver

# --- Redis Setup ---
redis_client: aioredis.Redis = None

def get_redis_client() -> aioredis.Redis:
    global redis_client
    if redis_client is None:
        redis_client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True
        )
    return redis_client

async def close_redis_client():
    global redis_client
    if redis_client is not None:
        await redis_client.close()
        redis_client = None

async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    client = get_redis_client()
    yield client
