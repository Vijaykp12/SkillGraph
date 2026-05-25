import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl, field_validator

class Settings(BaseSettings):
    PROJECT_NAME: str = "SkillGraph API"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "supersecretkeychangeinproduction"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # CORS Origins
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000"
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str]:
        if isinstance(v, str):
            if not v.startswith("["):
                origins = [i.strip() for i in v.split(",")]
            else:
                import json
                origins = json.loads(v)
        elif isinstance(v, list):
            origins = v
        else:
            origins = []

        # Add dynamic GitHub Codespaces origins if environment details exist
        codespace_name = os.getenv("CODESPACE_NAME")
        port_domain = os.getenv("GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN", "app.github.dev")
        if codespace_name:
            origins.append(f"https://{codespace_name}-3000.{port_domain}")
            origins.append(f"https://{codespace_name}-8000.{port_domain}")
            origins.append(f"http://{codespace_name}-3000.{port_domain}")
            origins.append(f"http://{codespace_name}-8000.{port_domain}")
            
        return origins

    # Postgres Configurations
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "skillgraph"
    POSTGRES_PORT: str = "5432"
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        
    @property
    def SYNC_DATABASE_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Neo4j Configurations
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"

    # Redis Configurations
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    # AI Model & FAISS Configurations
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    FAISS_INDEX_PATH: str = "data/faiss_index.bin" # Binary File
    FAISS_METADATA_PATH: str = "data/faiss_metadata.pkl" # Pickle Object (Python -> Binary Object)
    
    # GNN Parameters
    GNN_HIDDEN_CHANNELS: int = 128
    GNN_OUT_CHANNELS: int = 64
    GNN_NUM_LAYERS: int = 2
    GNN_LEARNING_RATE: float = 0.001
    GNN_EPOCHS: int = 50
    GNN_BATCH_SIZE: int = 256
    GNN_MODEL_SAVE_PATH: str = "data/gnn_model.pt" # PyTorch Model Object
    
    # Gemini API Configuration
    GEMINI_API_KEY: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()
