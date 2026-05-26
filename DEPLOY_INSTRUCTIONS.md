# 🚀 Next Steps: Python Version & Retraining Configuration

This guide addresses your Render environment adjustments and explains how to run model retraining without paid cron jobs or Celery services.

---

## 🐍 1. Forcing Python 3.11 on Render

Because your Render native Python web service defaulted to Python 3.14, you encountered version conflicts. Here are the two ways to force the correct Python version:

### Option A: Use the `PYTHON_VERSION` Environment Variable (Native Runtime)
If you want to continue running natively on Render without Docker:
1. Go to your Render Dashboard and click on your **`skillgraph-backend`** web service.
2. Click on the **Environment** tab on the left.
3. Click **Add Environment Variable**.
4. Set the key and value:
   - **Key**: `PYTHON_VERSION`
   - **Value**: `3.11.8`
5. Click **Save Changes**. Render will automatically redeploy and build the app using Python 3.11.

### Option B: Deploy via Docker (Highly Recommended)
ML applications with dependencies like PyTorch and FAISS are much more stable when built inside isolated Docker containers. Since we already have a production-ready `Dockerfile` in the `/backend` folder:
1. In the Render Dashboard, click **New +** -> **Web Service**.
2. Connect your Git repository.
3. In the setup page, change the **Runtime** selection from **Python** to **Docker**.
4. Set the **Docker Build Context** to `backend`.
5. Set the **Dockerfile Path** to `backend/Dockerfile`.
6. Add your environment variables (e.g., database URLs, keys) and click **Create Web Service**.

---

## 🧠 2. Persistent Search Indexes & GNN Models (Zero-Warmup Container)

Because Render free tier container filesystems are ephemeral, any model weights or FAISS index files created dynamically in the cloud would be deleted whenever your Render service restarts or redeploys.

To prevent this:
* We have pre-built the FAISS index and pre-trained the GNN model.
* These files have been committed directly to your Git repository in the `backend/data/` folder:
  - `faiss_index.bin` & `faiss_metadata.pkl` (Semantic Search Index)
  - `gnn_model.pt` (GNN Model Weights)
  - `skill_id_map.pkl` & `occ_id_map.pkl` (ID Maps)
* When you deploy to Render, these files are baked into the container out-of-the-box. The service warms up instantly and runs immediately without startup warnings!

---

## ⚡ 3. Refreshing Data & Seeding Taxonomy

If you ever add new nodes or want to refresh the default database tables and knowledge graph:

### Step 1: Run the Database Seeder
You can run the seeding script directly in the **Shell** tab of your Render Web Service, or run it locally by pointing to your production database credentials:
```bash
python scripts/seed_data.py
```
This will:
1. Initialize the PostgreSQL admin user (`admin@skillgraph.ai`).
2. Clear the Neo4j Graph database and insert default skills, occupations, companies, and relationships.
3. Re-build the local `faiss_index.bin` and `faiss_metadata.pkl` inside the running container.

### Step 2: Trigger GNN Model Retraining
Once the taxonomy is updated in Neo4j, trigger the model to learn the new graph structures:

#### Option A: Via Swagger UI Docs
1. Navigate to your running backend docs page:
   `https://your-backend-service.onrender.com/docs`
2. Scroll to the **`skills`** section and locate the endpoint:
   `POST /api/v1/skills/retrain`
3. Click **Try it out**.
4. Add the header value `X-Admin-Token` matching your `SECRET_KEY`.
5. Click **Execute**. The GNN model will retrain in the background.

#### Option B: Via Terminal/cURL
You can also trigger it from any command prompt:
```bash
curl -X POST "https://your-backend-service.onrender.com/api/v1/skills/retrain" \
     -H "accept: application/json" \
     -H "X-Admin-Token: YOUR_SECRET_KEY"
```
The GNN model will retrain in the background and write the new `gnn_model.pt` weights file in the active container. To make these weights persistent, you can download them from the container and commit them to Git.
