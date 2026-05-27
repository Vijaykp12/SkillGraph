# 🛠️ SkillGraph Deployment Troubleshooting Log

This file contains detailed records of errors encountered during the deployment of the SkillGraph platform, their root causes, and how they were solved. Use this as a reference when deploying similar applications in resource-constrained environments.

---

## 📌 Incident 1: Backend Hangup & Out-Of-Memory (OOM) Crashes on Skill Gap Analysis

### 🔍 Symptoms
* The application deploys successfully and the initial routes (login, resume parsing, skill DNA mapping) work fine.
* When navigating to the **Skill Gap Analysis** tab, the frontend spinner runs indefinitely and the backend becomes unresponsive (keeps waiting for a response).
* Reloading the server takes an unusually long time.
* The backend eventually crashes, and Render displays a rendering error or a 502 Bad Gateway / 503 Service Unavailable page.
* In Render logs, the service gets restarted due to exceeding memory limits (OOM Killer).

---

### 🧩 Root Cause
When the Skill Gap Analysis page is accessed, the backend endpoint calls the recommendation system, which lazy-loads the Graph Neural Network (GNN) model:
1. **CPU-Blocking event loop**: To align node features for PyTorch Geometric (PyG), the backend fetches the entire taxonomy of Skills and Occupations from Neo4j and calls `embedder_instance.get_embedding(txt)` in a loop using `SentenceTransformer('all-MiniLM-L6-v2')`. Since Uvicorn is single-threaded, running hundreds of neural network text encodings on the CPU sequentially blocks FastAPI's event loop entirely, causing all requests (including frontend requests and health checks) to hang and time out.
2. **Out of Memory (OOM) limits**: Loading the full `torch`, `torch_geometric`, and `sentence-transformers` libraries, creating the PyG `HeteroData` graph object, loading the 5.8MB model weights, and running a forward pass on a shared CPU consumes over 600MB of RAM. In cloud environments with tight memory limits (like the Render Free Tier's 512MB RAM cap), the OS kernel immediately terminates the server process.

---

### 🚀 Solution: Fused Embedding Pre-Computation Cache
Instead of dynamically loading the GNN and embedding nodes on the fly within a request lifecycle, we precompute the fused GNN embeddings and serialize them to disk as a cached resource.

1. **Pre-compute embeddings**:
   We created a script `backend/scripts/precompute_embeddings.py` that connects to the graph database, runs GNN forward propagation offline, and dumps the output into a dictionary mapping skill and occupation IDs to their GNN-fused numpy arrays, saved in `backend/data/fused_embeddings.pkl`.
   
2. **Instant startup loading**:
   We modified `backend/app/ai/recommender.py` to check for `data/fused_embeddings.pkl` at startup:
   * If the file is found, it loads it via standard python `pickle`. This takes **less than 5ms**, uses **less than 10MB of RAM**, and completely avoids loading PyTorch/PyG or calling SentenceTransformers inside web requests.
   * If the file is not found, the system gracefully falls back to the semantic FAISS index, eliminating any downtime.

3. **Retraining Sync**:
   We updated `backend/app/ai/train.py` so that whenever GNN training is triggered (either offline or via the `/retrain` admin endpoint), the new weights are used to automatically update `data/fused_embeddings.pkl`, keeping the cache in sync.

---

### 📋 How to Deploy the Fix
Whenever you encounter this error in this or other deployments, follow these steps:

#### Step 1: Precompute the Cache Locally
Run the pre-computation script inside your virtual environment (pointing to your graph database):

On Windows (PowerShell):
```powershell
.\venv\Scripts\python.exe scripts/precompute_embeddings.py
```

On Windows (Command Prompt):
```cmd
venv\Scripts\python scripts/precompute_embeddings.py
```

On macOS/Linux:
```bash
source venv/bin/activate
python scripts/precompute_embeddings.py
```
This generates the file `backend/data/fused_embeddings.pkl`.

#### Step 2: Commit the Cache File
Commit the precomputed file directly to your Git repository so it is built into the Docker container or uploaded directly to Render:
```bash
git add backend/data/fused_embeddings.pkl
git commit -m "chore: add precomputed fused GNN embeddings cache"
git push
```

#### Step 3: Deploy to Render
Render will deploy the new build. Because `fused_embeddings.pkl` is loaded instantly at startup, the container starts up immediately, memory consumption stays under **120MB**, and the skill gap analysis responses return in **milliseconds** without crashing the server.
