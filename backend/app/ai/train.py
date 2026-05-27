import os
import sys
import pickle
import torch
import torch.nn.functional as F
from torch_geometric.utils import negative_sampling

# Ensure backend folder is in path for standalone execution
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.core.config import settings
from app.ai.dataset_loader import dataset_loader
from app.ai.gnn_model import SkillGraphAIModel

def sample_negative_edges(edge_index, num_src_nodes, num_dst_nodes):
    """
    Generates negative edges (pairs with no relationship) for bipartite graph.
    """
    # Simply randomly sample pairs and filter out positives
    num_neg_samples = edge_index.size(1)
    neg_edges = []
    
    pos_set = set(zip(edge_index[0].tolist(), edge_index[1].tolist()))
    
    while len(neg_edges) < num_neg_samples:
        src = torch.randint(0, num_src_nodes, (num_neg_samples,)).tolist()
        dst = torch.randint(0, num_dst_nodes, (num_neg_samples,)).tolist()
        for s, d in zip(src, dst):
            if (s, d) not in pos_set:
                neg_edges.append([s, d])
                if len(neg_edges) >= num_neg_samples:
                    break
                    
    return torch.tensor(neg_edges, dtype=torch.long).t().contiguous()

async def train_model():
    print("Initializing GNN training pipeline...")
    
    # 1. Load Data
    try:
        data, skill_id_map, occ_id_map = await dataset_loader.load_heterodata()
    except Exception as e:
        print(f"Error loading graph data: {e}")
        print("Aborting training. Please seed Neo4j before training.")
        return False

    # Save ID mapping files for inference lookups
    os.makedirs(os.path.dirname(settings.GNN_MODEL_SAVE_PATH), exist_ok=True)
    with open("data/skill_id_map.pkl", "wb") as f:
        pickle.dump(skill_id_map, f)
    with open("data/occ_id_map.pkl", "wb") as f:
        pickle.dump(occ_id_map, f)

    # 2. Setup Model
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using GNN compute device: {device}")
    
    model = SkillGraphAIModel(
        metadata=data.metadata(),
        in_channels=384,
        hidden_channels=settings.GNN_HIDDEN_CHANNELS,
        out_channels=settings.GNN_OUT_CHANNELS
    ).to(device)
    
    data = data.to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=settings.GNN_LEARNING_RATE)
    
    # Extract training edges
    req_edges = data['occupation', 'requires', 'skill'].edge_index
    leads_edges = data['occupation', 'leads_to', 'occupation'].edge_index
    
    num_skills = data['skill'].x.size(0)
    num_occs = data['occupation'].x.size(0)

    model.train()
    for epoch in range(1, settings.GNN_EPOCHS + 1):
        optimizer.zero_grad()
        
        loss = 0.0
        
        # --- Relation 1: REQUIRES (Occupation -> Skill) ---
        if req_edges.numel() > 0:
            # Positive labels
            pos_label = torch.ones(req_edges.size(1), device=device)
            pos_pred = model(data.x_dict, data.edge_index_dict, req_edges, "requires")
            
            # Negative labels
            neg_edges = sample_negative_edges(req_edges.cpu(), num_occs, num_skills).to(device)
            neg_label = torch.zeros(neg_edges.size(1), device=device)
            neg_pred = model(data.x_dict, data.edge_index_dict, neg_edges, "requires")
            
            pred = torch.cat([pos_pred, neg_pred])
            label = torch.cat([pos_label, neg_label])
            loss += F.binary_cross_entropy(pred, label)
            
        # --- Relation 2: LEADS_TO (Occupation -> Occupation) ---
        if leads_edges.numel() > 0:
            pos_label = torch.ones(leads_edges.size(1), device=device)
            pos_pred = model(data.x_dict, data.edge_index_dict, leads_edges, "leads_to")
            
            neg_edges = sample_negative_edges(leads_edges.cpu(), num_occs, num_occs).to(device)
            neg_label = torch.zeros(neg_edges.size(1), device=device)
            neg_pred = model(data.x_dict, data.edge_index_dict, neg_edges, "leads_to")
            
            pred = torch.cat([pos_pred, neg_pred])
            label = torch.cat([pos_label, neg_label])
            loss += F.binary_cross_entropy(pred, label)
            
        if loss == 0.0:
            print("No valid edges to compute loss. Skipping training.")
            return False

        loss.backward()
        optimizer.step()
        
        if epoch % 10 == 0 or epoch == 1:
            print(f"Epoch {epoch:02d}/{settings.GNN_EPOCHS} | Loss: {loss.item():.4f}")
            
    # Save model weights
    torch.save(model.state_dict(), settings.GNN_MODEL_SAVE_PATH)
    print(f"GNN Model successfully trained and saved to {settings.GNN_MODEL_SAVE_PATH}")

    # Compute and save fused embeddings cache
    print("Computing and caching GNN fused embeddings...")
    model.eval()
    with torch.no_grad():
        fused = model.get_fused_embeddings(data.x_dict, data.edge_index_dict)
        fused_embeddings = {
            "skill": fused["skill"].cpu().numpy(),
            "occupation": fused["occupation"].cpu().numpy()
        }
    with open("data/fused_embeddings.pkl", "wb") as f:
        pickle.dump(fused_embeddings, f)
    print("GNN fused embeddings successfully cached to data/fused_embeddings.pkl")

    return True

if __name__ == "__main__":
    import asyncio
    asyncio.run(train_model())
