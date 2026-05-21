from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, JSON, Float
from sqlalchemy.orm import relationship
from app.db.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    role = Column(String, default="professional")  # professional, admin, recruiter
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    recommendations = relationship("LearningRecommendation", back_populates="user", cascade="all, delete-orphan")
    simulations = relationship("CareerTwinSimulation", back_populates="user", cascade="all, delete-orphan")

class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    bio = Column(String, nullable=True)
    resume_path = Column(String, nullable=True)
    parsed_skills = Column(JSON, default=list)  # list of skill strings parsed from resume
    parsed_experience = Column(JSON, default=list)  # list of jobs/roles parsed
    current_occupation = Column(String, nullable=True)
    target_occupation = Column(String, nullable=True)
    skills_dna = Column(JSON, default=dict)  # structured scoring of user skills
    
    user = relationship("User", back_populates="profile")

class LearningRecommendation(Base):
    __tablename__ = "learning_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    resource_name = Column(String, nullable=False)
    resource_url = Column(String, nullable=True)
    skill_target = Column(String, nullable=False)
    similarity_score = Column(Float, nullable=True)
    reason = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="recommendations")

class CareerTwinSimulation(Base):
    __tablename__ = "career_twin_simulations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    simulation_name = Column(String, nullable=False)
    path_sequence = Column(JSON, nullable=False)  # JSON representation of the transition nodes: [Occ1, Occ2, Occ3]
    skills_gap_sequence = Column(JSON, nullable=False)  # Skills required at each transition
    momentum_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="simulations")
