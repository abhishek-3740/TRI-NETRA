"""
Graph embedding layer — Layer 3 of the risk scoring pipeline.

GraphSAGE (PyTorch Geometric) is the primary goal. Node2Vec is the
safety-net fallback if PyG install/training stalls on a CPU-only box
(common failure: torch-scatter/torch-sparse needing a working C++
toolchain). Flip USE_GRAPHSAGE=false in .env to switch — no other code
needs to change, since both paths expose the same get_embeddings() /
classify() interface.

Demo narrative is identical either way:
  Graph embeddings -> Logistic Regression -> Mule Classification
"""
import numpy as np
import networkx as nx
from sklearn.linear_model import LogisticRegression
from app.config import settings


def get_embeddings(G: nx.Graph) -> dict:
    if settings.use_graphsage:
        try:
            return _graphsage_embeddings(G)
        except ImportError:
            print("[safety-valve] PyTorch Geometric unavailable — falling back to Node2Vec.")
            return _node2vec_embeddings(G)
    return _node2vec_embeddings(G)


def _graphsage_embeddings(G: nx.Graph) -> dict:
    """Primary path — requires torch + torch_geometric (see requirements.txt)."""
    import torch
    from torch_geometric.utils import from_networkx
    from torch_geometric.nn import SAGEConv

    class SAGE(torch.nn.Module):
        def __init__(self, in_dim, hidden_dim=32, out_dim=16):
            super().__init__()
            self.conv1 = SAGEConv(in_dim, hidden_dim)
            self.conv2 = SAGEConv(hidden_dim, out_dim)

        def forward(self, x, edge_index):
            x = self.conv1(x, edge_index).relu()
            return self.conv2(x, edge_index)

    data = from_networkx(G)
    in_dim = data.num_node_features or 1
    if data.x is None:
        data.x = torch.ones((data.num_nodes, 1))

    model = SAGE(in_dim)
    model.eval()
    with torch.no_grad():
        embeddings = model(data.x, data.edge_index).numpy()

    node_list = list(G.nodes)
    return {node_list[i]: embeddings[i] for i in range(len(node_list))}


def _node2vec_embeddings(G: nx.Graph) -> dict:
    """Safety-net path — pure NetworkX + node2vec, no C++ toolchain needed."""
    from node2vec import Node2Vec

    if G.number_of_nodes() == 0:
        return {}

    n2v = Node2Vec(G, dimensions=16, walk_length=10, num_walks=50, workers=1, quiet=True)
    model = n2v.fit(window=5, min_count=1)
    return {node: model.wv[str(node)] for node in G.nodes if str(node) in model.wv}


def classify_mule_accounts(embeddings: dict, labels: dict) -> LogisticRegression:
    """Trains Logistic Regression on top of graph embeddings to classify mule accounts."""
    node_ids = list(embeddings.keys())
    X = np.array([embeddings[n] for n in node_ids])
    y = np.array([labels.get(n, 0) for n in node_ids])

    clf = LogisticRegression(max_iter=1000)
    clf.fit(X, y)
    return clf
