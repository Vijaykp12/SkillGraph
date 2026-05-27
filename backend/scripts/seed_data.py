import os
import sys
import pickle
import asyncio
import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add backend app to path to import config, database, models
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.config import settings
from app.db.database import get_neo4j_driver
from app.models.models import User, UserProfile
from app.core.security import get_password_hash
from sentence_transformers import SentenceTransformer
import faiss

# Rich seed datasets representing ESCO / O*NET taxonomy elements
SKILLS = [
    # Programming & Software
    {"id": "sk_python", "name": "Python", "type": "Language", "domain": "Software Development"},
    {"id": "sk_javascript", "name": "JavaScript", "type": "Language", "domain": "Web Development"},
    {"id": "sk_typescript", "name": "TypeScript", "type": "Language", "domain": "Web Development"},
    {"id": "sk_sql", "name": "SQL", "type": "Language", "domain": "Data Management"},
    {"id": "sk_rust", "name": "Rust", "type": "Language", "domain": "Systems Programming"},
    {"id": "sk_go", "name": "Go", "type": "Language", "domain": "Systems Programming"},
    {"id": "sk_cpp", "name": "C++", "type": "Language", "domain": "Systems Programming"},
    {"id": "sk_java", "name": "Java", "type": "Language", "domain": "Software Development"},
    {"id": "sk_csharp", "name": "C#", "type": "Language", "domain": "Software Development"},
    {"id": "sk_git", "name": "Git", "type": "Tool", "domain": "Version Control"},
    {"id": "sk_html_css", "name": "HTML & CSS", "type": "Language", "domain": "Frontend Development"},
    
    # Machine Learning & AI
    {"id": "sk_pytorch", "name": "PyTorch", "type": "Framework", "domain": "Artificial Intelligence"},
    {"id": "sk_tensorflow", "name": "TensorFlow", "type": "Framework", "domain": "Artificial Intelligence"},
    {"id": "sk_scikit_learn", "name": "Scikit-Learn", "type": "Library", "domain": "Machine Learning"},
    {"id": "sk_gnn", "name": "Graph Neural Networks", "type": "Concept", "domain": "Deep Learning"},
    {"id": "sk_nlp", "name": "Natural Language Processing", "type": "Concept", "domain": "Artificial Intelligence"},
    {"id": "sk_transformers", "name": "Transformers", "type": "Concept", "domain": "Deep Learning"},
    {"id": "sk_llm", "name": "Large Language Models", "type": "Concept", "domain": "Artificial Intelligence"},
    {"id": "sk_cv", "name": "Computer Vision", "type": "Concept", "domain": "Artificial Intelligence"},
    {"id": "sk_mlops", "name": "MLOps", "type": "Concept", "domain": "Machine Learning"},
    {"id": "sk_huggingface", "name": "Hugging Face", "type": "Platform", "domain": "Artificial Intelligence"},
    {"id": "sk_deep_learning", "name": "Deep Learning", "type": "Concept", "domain": "Artificial Intelligence"},
    
    # Data & Database Architecture
    {"id": "sk_neo4j", "name": "Neo4j", "type": "Database", "domain": "Graph Technology"},
    {"id": "sk_postgres", "name": "PostgreSQL", "type": "Database", "domain": "Data Management"},
    {"id": "sk_redis", "name": "Redis", "type": "Database", "domain": "Caching"},
    {"id": "sk_faiss", "name": "FAISS", "type": "Library", "domain": "Vector Search"},
    {"id": "sk_mongodb", "name": "MongoDB", "type": "Database", "domain": "Data Management"},
    {"id": "sk_mysql", "name": "MySQL", "type": "Database", "domain": "Data Management"},
    {"id": "sk_elasticsearch", "name": "Elasticsearch", "type": "Search Engine", "domain": "Data Management"},
    {"id": "sk_spark", "name": "Apache Spark", "type": "Framework", "domain": "Data Engineering"},
    {"id": "sk_hadoop", "name": "Apache Hadoop", "type": "Framework", "domain": "Data Engineering"},
    {"id": "sk_snowflake", "name": "Snowflake", "type": "Database", "domain": "Data Engineering"},
    {"id": "sk_data_warehouse", "name": "Data Warehousing", "type": "Concept", "domain": "Data Engineering"},
    
    # DevOps & Infrastructure
    {"id": "sk_docker", "name": "Docker", "type": "Tool", "domain": "DevOps"},
    {"id": "sk_kubernetes", "name": "Kubernetes", "type": "Tool", "domain": "DevOps"},
    {"id": "sk_aws", "name": "AWS", "type": "Cloud Platform", "domain": "Cloud Engineering"},
    {"id": "sk_gcp", "name": "Google Cloud Platform", "type": "Cloud Platform", "domain": "Cloud Engineering"},
    {"id": "sk_azure", "name": "Microsoft Azure", "type": "Cloud Platform", "domain": "Cloud Engineering"},
    {"id": "sk_terraform", "name": "Terraform", "type": "Tool", "domain": "Infrastructure as Code"},
    {"id": "sk_ci_cd", "name": "CI/CD", "type": "Concept", "domain": "DevOps"},
    {"id": "sk_ansible", "name": "Ansible", "type": "Tool", "domain": "Configuration Management"},
    {"id": "sk_jenkins", "name": "Jenkins", "type": "Tool", "domain": "CI/CD"},
    {"id": "sk_prometheus", "name": "Prometheus", "type": "Tool", "domain": "Monitoring"},
    
    # Frontend Technologies & UX/UI
    {"id": "sk_react", "name": "React", "type": "Framework", "domain": "Frontend Development"},
    {"id": "sk_nextjs", "name": "Next.js", "type": "Framework", "domain": "Frontend Development"},
    {"id": "sk_vue", "name": "Vue.js", "type": "Framework", "domain": "Frontend Development"},
    {"id": "sk_angular", "name": "Angular", "type": "Framework", "domain": "Frontend Development"},
    {"id": "sk_svelte", "name": "Svelte", "type": "Framework", "domain": "Frontend Development"},
    {"id": "sk_tailwindcss", "name": "TailwindCSS", "type": "Framework", "domain": "Frontend Development"},
    {"id": "sk_framer_motion", "name": "Framer Motion", "type": "Library", "domain": "Frontend Development"},
    {"id": "sk_d3", "name": "D3.js", "type": "Library", "domain": "Data Visualization"},
    {"id": "sk_cytoscape", "name": "Cytoscape.js", "type": "Library", "domain": "Data Visualization"},
    {"id": "sk_figma", "name": "Figma", "type": "Tool", "domain": "UI/UX Design"},
    {"id": "sk_ui_ux", "name": "UI/UX Design", "type": "Concept", "domain": "Design"}
]

OCCUPATIONS = [
    {"id": "occ_ds", "name": "Data Scientist", "domain": "Data Science", "base_salary": 115000},
    {"id": "occ_mle", "name": "Machine Learning Engineer", "domain": "Artificial Intelligence", "base_salary": 135000},
    {"id": "occ_fsd", "name": "Full-Stack Developer", "domain": "Software Development", "base_salary": 105000},
    {"id": "occ_devops", "name": "DevOps Engineer", "domain": "Infrastructure", "base_salary": 118000},
    {"id": "occ_de", "name": "Data Engineer", "domain": "Data Engineering", "base_salary": 120000},
    {"id": "occ_ca", "name": "Cloud Architect", "domain": "Cloud Engineering", "base_salary": 145000},
    {"id": "occ_fed", "name": "Frontend Engineer", "domain": "Frontend Development", "base_salary": 98000},
    {"id": "occ_bed", "name": "Backend Engineer", "domain": "Backend Development", "base_salary": 110000},
    {"id": "occ_sys_eng", "name": "Systems Engineer", "domain": "Systems Programming", "base_salary": 112000},
    {"id": "occ_ai_res", "name": "AI Researcher", "domain": "Artificial Intelligence", "base_salary": 160000},
    {"id": "occ_pm", "name": "Product Manager", "domain": "Product Management", "base_salary": 125000},
    {"id": "occ_sec_eng", "name": "Security Engineer", "domain": "Cybersecurity", "base_salary": 130000},
    {"id": "occ_qa", "name": "QA Automation Engineer", "domain": "Quality Assurance", "base_salary": 90000},
    {"id": "occ_mobile", "name": "Mobile Developer", "domain": "Mobile Development", "base_salary": 108000},
    {"id": "occ_dba", "name": "Database Administrator", "domain": "Database Administration", "base_salary": 102000},
    {"id": "occ_designer", "name": "UI/UX Designer", "domain": "Design", "base_salary": 95000}
]

COMPANIES = [
    {"id": "com_google", "name": "Google", "industry": "Technology", "headquarters": "Mountain View, CA"},
    {"id": "com_deepmind", "name": "DeepMind", "industry": "Artificial Intelligence", "headquarters": "London, UK"},
    {"id": "com_openai", "name": "OpenAI", "industry": "Artificial Intelligence", "headquarters": "San Francisco, CA"},
    {"id": "com_meta", "name": "Meta", "industry": "Technology", "headquarters": "Menlo Park, CA"},
    {"id": "com_aws", "name": "Amazon Web Services", "industry": "Cloud Computing", "headquarters": "Seattle, WA"},
    {"id": "com_microsoft", "name": "Microsoft", "industry": "Technology", "headquarters": "Redmond, WA"}
]

CERTIFICATIONS = [
    {"id": "cert_aws_arch", "name": "AWS Certified Solutions Architect", "issuer": "Amazon", "level": "Associate"},
    {"id": "cert_cka", "name": "Certified Kubernetes Administrator", "issuer": "CNCF", "level": "Intermediate"},
    {"id": "cert_tf_dev", "name": "TensorFlow Developer Certificate", "issuer": "Google", "level": "Specialist"}
]

LEARNING_RESOURCES = [
    {"id": "lr_gnn_coursera", "name": "Coursera: Graph Neural Networks in Practice", "provider": "Coursera", "duration": "4 weeks"},
    {"id": "lr_fastapi_doc", "name": "FastAPI Official Documentation & Tutorial", "provider": "FastAPI Docs", "duration": "5 hours"},
    {"id": "lr_pyg_hands_on", "name": "PyTorch Geometric Hands-on Deep Learning", "provider": "YouTube/PyG", "duration": "8 hours"},
    {"id": "lr_nextjs_learn", "name": "Next.js App Router Course", "provider": "Vercel", "duration": "12 hours"},
    {"id": "lr_neo4j_academy", "name": "Neo4j Graph Academy: Cypher Fundamentals", "provider": "Neo4j", "duration": "10 hours"}
]

TECHNOLOGIES = [
    {"id": "tech_postgres", "name": "Postgres", "category": "RDBMS"},
    {"id": "tech_docker", "name": "Docker", "category": "Containerization"},
    {"id": "tech_neo4j", "name": "Neo4j Graph Database", "category": "GraphDB"},
    {"id": "tech_redis", "name": "Redis Memory Store", "category": "Cache"},
    {"id": "tech_pytorch", "name": "PyTorch Framework", "category": "ML Framework"},
    {"id": "tech_nextjs", "name": "Next.js Framework", "category": "Web Framework"}
]

# Structural Edge Connections for seeding the heterogeneous graph
EDGES = {
    "REQUIRES": [
        # (Occupation, Skill, Weight)
        ("occ_ds", "sk_python", 0.95), ("occ_ds", "sk_sql", 0.85), ("occ_ds", "sk_scikit_learn", 0.90),
        ("occ_ds", "sk_pytorch", 0.75), ("occ_ds", "sk_gnn", 0.40), ("occ_ds", "sk_nlp", 0.60),
        ("occ_mle", "sk_python", 0.95), ("occ_mle", "sk_pytorch", 0.95), ("occ_mle", "sk_tensorflow", 0.85),
        ("occ_mle", "sk_transformers", 0.90), ("occ_mle", "sk_docker", 0.70), ("occ_mle", "sk_kubernetes", 0.60),
        ("occ_fsd", "sk_javascript", 0.95), ("occ_fsd", "sk_typescript", 0.85), ("occ_fsd", "sk_react", 0.90),
        ("occ_fsd", "sk_nextjs", 0.80), ("occ_fsd", "sk_python", 0.70), ("occ_fsd", "sk_postgres", 0.80),
        ("occ_devops", "sk_docker", 0.95), ("occ_devops", "sk_kubernetes", 0.95), ("occ_devops", "sk_terraform", 0.90),
        ("occ_devops", "sk_aws", 0.85), ("occ_devops", "sk_ci_cd", 0.95),
        ("occ_de", "sk_python", 0.85), ("occ_de", "sk_sql", 0.95), ("occ_de", "sk_postgres", 0.90),
        ("occ_de", "sk_neo4j", 0.80), ("occ_de", "sk_redis", 0.75), ("occ_de", "sk_data_warehouse", 0.95),
        ("occ_ca", "sk_aws", 0.95), ("occ_ca", "sk_gcp", 0.85), ("occ_ca", "sk_kubernetes", 0.80),
        ("occ_ca", "sk_terraform", 0.85),
        ("occ_fed", "sk_javascript", 0.95), ("occ_fed", "sk_typescript", 0.90), ("occ_fed", "sk_react", 0.95),
        ("occ_fed", "sk_nextjs", 0.85), ("occ_fed", "sk_tailwindcss", 0.90), ("occ_fed", "sk_framer_motion", 0.60),
        ("occ_bed", "sk_python", 0.90), ("occ_bed", "sk_sql", 0.85), ("occ_bed", "sk_postgres", 0.90),
        ("occ_bed", "sk_redis", 0.80), ("occ_bed", "sk_docker", 0.75),
        # New occupations relationships
        ("occ_sys_eng", "sk_cpp", 0.95), ("occ_sys_eng", "sk_rust", 0.90), ("occ_sys_eng", "sk_go", 0.85), ("occ_sys_eng", "sk_docker", 0.70), ("occ_sys_eng", "sk_git", 0.80),
        ("occ_ai_res", "sk_python", 0.95), ("occ_ai_res", "sk_pytorch", 0.95), ("occ_ai_res", "sk_deep_learning", 0.95), ("occ_ai_res", "sk_transformers", 0.90), ("occ_ai_res", "sk_llm", 0.90),
        ("occ_pm", "sk_ui_ux", 0.70), ("occ_pm", "sk_figma", 0.60), ("occ_pm", "sk_git", 0.40),
        ("occ_sec_eng", "sk_python", 0.75), ("occ_sec_eng", "sk_docker", 0.80), ("occ_sec_eng", "sk_kubernetes", 0.80), ("occ_sec_eng", "sk_aws", 0.85), ("occ_sec_eng", "sk_azure", 0.80),
        ("occ_qa", "sk_python", 0.80), ("occ_qa", "sk_javascript", 0.80), ("occ_qa", "sk_git", 0.85), ("occ_qa", "sk_ci_cd", 0.80), ("occ_qa", "sk_jenkins", 0.80),
        ("occ_mobile", "sk_javascript", 0.85), ("occ_mobile", "sk_typescript", 0.80), ("occ_mobile", "sk_git", 0.85), ("occ_mobile", "sk_react", 0.85),
        ("occ_dba", "sk_sql", 0.95), ("occ_dba", "sk_postgres", 0.95), ("occ_dba", "sk_mysql", 0.90), ("occ_dba", "sk_redis", 0.80), ("occ_dba", "sk_mongodb", 0.80),
        ("occ_designer", "sk_ui_ux", 0.95), ("occ_designer", "sk_figma", 0.95), ("occ_designer", "sk_html_css", 0.70)
    ],
    "SIMILAR_TO": [
        # (Skill, Skill, Weight)
        ("sk_pytorch", "sk_tensorflow", 0.85),
        ("sk_javascript", "sk_typescript", 0.90),
        ("sk_nextjs", "sk_react", 0.95),
        ("sk_gnn", "sk_transformers", 0.75),
        ("sk_transformers", "sk_llm", 0.90),
        ("sk_nlp", "sk_transformers", 0.80),
        ("sk_neo4j", "sk_faiss", 0.60),
        ("sk_postgres", "sk_mongodb", 0.70),
        ("sk_docker", "sk_kubernetes", 0.85),
        ("sk_d3", "sk_cytoscape", 0.80)
    ],
    "LEARNED_WITH": [
        # (Skill, LearningResource)
        ("sk_gnn", "lr_gnn_coursera"),
        ("sk_python", "lr_fastapi_doc"),
        ("sk_pytorch", "lr_pyg_hands_on"),
        ("sk_gnn", "lr_pyg_hands_on"),
        ("sk_nextjs", "lr_nextjs_learn"),
        ("sk_react", "lr_nextjs_learn"),
        ("sk_neo4j", "lr_neo4j_academy")
    ],
    "PREREQUISITE_FOR": [
        # (Skill, Skill)
        ("sk_python", "sk_pytorch"),
        ("sk_python", "sk_scikit_learn"),
        ("sk_javascript", "sk_react"),
        ("sk_react", "sk_nextjs"),
        ("sk_typescript", "sk_nextjs"),
        ("sk_docker", "sk_kubernetes"),
        ("sk_pytorch", "sk_gnn"),
        ("sk_transformers", "sk_llm")
    ],
    "TRENDING_WITH": [
        # (Skill, Skill)
        ("sk_pytorch", "sk_llm"),
        ("sk_transformers", "sk_llm"),
        ("sk_rust", "sk_go"),
        ("sk_kubernetes", "sk_terraform")
    ],
    "DEMANDED_BY": [
        # (Company, Skill)
        ("com_google", "sk_python"), ("com_google", "sk_pytorch"), ("com_google", "sk_kubernetes"),
        ("com_deepmind", "sk_pytorch"), ("com_deepmind", "sk_gnn"), ("com_deepmind", "sk_transformers"),
        ("com_openai", "sk_pytorch"), ("com_openai", "sk_transformers"), ("com_openai", "sk_llm"),
        ("com_meta", "sk_python"), ("com_meta", "sk_pytorch"), ("com_meta", "sk_react"),
        ("com_aws", "sk_aws"), ("com_aws", "sk_kubernetes"),
        ("com_microsoft", "sk_typescript"), ("com_microsoft", "sk_react")
    ],
    "LEADS_TO": [
        # (Occupation, Occupation)
        ("occ_fed", "occ_fsd"),
        ("occ_bed", "occ_fsd"),
        ("occ_ds", "occ_mle"),
        ("occ_de", "occ_mle"),
        ("occ_devops", "occ_ca"),
        # New transition paths
        ("occ_designer", "occ_pm"),
        ("occ_qa", "occ_fsd"),
        ("occ_mobile", "occ_fsd"),
        ("occ_sys_eng", "occ_devops"),
        ("occ_bed", "occ_sec_eng")
    ],
    "USED_IN": [
        # (Skill, Technology)
        ("sk_postgres", "tech_postgres"),
        ("sk_docker", "tech_docker"),
        ("sk_neo4j", "tech_neo4j"),
        ("sk_redis", "tech_redis"),
        ("sk_pytorch", "tech_pytorch"),
        ("sk_nextjs", "tech_nextjs")
    ]
}

async def seed_postgres():
    print("Seeding PostgreSQL Database...")
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Check if admin user already exists
        result = await session.execute(select(User).where(User.email == "admin@skillgraph.ai"))
        user = result.scalars().first()
        
        if not user:
            # Create user
            admin_user = User(
                email="admin@skillgraph.ai",
                hashed_password=get_password_hash("admin123"),
                full_name="SkillGraph Administrator",
                role="admin",
                is_superuser=True
            )
            session.add(admin_user)
            await session.commit()
            
            # Create profile
            admin_profile = UserProfile(
                user_id=admin_user.id,
                bio="Workforce Intelligence System admin profile.",
                current_occupation="Data Scientist",
                target_occupation="Machine Learning Engineer",
                parsed_skills=["Python", "SQL", "Scikit-Learn"],
                parsed_experience=[
                    {"role": "Data Analyst", "years": 2, "company": "Stripe"}
                ],
                skills_dna={"Data Scientist": 2.5, "Machine Learning Engineer": 0.8, "Full-Stack Developer": 0.8, "Database Administrator": 1.0}
            )
            session.add(admin_profile)
            await session.commit()
            print("PostgreSQL seeded successfully!")
        else:
            print("PostgreSQL already seeded.")
            
    await engine.dispose()

async def seed_neo4j():
    print("Seeding Neo4j Knowledge Graph...")
    driver = get_neo4j_driver()
    
    async with driver.session() as session:
        # Clear database
        print("Clearing Neo4j state...")
        await session.run("MATCH (n) DETACH DELETE n")
        
        # Apply Cypher schema constraints/indexes
        schema_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend/app/db/neo4j_schema.cypher'))
        if os.path.exists(schema_file):
            print("Applying Neo4j constraints...")
            with open(schema_file, 'r') as f:
                queries = f.read().split(';')
                for q in queries:
                    q_clean = q.strip()
                    if q_clean and not q_clean.startswith("//"):
                        try:
                            await session.run(q_clean)
                        except Exception as e:
                            # Cypher constraints might raise if already present or in some cluster modes
                            print(f"Skipping cypher: {q_clean[:40]}... Detail: {e}")
        
        # Create Nodes
        print("Inserting Skill nodes...")
        for node in SKILLS:
            await session.run(
                "CREATE (s:Skill {id: $id, name: $name, type: $type, domain: $domain})",
                **node
            )
            
        print("Inserting Occupation nodes...")
        for node in OCCUPATIONS:
            await session.run(
                "CREATE (o:Occupation {id: $id, name: $name, domain: $domain, base_salary: $base_salary})",
                **node
            )
            
        print("Inserting Company nodes...")
        for node in COMPANIES:
            await session.run(
                "CREATE (c:Company {id: $id, name: $name, industry: $industry, headquarters: $headquarters})",
                **node
            )
            
        print("Inserting Certification nodes...")
        for node in CERTIFICATIONS:
            await session.run(
                "CREATE (cert:Certification {id: $id, name: $name, issuer: $issuer, level: $level})",
                **node
            )
            
        print("Inserting LearningResource nodes...")
        for node in LEARNING_RESOURCES:
            await session.run(
                "CREATE (lr:LearningResource {id: $id, name: $name, provider: $provider, duration: $duration})",
                **node
            )
            
        print("Inserting Technology nodes...")
        for node in TECHNOLOGIES:
            await session.run(
                "CREATE (tech:Technology {id: $id, name: $name, category: $category})",
                **node
            )
            
        # Create Edges
        print("Inserting REQUIRES relationships...")
        for u, v, w in EDGES["REQUIRES"]:
            await session.run(
                "MATCH (o:Occupation {id: $u}), (s:Skill {id: $v}) "
                "CREATE (o)-[:REQUIRES {weight: $w}]->(s)",
                u=u, v=v, w=w
            )
            
        print("Inserting SIMILAR_TO relationships...")
        for u, v, w in EDGES["SIMILAR_TO"]:
            # Make bidirectional relationships
            await session.run(
                "MATCH (s1:Skill {id: $u}), (s2:Skill {id: $v}) "
                "CREATE (s1)-[:SIMILAR_TO {weight: $w}]->(s2), (s2)-[:SIMILAR_TO {weight: $w}]->(s1)",
                u=u, v=v, w=w
            )
            
        print("Inserting LEARNED_WITH relationships...")
        for u, v in EDGES["LEARNED_WITH"]:
            await session.run(
                "MATCH (s:Skill {id: $u}), (r:LearningResource {id: $v}) "
                "CREATE (s)-[:LEARNED_WITH]->(r)",
                u=u, v=v
            )
            
        print("Inserting PREREQUISITE_FOR relationships...")
        for u, v in EDGES["PREREQUISITE_FOR"]:
            await session.run(
                "MATCH (s1:Skill {id: $u}), (s2:Skill {id: $v}) "
                "CREATE (s1)-[:PREREQUISITE_FOR]->(s2)",
                u=u, v=v
            )
            
        print("Inserting TRENDING_WITH relationships...")
        for u, v in EDGES["TRENDING_WITH"]:
            await session.run(
                "MATCH (s1:Skill {id: $u}), (s2:Skill {id: $v}) "
                "CREATE (s1)-[:TRENDING_WITH]->(s2), (s2)-[:TRENDING_WITH]->(s1)",
                u=u, v=v
            )
            
        print("Inserting DEMANDED_BY relationships...")
        for u, v in EDGES["DEMANDED_BY"]:
            # Ensure target skill exists before making edge
            await session.run(
                "MATCH (c:Company {id: $u}), (s:Skill {id: $v}) "
                "CREATE (c)-[:DEMANDED_BY]->(s)",
                u=u, v=v
            )
            
        print("Inserting LEADS_TO relationships...")
        for u, v in EDGES["LEADS_TO"]:
            await session.run(
                "MATCH (o1:Occupation {id: $u}), (o2:Occupation {id: $v}) "
                "CREATE (o1)-[:LEADS_TO]->(o2)",
                u=u, v=v
            )
            
        print("Inserting USED_IN relationships...")
        for u, v in EDGES["USED_IN"]:
            await session.run(
                "MATCH (s:Skill {id: $u}), (t:Technology {id: $v}) "
                "CREATE (s)-[:USED_IN]->(t)",
                u=u, v=v
            )
            
    await get_neo4j_driver().close()
    print("Neo4j knowledge graph seeded successfully!")

def build_faiss_embeddings():
    print("Generating Semantic Embeddings & FAISS Index...")
    os.makedirs(os.path.dirname(settings.FAISS_INDEX_PATH), exist_ok=True)
    
    # Initialize SentenceTransformer
    print(f"Loading transformer: {settings.EMBEDDING_MODEL_NAME}...")
    model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
    
    # Aggregate all skills & occupations
    elements = []
    # Add skills
    for s in SKILLS:
        elements.append({
            "id": s["id"],
            "name": s["name"],
            "type": "Skill",
            "text": f"Skill: {s['name']}. Category: {s['type']}. Domain: {s['domain']}."
        })
    # Add occupations
    for o in OCCUPATIONS:
        elements.append({
            "id": o["id"],
            "name": o["name"],
            "type": "Occupation",
            "text": f"Occupation: {o['name']}. Career Domain: {o['domain']}."
        })
        
    texts = [el["text"] for el in elements]
    embeddings = model.encode(texts, show_progress_bar=True)
    embeddings = np.array(embeddings).astype('float32')
    
    # Build FAISS Flat L2 Index
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)  # IndexFlatIP is inner product, which matches cosine similarity if vectors normalized
    
    # Normalize vectors for cosine similarity
    faiss.normalize_L2(embeddings)
    index.add(embeddings)
    
    # Save Index
    faiss.write_index(index, settings.FAISS_INDEX_PATH)
    
    # Save metadata mapping
    metadata = {i: el for i, el in enumerate(elements)}
    with open(settings.FAISS_METADATA_PATH, 'wb') as f:
        pickle.dump(metadata, f)
        
    print(f"FAISS index created successfully at {settings.FAISS_INDEX_PATH}. Index contains {index.ntotal} elements.")

async def main():
    # 1. PostgreSQL Seeding
    try:
        await seed_postgres()
    except Exception as e:
        print(f"Warning: PostgreSQL seeding failed ({e}). PostgreSQL must be running.")
        
    # 2. Neo4j Seeding
    try:
        await seed_neo4j()
    except Exception as e:
        print(f"Warning: Neo4j seeding failed ({e}). Neo4j must be running.")
        
    # 3. FAISS Embedding generation (standalone, doesn't need DBs running)
    try:
        build_faiss_embeddings()
    except Exception as e:
        print(f"Embedding/FAISS generation failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
