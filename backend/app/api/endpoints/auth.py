from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db, get_neo4j_driver
from app.models.models import User, UserProfile
from app.schemas.schemas import UserCreate, UserResponse, Token, ProfileResponse, ProfileUpdate
from app.core.security import get_password_hash, verify_password, create_access_token, get_current_user
from app.services.parser import parse_resume_pdf
from app.ai.recommender import recommender

router = APIRouter()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    """Registers a new user and creates an empty profile."""
    # Check if exists
    res = await db.execute(select(User).where(User.email == user_in.email))
    if res.scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered")
        
    hashed_pwd = get_password_hash(user_in.password)
    user = User(
        email=user_in.email,
        hashed_password=hashed_pwd,
        full_name=user_in.full_name,
        role=user_in.role or "professional"
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Create associated profile
    profile = UserProfile(
        user_id=user.id,
        parsed_skills=[],
        parsed_experience=[],
        skills_dna={}
    )
    db.add(profile)
    await db.commit()
    
    return user

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    """Performs OAuth2 password hashing and token generation."""
    res = await db.execute(select(User).where(User.email == form_data.username))
    user = res.scalars().first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {
        "access_token": create_access_token(user.id),
        "token_type": "bearer"
    }

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Retrieves current user details."""
    return current_user

@router.get("/profile", response_model=ProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves user profile containing skill sets and DNA mapping."""
    res = await db.execute(select(UserProfile).where(UserProfile.user_id == current_user.id))
    profile = res.scalars().first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

@router.put("/profile", response_model=ProfileResponse)
async def update_profile(
    profile_in: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Updates profile attributes and recalculates Skill DNA."""
    res = await db.execute(select(UserProfile).where(UserProfile.user_id == current_user.id))
    profile = res.scalars().first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
        
    if profile_in.bio is not None:
        profile.bio = profile_in.bio
    if profile_in.current_occupation is not None:
        profile.current_occupation = profile_in.current_occupation
    if profile_in.target_occupation is not None:
        profile.target_occupation = profile_in.target_occupation
    if profile_in.parsed_skills is not None:
        profile.parsed_skills = profile_in.parsed_skills
        # Recalculate DNA mapping based on new skills list
        profile.skills_dna = await recommender.get_skill_dna(profile_in.parsed_skills)

    await db.commit()
    await db.refresh(profile)
    return profile

@router.post("/resume/upload", response_model=ProfileResponse)
async def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Uploads a PDF resume, parses its text, updates current/target occupations,
    matches parsed skills, and generates the user's Skill DNA mapping.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF resumes are supported.")
        
    contents = await file.read()
    
    # Fetch all skill names from Neo4j database to pass to parser
    db_skills = []
    try:
        driver = get_neo4j_driver()
        async with driver.session() as session:
            result = await session.run("MATCH (s:Skill) RETURN s.name AS name")
            async for record in result:
                db_skills.append(record["name"])
    except Exception as e:
        print(f"Error querying Neo4j skills: {e}")
        
    parsed_data = parse_resume_pdf(contents, existing_skills=db_skills)
    
    res = await db.execute(select(UserProfile).where(UserProfile.user_id == current_user.id))
    profile = res.scalars().first()
    if not profile:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)
        
    profile.bio = parsed_data["bio"]
    profile.parsed_skills = parsed_data["parsed_skills"]
    profile.parsed_experience = parsed_data["parsed_experience"]
    profile.current_occupation = parsed_data["current_occupation"]
    profile.target_occupation = parsed_data["target_occupation"]
    
    # Calculate DNA score metrics
    profile.skills_dna = await recommender.get_skill_dna(parsed_data["parsed_skills"])
    
    await db.commit()
    await db.refresh(profile)
    return profile
