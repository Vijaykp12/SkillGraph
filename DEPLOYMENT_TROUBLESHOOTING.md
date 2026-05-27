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

---

## 📌 Incident 2: Docker Build Failure on Render due to Invalid COPY statement

### 🔍 Symptoms
* Even after pushing the `fused_embeddings.pkl` cache and recommender updates, the deployed backend remains down (returning a **502 Bad Gateway** or pending connection timeout).
* Render dashboard shows the build has failed and is unable to deploy the new container.

### 🧩 Root Cause
The `backend/Dockerfile` had the following line:
`COPY ../scripts /scripts`
Since the Docker build context is configured as the `backend/` directory on Render, Docker forbids pointing to paths outside the build context using `..` relative paths. This throws a build error immediately. Furthermore, because `scripts` is inside `backend/scripts/`, it is already copied into the image by the preceding `COPY . .` instruction, making this line both invalid and redundant.

### 🚀 Solution
Removed the line `COPY ../scripts /scripts` from the Dockerfile.

### 📋 How to Deploy the Fix
Commit and push the updated Dockerfile to GitHub:
```bash
git add backend/Dockerfile
git commit -m "fix: remove invalid COPY statement from Dockerfile to fix Render build context error"
git push
```
Render will trigger a fresh build and deploy the container successfully.

---

## 📌 Incident 3: Indefinite Loading on Skill Gap Radar Page due to Sequentially-Looped Queries & Long Timeouts

### 🔍 Symptoms
* The **Skill DNA Mapping** and **Profile Overview** tabs work properly.
* The **Skill Gap Radar** page hangs indefinitely on the loading spinner, even though `/gap-analysis` responds instantly.
* The backend server event loop becomes blocked and unresponsive to subsequent requests.

### 🧩 Root Cause
1. When navigating to the Skill Gap Radar page, the frontend calls `/auth/profile` and `/recs/gap-analysis`, followed immediately by `/recs/learning-resources` to build the recommended training roadmap for missing skills.
2. Inside `/recs/learning-resources` (in `recommendations.py`), the backend performed N sequential database requests inside a loop (`for skill_id in missing_skill_ids:`) to fetch matching courses for each missing skill.
3. If Neo4j was offline or unreachable, each sequential request would block and wait for the default connection timeout of **30 seconds**. With 5+ missing skills, the route would take up to **150 seconds** to complete, clogging Uvicorn's event loop and appearing frozen to the user.

### 🚀 Solution
1. **Single Query Batching**: We refactored the loop in `app/api/endpoints/recommendations.py` to fetch all course recommendations in a single Cypher query using the `IN` clause: `WHERE s.id IN $missing_ids`. This reduces N roundtrips down to exactly 1.
2. **Fast Driver Timeout**: We configured the Neo4j driver in `app/db/database.py` with `connection_timeout=2.0` seconds. If Neo4j is offline, the connection fails fast (within 2 seconds) and falls back to mock recommendations instantly, avoiding blocking Uvicorn's thread.

### 📋 How to Deploy the Fix
Commit and push the backend updates to GitHub:
```bash
git add backend/app/api/endpoints/recommendations.py backend/app/db/database.py
git commit -m "fix: optimize learning recommendations with single query and 2s timeout on neo4j driver"
git push
```
Render will build and deploy the updated service automatically.

---

## 📌 Incident 4: API Requests Blocked by CORS Policy on Vercel Deployment

### 🔍 Symptoms
* API calls (like `/recs/gap-analysis`) fail immediately with `net::ERR_FAILED` or `Failed to fetch`.
* The browser console displays the following error:
  `Access to fetch at 'https://skillgraph-backend-14k8.onrender.com/api/v1/recs/gap-analysis' from origin 'https://skill-graph-rho.vercel.app' has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present on the requested resource.`

### 🧩 Root Cause
The frontend application is hosted on Vercel at `https://skill-graph-rho.vercel.app`. However, this URL was not included in the default `BACKEND_CORS_ORIGINS` list inside the backend configuration file (`app/core/config.py`). Because of this, the FastAPI CORSMiddleware rejected the request preflights and did not return the required `Access-Control-Allow-Origin` headers, causing the browser to block the frontend's API requests.

### 🚀 Solution
Added the production Vercel frontend URL `"https://skill-graph-rho.vercel.app"` to the `BACKEND_CORS_ORIGINS` list in `backend/app/core/config.py`.

### 📋 How to Deploy the Fix
Commit and push the updates:
```bash
git add backend/app/core/config.py
git commit -m "fix: allow Vercel origin https://skill-graph-rho.vercel.app in CORS backend settings"
git push
```
Render will deploy the updated config, and the Vercel app will be able to connect to the backend without CORS issues.

---

## 📌 Incident 5: PyTorch Threading RuntimeError on Startup/Inference

### 🔍 Symptoms
* Requests (like `/recs/twin-simulator`) fail with a **500 Internal Server Error**.
* The Hugging Face or Render backend logs show the following exception:
  `RuntimeError: Error: cannot set number of interop threads after parallel work has started or set_num_interop_threads called`

### 🧩 Root Cause
To optimize memory usage, we configure PyTorch to use a single CPU thread (`torch.set_num_threads(1)` / `torch.set_num_interop_threads(1)`). However, if PyTorch has already executed any tensor operations (such as converting numpy arrays to tensors in the database seeder/loader fallback) before these limits are set, the PyTorch C++ engine starts parallel workers. Attempting to set thread limits *after* parallel work has initiated is forbidden by PyTorch and throws a `RuntimeError`, crashing the API requests.

### 🚀 Solution
We wrapped the thread limit configuration calls inside `backend/app/ai/embedder.py` and `backend/app/ai/recommender.py` inside `try...except RuntimeError: pass` blocks. This allows PyTorch to gracefully bypass the thread-limit configuration if the parallel engine is already initialized, avoiding any crashes.

### 📋 How to Deploy the Fix
Commit and push the updates to GitHub and Hugging Face:
```bash
git add backend/app/ai/embedder.py backend/app/ai/recommender.py
git commit -m "fix: wrap PyTorch thread limit calls in try-except to avoid RuntimeError"
git push
```
Or for Hugging Face Spaces:
```bash
# Push the updated code files to Hugging Face
git push --force hf main
```
Hugging Face will rebuild and run the server successfully without crashes!

---

## 📌 Incident 6: Failed to Load GNN Model and FAISS Index on Hugging Face Space Deployment

### 🔍 Symptoms
* API logs show:
  ```
  Failed to load GNN model. Falling back to semantic-only: [Errno 2] No such file or directory: 'data/gnn_model.pt'
  FAISS index files not found. Vector search will be unavailable until indexed.
  FAISS index is not initialized. Returning empty.
  ```
* Career transitions, career twin simulations, and gap analysis requests do not use the GNN model and fallback to semantic-only (or return empty recommendations).

### 🧩 Root Cause
1. **Directory Path Mismatch**: Hugging Face rejects pushing large binary files via git push. The user uploaded the model checkpoints (`gnn_model.pt`, `fused_embeddings.pkl`, `faiss_index.bin`, `faiss_metadata.pkl`) using the Hugging Face Web UI, but placed them in the repository's root directory instead of the expected `data/` subdirectory.
2. **Missing Mappings due to Gitignore**: The GNN ID mapping files (`skill_id_map.pkl` and `occ_id_map.pkl`) were listed in `backend/.gitignore` under `data/*.pkl` and were thus omitted during `git push`. Without these mappings, GNN recommendations cannot match node IDs to embedding indices.

### 🚀 Solution
1. **Root-Level Fallback Paths**: We modified the loading logic in `backend/app/ai/recommender.py` and `backend/app/ai/embedder.py` to check for model files at the root directory (`.`) if they are missing in the `data/` directory.
2. **Git-Trackable JSON Mappings**: Instead of relying solely on binary `.pkl` mapping files, we updated `backend/app/ai/train.py` to save mapping structures as JSON files (`skill_id_map.json` and `occ_id_map.json`). JSON files are text-based and are NOT blocked by Hugging Face's Git push filters.
3. **JSON Loading Support**: We added support in `recommender.py` to automatically load from the JSON mapping files if pickle files are not found.

### 📋 How to Deploy the Fix
1. Commit the JSON mapping files and code fixes, then push them to Hugging Face:
   ```bash
   git add app/ai/embedder.py app/ai/recommender.py app/ai/train.py data/skill_id_map.json data/occ_id_map.json
   git commit -m "fix: fall back to root folder for model files and support JSON ID mappings"
   git push --force hf main
   ```
2. The Hugging Face container will automatically rebuild, detect the JSON mapping files via Git, locate the binary model files at the root level, and run the GNN recommendation engine successfully.


