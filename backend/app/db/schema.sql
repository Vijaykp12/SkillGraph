-- SkillGraph Database Schema (PostgreSQL)

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'professional',
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_profiles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    bio TEXT,
    resume_path VARCHAR(512),
    parsed_skills JSONB DEFAULT '[]'::jsonb,
    parsed_experience JSONB DEFAULT '[]'::jsonb,
    current_occupation VARCHAR(255),
    target_occupation VARCHAR(255),
    skills_dna JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS learning_recommendations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    resource_name VARCHAR(255) NOT NULL,
    resource_url VARCHAR(512),
    skill_target VARCHAR(255) NOT NULL,
    similarity_score DOUBLE PRECISION,
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS career_twin_simulations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    simulation_name VARCHAR(255) NOT NULL,
    path_sequence JSONB NOT NULL,
    skills_gap_sequence JSONB NOT NULL,
    momentum_score DOUBLE PRECISION DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
