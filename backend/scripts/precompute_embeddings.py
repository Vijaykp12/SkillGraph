import os
import sys
import pickle
import torch

# Ensure backend folder is in path for standalone execution
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.config import settings
from app.ai.dataset_loader import dataset_loader
from app.ai.gnn_model import SkillGraphAIModel

async def precompute():
    print("Starting pre-computation of GNN fused embeddings...")
    
    # Check if model weights exist
    if not os.path.exists(settings.GNN_MODEL_SAVE_PATH):
        print(f"Error: GNN model weights not found at {settings.GNN_MODEL_SAVE_PATH}")
        print("Please train the model first by running: python app/ai/train.py")
        sys.exit(1)
        
    # Check if ID mappings exist
    if not os.path.exists("data/skill_id_map.pkl") or not os.path.exists("data/occ_id_map.pkl"):
        print("Error: ID mappings (skill_id_map.pkl / occ_id_map.pkl) not found in data/.")
        print("Please train the model first to generate mappings.")
        sys.exit(1)

    print("Loading heterogeneous graph data from Neo4j...")
    try:
        data, skill_id_map, occ_id_map = await dataset_loader.load_heterodata()
    except Exception as e:
        print(f"Error loading graph data from Neo4j: {e}")
        print("Please ensure Neo4j is running and seeded.")
        sys.exit(1)

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using GNN compute device: {device}")

    # Build model architecture
    model = SkillGraphAIModel(
        metadata=data.metadata(),
        in_channels=384,
        hidden_channels=settings.GNN_HIDDEN_CHANNELS,
        out_channels=settings.GNN_OUT_CHANNELS
    ).to(device)

    # Load weights
    print(f"Loading weights from {settings.GNN_MODEL_SAVE_PATH}...")
    try:
        state_dict = torch.load(settings.GNN_MODEL_SAVE_PATH, map_location=device)
        model.load_state_dict(state_dict)
    except Exception as e:
        print(f"Error loading state dictionary into model: {e}")
        sys.exit(1)
        
    model.eval()

    # Compute fused embeddings
    print("Computing fused embeddings...")
    data = data.to(device)
    with torch.no_grad():
        fused = model.get_fused_embeddings(data.x_dict, data.edge_index_dict)
        fused_embeddings = {
            "skill": fused["skill"].cpu().numpy(),
            "occupation": fused["occupation"].cpu().numpy()
        }

    # Save to data/fused_embeddings.pkl
    out_path = "data/fused_embeddings.pkl"
    print(f"Saving fused embeddings to {out_path}...")
    with open(out_path, "wb") as f:
        pickle.dump(fused_embeddings, f)
        
    print("Pre-computation complete! Fused GNN embeddings cached successfully.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(precompute())
