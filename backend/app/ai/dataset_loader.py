import torch
from torch_geometric.data import HeteroData
from app.db.database import get_neo4j_driver
from app.ai.embedder import embedder_instance

class SkillGraphDatasetLoader:
    def __init__(self):
        self.driver = get_neo4j_driver()

    async def load_heterodata(self) -> tuple[HeteroData, dict, dict]:
        """
        Queries Neo4j, converts graph to PyTorch Geometric HeteroData,
        and returns (hetero_data, skill_id_map, occupation_id_map)
        """
        async with self.driver.session() as session:
            # 1. Fetch all Skills
            skill_result = await session.run(
                "MATCH (s:Skill) RETURN s.id as id, s.name as name, s.type as type, s.domain as domain"
            )
            skills = [record async for record in skill_result]
            
            # 2. Fetch all Occupations
            occ_result = await session.run(
                "MATCH (o:Occupation) RETURN o.id as id, o.name as name, o.domain as domain"
            )
            occupations = [record async for record in occ_result]

            if not skills or not occupations:
                raise ValueError("Graph databases are empty. Seed the databases before loading.")

            # Create ID mappings (Neo4j ID -> Tensor Index)
            skill_to_idx = {s["id"]: i for i, s in enumerate(skills)}
            idx_to_skill = {i: s["id"] for i, s in enumerate(skills)}
            
            occ_to_idx = {o["id"]: i for i, o in enumerate(occupations)}
            idx_to_occ = {i: o["id"] for i, o in enumerate(occupations)}

            # Build semantic features using sentence-transformer
            skill_features = []
            for s in skills:
                txt = f"Skill: {s['name']}. Category: {s['type']}. Domain: {s['domain']}."
                skill_features.append(embedder_instance.get_embedding(txt))
            
            occ_features = []
            for o in occupations:
                txt = f"Occupation: {o['name']}. Domain: {o['domain']}."
                occ_features.append(embedder_instance.get_embedding(txt))

            # Convert to PyTorch Tensors
            x_skill = torch.tensor(skill_features, dtype=torch.float)
            x_occ = torch.tensor(occ_features, dtype=torch.float)

            data = HeteroData()
            data['skill'].x = x_skill
            data['occupation'].x = x_occ

            # 3. Fetch REQUIRES edges (Occupation -> Skill)
            req_result = await session.run(
                "MATCH (o:Occupation)-[r:REQUIRES]->(s:Skill) RETURN o.id as o_id, s.id as s_id, r.weight as weight"
            )
            req_edges = []
            req_weights = []
            async for rec in req_result:
                o_idx = occ_to_idx.get(rec["o_id"])
                s_idx = skill_to_idx.get(rec["s_id"])
                if o_idx is not None and s_idx is not None:
                     req_edges.append([o_idx, s_idx])
                     req_weights.append(rec["weight"] or 1.0)
            
            if req_edges:
                data['occupation', 'requires', 'skill'].edge_index = torch.tensor(req_edges, dtype=torch.long).t().contiguous()
                data['occupation', 'requires', 'skill'].edge_attr = torch.tensor(req_weights, dtype=torch.float)
                # Add reverse edge for message passing symmetry
                rev_req_edges = [[s_idx, o_idx] for o_idx, s_idx in req_edges]
                data['skill', 'rev_requires', 'occupation'].edge_index = torch.tensor(rev_req_edges, dtype=torch.long).t().contiguous()
            else:
                data['occupation', 'requires', 'skill'].edge_index = torch.empty((2, 0), dtype=torch.long)
                data['skill', 'rev_requires', 'occupation'].edge_index = torch.empty((2, 0), dtype=torch.long)

            # 4. Fetch SIMILAR_TO edges (Skill -> Skill)
            sim_result = await session.run(
                "MATCH (s1:Skill)-[r:SIMILAR_TO]->(s2:Skill) RETURN s1.id as s1_id, s2.id as s2_id, r.weight as weight"
            )
            sim_edges = []
            sim_weights = []
            async for rec in sim_result:
                s1_idx = skill_to_idx.get(rec["s1_id"])
                s2_idx = skill_to_idx.get(rec["s2_id"])
                if s1_idx is not None and s2_idx is not None:
                    sim_edges.append([s1_idx, s2_idx])
                    sim_weights.append(rec["weight"] or 1.0)
            
            if sim_edges:
                data['skill', 'similar_to', 'skill'].edge_index = torch.tensor(sim_edges, dtype=torch.long).t().contiguous()
                data['skill', 'similar_to', 'skill'].edge_attr = torch.tensor(sim_weights, dtype=torch.float)
            else:
                data['skill', 'similar_to', 'skill'].edge_index = torch.empty((2, 0), dtype=torch.long)

            # 5. Fetch LEADS_TO edges (Occupation -> Occupation)
            lead_result = await session.run(
                "MATCH (o1:Occupation)-[:LEADS_TO]->(o2:Occupation) RETURN o1.id as o1_id, o2.id as o2_id"
            )
            lead_edges = []
            async for rec in lead_result:
                o1_idx = occ_to_idx.get(rec["o1_id"])
                o2_idx = occ_to_idx.get(rec["o2_id"])
                if o1_idx is not None and o2_idx is not None:
                    lead_edges.append([o1_idx, o2_idx])
            
            if lead_edges:
                data['occupation', 'leads_to', 'occupation'].edge_index = torch.tensor(lead_edges, dtype=torch.long).t().contiguous()
            else:
                data['occupation', 'leads_to', 'occupation'].edge_index = torch.empty((2, 0), dtype=torch.long)

            # Define node mapping payloads
            skill_id_map = {"to_idx": skill_to_idx, "to_id": idx_to_skill}
            occ_id_map = {"to_idx": occ_to_idx, "to_id": idx_to_occ}
            
            return data, skill_id_map, occ_id_map

# Shared global dataset loader
dataset_loader = SkillGraphDatasetLoader()
