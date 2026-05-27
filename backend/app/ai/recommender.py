import os
import pickle
import numpy as np
from app.core.config import settings
from app.db.database import get_neo4j_driver
from app.ai.embedder import embedder_instance

class SkillGraphRecommender:
    def __init__(self):
        self.model = None
        self.skill_map = None
        self.occ_map = None
        self.fused_embeddings = None
        self.driver = get_neo4j_driver()
        self.load_model()

    def load_model(self):
        """Loads trained GNN model and ID mapping files if available."""
        # 1. First check if we have pre-computed fused GNN embeddings (preferred production route)
        if os.path.exists("data/fused_embeddings.pkl") and os.path.exists("data/skill_id_map.pkl"):
            try:
                with open("data/skill_id_map.pkl", "rb") as f:
                    self.skill_map = pickle.load(f)
                with open("data/occ_id_map.pkl", "rb") as f:
                    self.occ_map = pickle.load(f)
                with open("data/fused_embeddings.pkl", "rb") as f:
                    self.fused_embeddings = pickle.load(f)
                self.model = "LOADED"
                print("Pre-computed GNN fused embeddings successfully loaded from disk.")
                return
            except Exception as e:
                print(f"Error loading cached GNN fused embeddings: {e}. Falling back to lazy loading.")

        # 2. Check if we can lazy-load via PyTorch weights (fallback)
        if os.path.exists(settings.GNN_MODEL_SAVE_PATH) and os.path.exists("data/skill_id_map.pkl"):
            try:
                # Load mappings
                with open("data/skill_id_map.pkl", "rb") as f:
                    self.skill_map = pickle.load(f)
                with open("data/occ_id_map.pkl", "rb") as f:
                    self.occ_map = pickle.load(f)

                # Initialize model architecture to load state dict
                # PyG HeteroData is needed to get metadata schema
                # Since loading graph data requires DB, we can wrap this in async to run it, 
                # or run a quick sync-blocking query or run on first recommendation call
                self.model = "PENDING_LAZY_LOAD"
                print("GNN model files detected. Lazy loading on first recommendation request.")
            except Exception as e:
                print(f"Error preparing GNN model load: {e}")
                self.model = None
        else:
            print("GNN weights not found. Running in semantic-only fallback mode.")

    async def _lazy_load_gnn_fused(self):
        """Loads GNN model weights and computes fused embeddings."""
        if self.model == "LOADED":
            return
        if self.model != "PENDING_LAZY_LOAD" and self.fused_embeddings is not None:
            return
            
        try:
            import torch
            # Apply CPU thread limits to PyTorch to save memory
            try:
                torch.set_num_threads(1)
                torch.set_num_interop_threads(1)
            except RuntimeError:
                pass
            
            from app.ai.dataset_loader import dataset_loader
            from app.ai.gnn_model import SkillGraphAIModel

            data, skill_id_map, occ_id_map = await dataset_loader.load_heterodata()
            self.skill_map = skill_id_map
            self.occ_map = occ_id_map
            
            device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            model_arch = SkillGraphAIModel(
                metadata=data.metadata(),
                in_channels=384,
                hidden_channels=settings.GNN_HIDDEN_CHANNELS,
                out_channels=settings.GNN_OUT_CHANNELS
            ).to(device)
            
            # Load weights
            state_dict = torch.load(settings.GNN_MODEL_SAVE_PATH, map_location=device)
            model_arch.load_state_dict(state_dict)
            model_arch.eval()
            
            # Compute and cache fused embeddings
            data = data.to(device)
            with torch.no_grad():
                fused = model_arch.get_fused_embeddings(data.x_dict, data.edge_index_dict)
                self.fused_embeddings = {
                    "skill": fused["skill"].cpu().numpy(),
                    "occupation": fused["occupation"].cpu().numpy()
                }
            self.model = model_arch
            print("GNN fused embeddings successfully computed and cached!")
        except Exception as e:
            print(f"Failed to load GNN model. Falling back to semantic-only: {e}")
            self.model = None
            self.fused_embeddings = None

    async def get_fused_embedding_for_node(self, node_id: str, node_type: str) -> np.ndarray:
        """Retrieves fused embedding for a specific node, or defaults to semantic embedding."""
        await self._lazy_load_gnn_fused()
        
        # If GNN is active and node is mapped
        if self.fused_embeddings and self.skill_map and self.occ_map:
            if node_type == "skill" and node_id in self.skill_map["to_idx"]:
                idx = self.skill_map["to_idx"][node_id]
                return self.fused_embeddings["skill"][idx]
            elif node_type == "occupation" and node_id in self.occ_map["to_idx"]:
                idx = self.occ_map["to_idx"][node_id]
                return self.fused_embeddings["occupation"][idx]
                
        # Semantic fallback
        return embedder_instance.get_embedding(node_id)

    async def recommend_skills_for_occupation(self, occupation_id: str, top_k: int = 5) -> list[dict]:
        """
        Recommends best skills for an occupation using structural GNN similarity.
        Falls back to semantic vector lookup if GNN is not trained.
        """
        await self._lazy_load_gnn_fused()
        
        if self.fused_embeddings and self.occ_map and self.skill_map and occupation_id in self.occ_map["to_idx"]:
            occ_idx = self.occ_map["to_idx"][occupation_id]
            occ_emb = self.fused_embeddings["occupation"][occ_idx]
            
            # Compute cosine similarity against all skills
            skill_embs = self.fused_embeddings["skill"]
            similarities = np.dot(skill_embs, occ_emb) # vectors are normalized
            
            top_indices = np.argsort(similarities)[::-1][:top_k]
            
            results = []
            for idx in top_indices:
                s_id = self.skill_map["to_id"][int(idx)]
                results.append({
                    "id": s_id,
                    "similarity": float(similarities[idx])
                })
            return results
        else:
            # Semantic search fallback
            return embedder_instance.search_similar(occupation_id, top_k=top_k, item_type="Skill")

    async def predict_career_transitions(self, occupation_id: str, top_k: int = 3) -> list[dict]:
        """
        Predicts next career transition occupation using link prediction.
        """
        await self._lazy_load_gnn_fused()
        
        if self.fused_embeddings and self.occ_map and occupation_id in self.occ_map["to_idx"]:
            occ_idx = self.occ_map["to_idx"][occupation_id]
            occ_emb = self.fused_embeddings["occupation"][occ_idx]
            
            # Compare to all other occupations
            occ_embs = self.fused_embeddings["occupation"]
            similarities = np.dot(occ_embs, occ_emb)
            
            # Sort, excluding itself
            sorted_indices = np.argsort(similarities)[::-1]
            results = []
            for idx in sorted_indices:
                o_id = self.occ_map["to_id"][int(idx)]
                if o_id == occupation_id:
                    continue
                results.append({
                    "id": o_id,
                    "similarity": float(similarities[idx])
                })
                if len(results) >= top_k:
                    break
            return results
        else:
            return embedder_instance.search_similar(occupation_id, top_k=top_k, item_type="Occupation")

    async def analyze_skill_gap(self, user_skills: list[str], target_occupation: str) -> dict:
        """
        Calculates skill gap analysis, diffing user skills against target occupation.
        """
        # Determine target occupation node
        target_id = target_occupation.lower().replace(" ", "_")
        if not target_id.startswith("occ_"):
            target_id = f"occ_{target_id}"

        # Get top skills for target occupation
        recs = await self.recommend_skills_for_occupation(target_id, top_k=8)
        
        # Mapping skill names for easy string matching
        target_skills_clean = []
        for r in recs:
            # Clean skill ID to readable name (e.g. sk_pytorch -> PyTorch)
            name = r["id"].replace("sk_", "").replace("_", " ").title()
            target_skills_clean.append({"id": r["id"], "name": name, "priority": r.get("similarity", 0.8)})
            
        user_skills_lower = [s.lower().strip() for s in user_skills]
        
        matching = []
        missing = []
        
        for ts in target_skills_clean:
            # Check if user has it
            match = False
            ts_name_lower = ts["name"].lower()
            for us in user_skills_lower:
                if us in ts_name_lower or ts_name_lower in us:
                    match = True
                    break
            if match:
                matching.append(ts)
            else:
                missing.append(ts)
                
        # Calculate compatibility percentage
        total_target = len(target_skills_clean)
        match_score = (len(matching) / total_target * 100) if total_target > 0 else 0
        
        return {
            "target_occupation": target_occupation,
            "match_score": round(match_score, 1),
            "matching_skills": matching,
            "missing_skills": missing
        }

    async def career_twin_simulation(self, start_occupation: str, target_occupation: str, user_skills: list[str] = None) -> dict:
        """
        Traces a career transition sequence from start to target.
        Generates transition steps, skills gaps, and a momentum indicator.
        """
        # Formulate transition nodes
        # If they are similar, it's a 1-step. If they are distant (e.g. Frontend to DevOps), 
        # it might suggest a transition like: Frontend -> Backend -> DevOps or Frontend -> Full-Stack -> DevOps.
        # We can implement a graph traversal or semantic multi-hop logic
        steps = [start_occupation]
        
        # Check semantic similarity between start and target
        start_emb = embedder_instance.get_embedding(start_occupation)
        target_emb = embedder_instance.get_embedding(target_occupation)
        
        sim = float(np.dot(start_emb, target_emb) / (np.linalg.norm(start_emb) * np.linalg.norm(target_emb)))
        
        # Simple heuristic multi-hop builder for realistic demonstration
        if sim > 0.8:
            steps.append(target_occupation)
        elif sim > 0.6:
            # 1 intermediary step
            # Find an intermediary occupation from standard lists
            intermediary = "Full-Stack Developer"
            if "frontend" in start_occupation.lower() and "devops" in target_occupation.lower():
                intermediary = "Backend Engineer"
            elif "scientist" in start_occupation.lower() and "engineer" in target_occupation.lower():
                intermediary = "Machine Learning Engineer"
            steps.append(intermediary)
            steps.append(target_occupation)
        else:
            # 2 intermediary steps
            intermediary1 = "Backend Engineer"
            intermediary2 = "DevOps Engineer"
            steps.append(intermediary1)
            steps.append(intermediary2)
            steps.append(target_occupation)
            
        # Build path sequence with gap details
        path_sequence = []
        for i in range(len(steps) - 1):
            curr = steps[i]
            nxt = steps[i+1]
            
            # Analyze gap for transition
            if i == 0 and user_skills is not None:
                curr_skills = user_skills
            else:
                # For subsequent steps or if user_skills not provided, 
                # extract mock user skills as current occupation standard skills
                curr_skills_data = await self.analyze_skill_gap([], curr)
                curr_skills = [s["name"] for s in curr_skills_data["missing_skills"][:4]]
            
            gap_data = await self.analyze_skill_gap(curr_skills, nxt)
            
            path_sequence.append({
                "from_occupation": curr,
                "to_occupation": nxt,
                "gap_percentage": 100 - gap_data["match_score"],
                "skills_to_learn": [s["name"] for s in gap_data["missing_skills"][:3]]
            })
            
        # Calculate momentum score based on similarity and step size
        # Less steps = higher velocity/momentum. High similarity = higher momentum.
        step_penalty = len(steps) * 0.1
        momentum = max(0.1, min(1.0, sim + 0.2 - step_penalty))
        
        return {
            "start_occupation": start_occupation,
            "target_occupation": target_occupation,
            "path_sequence": path_sequence,
            "momentum_score": round(momentum * 100, 1),
            "total_steps": len(steps) - 1
        }

    async def get_skill_dna(self, user_skills: list[str]) -> dict:
        """
        Maps user skills into scores across occupations.
        To reach 5/5, the user must have all skills associated with the occupation.
        """
        occupation_skills = {}
        try:
            async with self.driver.session() as session:
                result = await session.run(
                    "MATCH (o:Occupation)-[:REQUIRES]->(s:Skill) "
                    "RETURN o.name as occ_name, s.name as skill_name"
                )
                async for record in result:
                    occ_name = record["occ_name"]
                    skill_name = record["skill_name"]
                    if occ_name not in occupation_skills:
                        occupation_skills[occ_name] = []
                    occupation_skills[occ_name].append(skill_name)
        except Exception as e:
            print(f"Error fetching DNA occupations from Neo4j: {e}")
            occupation_skills = {}

        # Fallback if Neo4j is empty or query failed
        if not occupation_skills:
            occupation_skills = {
                "Data Scientist": ["Python", "SQL", "Scikit-Learn", "PyTorch", "Graph Neural Networks", "Natural Language Processing"],
                "Machine Learning Engineer": ["Python", "PyTorch", "TensorFlow", "Transformers", "Docker", "Kubernetes"],
                "Full-Stack Developer": ["JavaScript", "TypeScript", "React", "Next.js", "Python", "PostgreSQL"],
                "DevOps Engineer": ["Docker", "Kubernetes", "Terraform", "AWS", "CI/CD"],
                "Data Engineer": ["Python", "SQL", "PostgreSQL", "Neo4j", "Redis", "Data Warehousing"],
                "Cloud Architect": ["AWS", "Google Cloud Platform", "Kubernetes", "Terraform"],
                "Frontend Engineer": ["JavaScript", "TypeScript", "React", "Next.js", "TailwindCSS", "Framer Motion"],
                "Backend Engineer": ["Python", "SQL", "PostgreSQL", "Redis", "Docker"],
                "Systems Engineer": ["C++", "Rust", "Go", "Docker", "Git"],
                "AI Researcher": ["Python", "PyTorch", "Deep Learning", "Transformers", "Large Language Models"],
                "Product Manager": ["UI/UX Design", "Figma", "Git"],
                "Security Engineer": ["Python", "Docker", "Kubernetes", "AWS", "Microsoft Azure"],
                "QA Automation Engineer": ["Python", "JavaScript", "Git", "CI/CD", "Jenkins"],
                "Mobile Developer": ["JavaScript", "TypeScript", "Git", "React"],
                "Database Administrator": ["SQL", "PostgreSQL", "MySQL", "Redis", "MongoDB"],
                "UI/UX Designer": ["UI/UX Design", "Figma", "HTML & CSS"]
            }

        dna = {}
        user_skills_lower = [s.lower().strip() for s in user_skills]

        for occ_name, req_skills in occupation_skills.items():
            if not req_skills:
                dna[occ_name] = 0.0
                continue
                
            matches = 0
            for req_skill in req_skills:
                req_skill_lower = req_skill.lower().strip()
                match_found = False
                for us in user_skills_lower:
                    if us in req_skill_lower or req_skill_lower in us:
                        match_found = True
                        break
                if match_found:
                    matches += 1

            # Scale to 5/5 max, only 5/5 if they have all skills
            score = 5.0 * (matches / len(req_skills))
            dna[occ_name] = round(score, 1)

        return dna

# Shared global recommender
recommender = SkillGraphRecommender()
