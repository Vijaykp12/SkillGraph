from typing import List, Dict, Optional, Any
from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    role: Optional[str] = "professional"

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: Optional[str] = None
    role: str
    is_active: bool

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenPayload(BaseModel):
    sub: Optional[str] = None

class ProfileUpdate(BaseModel):
    bio: Optional[str] = None
    current_occupation: Optional[str] = None
    target_occupation: Optional[str] = None
    parsed_skills: Optional[List[str]] = None

class ProfileResponse(BaseModel):
    user_id: int
    bio: Optional[str] = None
    current_occupation: Optional[str] = None
    target_occupation: Optional[str] = None
    parsed_skills: List[str]
    parsed_experience: List[Dict[str, Any]]
    skills_dna: Dict[str, float]

    class Config:
        from_attributes = True

class SkillItem(BaseModel):
    id: str
    name: str
    priority: float

class SkillGapRequest(BaseModel):
    target_occupation: str
    current_skills: Optional[List[str]] = None

class LearningResourcesRequest(BaseModel):
    target_occupation: Optional[str] = None
    current_skills: Optional[List[str]] = None

class SkillGapResponse(BaseModel):
    target_occupation: str
    match_score: float
    matching_skills: List[SkillItem]
    missing_skills: List[SkillItem]

class TwinSimRequest(BaseModel):
    start_occupation: str
    target_occupation: str

class PathStep(BaseModel):
    from_occupation: str
    to_occupation: str
    gap_percentage: float
    skills_to_learn: List[str]

class TwinSimResponse(BaseModel):
    start_occupation: str
    target_occupation: str
    path_sequence: List[PathStep]
    momentum_score: float
    total_steps: int

class ChatMessage(BaseModel):
    role: str  # user, assistant
    content: str

class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []

class ChatResponse(BaseModel):
    response: str
    history: List[ChatMessage]
