import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import HeteroConv, SAGEConv, GATConv, Linear
from app.core.config import settings

class SkillGraphHeteroGNN(nn.Module): # nn.Module => core neural network working component , provides trainable parameters and supports forward and backward propogation.
    def __init__(self, metadata, hidden_channels: int, out_channels: int, num_layers: int = 2):
        super().__init__()
        
        self.convs = nn.ModuleList()
        # Layer 1
        conv1_dict = {}
        for edge_type in metadata[1]:
            # edge_type is (src_type, rel_type, dst_type)
            src_type, _, dst_type = edge_type
            # We use GATConv for expressive attention-based message passing
            conv1_dict[edge_type] = GATConv((-1, -1), hidden_channels, heads=2, concat=False, add_self_loops=False)
        self.convs.append(HeteroConv(conv1_dict, aggr='mean'))
        
        # Subsequent Layers
        for _ in range(num_layers - 1):
            conv_dict = {}
            for edge_type in metadata[1]:
                conv_dict[edge_type] = SAGEConv(hidden_channels, hidden_channels)
            self.convs.append(HeteroConv(conv_dict, aggr='mean'))
            
        # Final projection to align dimensions and produce structural embeddings
        self.proj_skill = Linear(hidden_channels, out_channels)
        self.proj_occ = Linear(hidden_channels, out_channels)

    def forward(self, x_dict, edge_index_dict) -> dict[str, torch.Tensor]:
        """
        Passes messages through heterogeneous edges.
        Returns structural embeddings for each node type.
        """
        x = x_dict
        for conv in self.convs:
            x = conv(x, edge_index_dict)
            # Apply ReLU and dropout to dict of tensors
            x = {key: F.dropout(F.relu(val), p=0.2, training=self.training) for key, val in x.items()}
            
        # Output projection
        out = {}
        if 'skill' in x:
            out['skill'] = self.proj_skill(x['skill'])
        if 'occupation' in x:
            out['occupation'] = self.proj_occ(x['occupation'])
            
        return out

class LinkPredictor(nn.Module):
    """
    Decodes pairs of node embeddings to predict edge presence.
    Supports predicting transitions (Occupation -> Occupation) or requirements (Occupation -> Skill).
    """
    def __init__(self, in_channels: int):
        super().__init__()
        self.mlp = nn.Sequential(
            nn.Linear(in_channels * 2, in_channels),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(in_channels, 1)
        )

    def forward(self, x_src: torch.Tensor, x_dst: torch.Tensor, edge_label_index: torch.Tensor) -> torch.Tensor:
        # edge_label_index is [2, E] containing indices of src and dst node pairs
        src_nodes = x_src[edge_label_index[0]]
        dst_nodes = x_dst[edge_label_index[1]]
        # Concatenate src and dst features
        features = torch.cat([src_nodes, dst_nodes], dim=-1)
        return torch.sigmoid(self.mlp(features)).squeeze(-1)

class SkillGraphAIModel(nn.Module):
    def __init__(self, metadata, in_channels: int = 384, hidden_channels: int = 128, out_channels: int = 64):
        super().__init__()
        # Initial dimension alignment (e.g. 384 semantic embedding input -> GNN channels)
        self.align_skill = nn.Linear(in_channels, hidden_channels)
        self.align_occ = nn.Linear(in_channels, hidden_channels)
        
        # Heterogeneous GNN
        self.gnn = SkillGraphHeteroGNN(metadata, hidden_channels, out_channels, num_layers=settings.GNN_NUM_LAYERS)
        
        # Fused linear projection layer to merge initial semantic features and GNN structural output
        self.fuse_skill = nn.Linear(in_channels + out_channels, in_channels)
        self.fuse_occ = nn.Linear(in_channels + out_channels, in_channels)
        
        # Predictors for recommendation & career paths
        self.requires_predictor = LinkPredictor(in_channels)
        self.leads_to_predictor = LinkPredictor(in_channels)

    def get_fused_embeddings(self, x_dict, edge_index_dict) -> dict[str, torch.Tensor]:
        """
        Merges initial semantic embeddings (384-dim) and structural GNN embeddings (64-dim)
        to form a unified 384-dimensional representation.
        """
        # Step 1: Align dimensions for GNN input
        x_aligned = {
            'skill': F.relu(self.align_skill(x_dict['skill'])),
            'occupation': F.relu(self.align_occ(x_dict['occupation']))
        }
        
        # Step 2: Extract GNN structural representations
        struct_embs = self.gnn(x_aligned, edge_index_dict)
        
        # Step 3: Concatenate semantic (x_dict) + structural (struct_embs)
        fused_skill = self.fuse_skill(torch.cat([x_dict['skill'], struct_embs['skill']], dim=-1))
        fused_occ = self.fuse_occ(torch.cat([x_dict['occupation'], struct_embs['occupation']], dim=-1))
        
        # L2 Normalize the final representations for easy cosine-similarity lookups
        return {
            'skill': F.normalize(fused_skill, p=2, dim=-1),
            'occupation': F.normalize(fused_occ, p=2, dim=-1)
        }

    def forward(self, x_dict, edge_index_dict, edge_label_index, relation_type: str = "requires") -> torch.Tensor:
        """
        Evaluates link prediction for training.
        - relation_type: "requires" (Occupation -> Skill) or "leads_to" (Occupation -> Occupation)
        """
        fused = self.get_fused_embeddings(x_dict, edge_index_dict)
        
        if relation_type == "requires":
            return self.requires_predictor(fused['occupation'], fused['skill'], edge_label_index)
        elif relation_type == "leads_to":
            return self.leads_to_predictor(fused['occupation'], fused['occupation'], edge_label_index)
        else:
            raise ValueError(f"Unknown relation type for predictor: {relation_type}")
