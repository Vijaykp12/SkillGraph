from fastapi import APIRouter, Depends, Query, HTTPException
from neo4j import AsyncDriver
from app.db.database import get_neo4j, get_db
from app.ai.embedder import embedder_instance
from app.models.models import User, UserProfile
from app.core.security import get_current_user
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

router = APIRouter()

@router.get("/search")
async def search_graph(
    q: str = Query(..., min_length=1),
    item_type: str = Query(None, description="Filter: Skill or Occupation"),
    limit: int = Query(15, ge=1, le=50)
):
    """
    Performs semantic vector search across skills and occupations using FAISS.
    """
    try:
        results = embedder_instance.search_similar(q, top_k=limit, item_type=item_type)
        return {"query": q, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Semantic search failed: {e}")

@router.get("/node/{node_id}")
async def get_node_details(node_id: str, driver: AsyncDriver = Depends(get_neo4j)):
    """
    Fetches detailed metadata and 1-hop connections for a specific node in Neo4j.
    """
    try:
        async with driver.session() as session:
            # Query node details
            query = """
            MATCH (n {id: $id})
            RETURN n as node, labels(n)[0] as label
            """
            result = await session.run(query, id=node_id)
            records = [record async for record in result]
            
            if not records:
                return get_mock_node_details(node_id)
                
            node_props = dict(records[0]["node"])
            node_label = records[0]["label"]
            
            related_jobs = []
            courses = []
            
            if node_label == "Skill":
                # Get related jobs (occupations requiring it)
                jobs_res = await session.run(
                    "MATCH (o:Occupation)-[:REQUIRES]->(s:Skill {id: $id}) RETURN o.id as id, o.name as name LIMIT 5",
                    id=node_id
                )
                async for rec in jobs_res:
                    related_jobs.append({"id": rec["id"], "name": rec["name"]})
                
                # Get courses
                courses_res = await session.run(
                    "MATCH (s:Skill {id: $id})-[:LEARNED_WITH]->(r:LearningResource) RETURN r.name as name, r.provider as provider, r.duration as duration LIMIT 5",
                    id=node_id
                )
                async for rec in courses_res:
                    courses.append({
                        "resource_name": f"{rec['provider']}: {rec['name']}",
                        "duration": rec["duration"],
                        "url": "https://cyber-academy.org"
                    })
                
                # Fallback if no courses found
                if not courses:
                    courses.append({
                        "resource_name": f"Coursera: Mastering {node_props.get('name')} and applications",
                        "duration": "12 hours",
                        "url": "https://cyber-academy.org"
                    })
            elif node_label == "Occupation":
                # Get required skills
                skills_res = await session.run(
                    "MATCH (o:Occupation {id: $id})-[r:REQUIRES]->(s:Skill) RETURN s.id as id, s.name as name, r.weight as weight LIMIT 10",
                    id=node_id
                )
                async for rec in skills_res:
                    related_jobs.append({"id": rec["id"], "name": rec["name"], "weight": rec["weight"] or 1.0})
                
                # Get transition paths
                trans_res = await session.run(
                    "MATCH (o:Occupation {id: $id})-[:LEADS_TO]->(target:Occupation) RETURN target.id as id, target.name as name LIMIT 5",
                    id=node_id
                )
                async for rec in trans_res:
                    courses.append({
                        "resource_name": f"Transition to {rec['name']}",
                        "duration": "Career Path",
                        "url": "#"
                    })
            
            return {
                "id": node_id,
                "name": node_props.get("name"),
                "type": node_label,
                "properties": node_props,
                "related_jobs": related_jobs,
                "courses": courses
            }
    except Exception as e:
        return get_mock_node_details(node_id)

@router.get("/explorer")
async def get_explorer_graph(
    center_id: str = Query(None, description="Focus node ID"),
    depth: int = Query(1, ge=1, le=2),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    driver: AsyncDriver = Depends(get_neo4j)
):
    """
    Returns nodes and edges layout for Next.js interactive Graph Visualizer.
    """
    try:
        async with driver.session() as session:
            if center_id:
                # Query sub-graph centered around focus node
                query = """
                MATCH (center {id: $id})
                MATCH path = (center)-[*1..2]-(m)
                RETURN path
                LIMIT 100
                """
                result = await session.run(query, id=center_id)
            else:
                # Get current user profile
                res_profile = await db.execute(select(UserProfile).where(UserProfile.user_id == current_user.id))
                profile = res_profile.scalars().first()
                
                user_node_ids = []
                user_node_names = []
                if profile:
                    for skill in profile.parsed_skills:
                        user_node_names.append(skill)
                        slug = skill.lower().strip().replace(" ", "_")
                        user_node_ids.append(slug)
                        user_node_ids.append(f"sk_{slug}")
                    if profile.current_occupation:
                        user_node_names.append(profile.current_occupation)
                        slug = profile.current_occupation.lower().strip().replace(" ", "_")
                        user_node_ids.append(slug)
                        user_node_ids.append(f"occ_{slug}")
                    if profile.target_occupation:
                        user_node_names.append(profile.target_occupation)
                        slug = profile.target_occupation.lower().strip().replace(" ", "_")
                        user_node_ids.append(slug)
                        user_node_ids.append(f"occ_{slug}")
                
                if user_node_ids:
                    # Query graph centered around user's own profile nodes
                    query = """
                    MATCH (n) WHERE n.id IN $user_node_ids OR n.name IN $user_node_names
                    OPTIONAL MATCH (n)-[r]-(m)
                    RETURN n, r, m
                    LIMIT 100
                    """
                    result = await session.run(query, user_node_ids=user_node_ids, user_node_names=user_node_names)
                else:
                    # Query overall core graph fallback
                    query = """
                    MATCH (n)-[r]->(m)
                    RETURN n, r, m
                    LIMIT 60
                    """
                    result = await session.run(query)
                
            records = [record async for record in result]
            if not records:
                return get_mock_explorer_graph(center_id)
                
            nodes = {}
            edges = []
            
            for rec in records:
                if "path" in rec:
                    path = rec["path"]
                    for node in path.nodes:
                        nodes[node["id"]] = {
                            "id": node["id"],
                            "name": node["name"],
                            "type": list(node.labels)[0]
                        }
                    for rel in path.relationships:
                        start_node = rel.nodes[0]
                        end_node = rel.nodes[1]
                        edges.append({
                            "id": f"edge_{rel.id}",
                            "source": start_node["id"],
                            "target": end_node["id"],
                            "type": rel.type
                        })
                else:
                    n = rec["n"]
                    m = rec["m"]
                    r = rec["r"]
                    if n:
                        nodes[n["id"]] = {"id": n["id"], "name": n["name"], "type": list(n.labels)[0]}
                    if m:
                        nodes[m["id"]] = {"id": m["id"], "name": m["name"], "type": list(m.labels)[0]}
                    if n and m and r:
                        edges.append({
                            "id": f"edge_{r.id}",
                            "source": n["id"],
                            "target": m["id"],
                            "type": r.type
                        })
                    
            return {
                "nodes": list(nodes.values()),
                "edges": edges
            }
    except Exception:
        return get_mock_explorer_graph(center_id)

def get_mock_node_details(node_id: str) -> dict:
    # Human-readable format matching seed data structure
    name = node_id.replace("sk_", "").replace("occ_", "").replace("_", " ").title()
    is_skill = node_id.startswith("sk_")
    node_type = "Skill" if is_skill else "Occupation"
    
    connections = []
    if is_skill:
        connections.append({"rel_type": "SIMILAR_TO", "target_id": "sk_python", "target_name": "Python", "target_type": "Skill", "weight": 0.8})
        connections.append({"rel_type": "PREREQUISITE_FOR", "target_id": "sk_pytorch", "target_name": "PyTorch", "target_type": "Skill", "weight": 1.0})
    else:
        connections.append({"rel_type": "REQUIRES", "target_id": "sk_python", "target_name": "Python", "target_type": "Skill", "weight": 0.9})
        connections.append({"rel_type": "LEADS_TO", "target_id": "occ_mle", "target_name": "Machine Learning Engineer", "target_type": "Occupation", "weight": 1.0})
        
    return {
        "id": node_id,
        "name": name,
        "type": node_type,
        "properties": {"id": node_id, "name": name, "domain": "Tech Domain"},
        "connections": connections
    }

def get_mock_explorer_graph(center_id: str = None) -> dict:
    # Full mockup graph to display on frontend dashboard immediately
    nodes = [
        {"id": "sk_python", "name": "Python", "type": "Skill"},
        {"id": "sk_pytorch", "name": "PyTorch", "type": "Skill"},
        {"id": "sk_gnn", "name": "Graph Neural Networks", "type": "Skill"},
        {"id": "sk_neo4j", "name": "Neo4j", "type": "Skill"},
        {"id": "sk_redis", "name": "Redis", "type": "Skill"},
        {"id": "sk_nextjs", "name": "Next.js", "type": "Skill"},
        {"id": "sk_react", "name": "React", "type": "Skill"},
        {"id": "sk_sql", "name": "SQL", "type": "Skill"},
        
        {"id": "occ_ds", "name": "Data Scientist", "type": "Occupation"},
        {"id": "occ_mle", "name": "Machine Learning Engineer", "type": "Occupation"},
        {"id": "occ_fsd", "name": "Full-Stack Developer", "type": "Occupation"},
        {"id": "occ_devops", "name": "DevOps Engineer", "type": "Occupation"}
    ]
    edges = [
        {"id": "e1", "source": "occ_ds", "target": "sk_python", "type": "REQUIRES"},
        {"id": "e2", "source": "occ_ds", "target": "sk_sql", "type": "REQUIRES"},
        {"id": "e3", "source": "occ_mle", "target": "sk_python", "type": "REQUIRES"},
        {"id": "e4", "source": "occ_mle", "target": "sk_pytorch", "type": "REQUIRES"},
        {"id": "e5", "source": "sk_pytorch", "target": "sk_gnn", "type": "PREREQUISITE_FOR"},
        {"id": "e6", "source": "occ_fsd", "target": "sk_react", "type": "REQUIRES"},
        {"id": "e7", "source": "sk_react", "target": "sk_nextjs", "type": "PREREQUISITE_FOR"},
        {"id": "e8", "source": "occ_devops", "target": "sk_redis", "type": "REQUIRES"},
        {"id": "e9", "source": "occ_ds", "target": "occ_mle", "type": "LEADS_TO"},
        {"id": "e10", "source": "occ_fsd", "target": "occ_devops", "type": "LEADS_TO"}
    ]
    
    if center_id:
        # Filter mock to only return center node and neighbors
        neighbors = set()
        for e in edges:
            if e["source"] == center_id:
                neighbors.add(e["target"])
            elif e["target"] == center_id:
                neighbors.add(e["source"])
        neighbors.add(center_id)
        
        filtered_nodes = [n for n in nodes if n["id"] in neighbors]
        filtered_edges = [e for e in edges if e["source"] in neighbors and e["target"] in neighbors]
        return {"nodes": filtered_nodes, "edges": filtered_edges}
        
    return {"nodes": nodes, "edges": edges}
