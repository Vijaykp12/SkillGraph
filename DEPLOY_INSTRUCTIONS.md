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

## 🧠 2. Manual GNN Retraining (No Billing / No Cron)

Since we have removed Celery and cron schedulers to bypass billing fees, you can trigger GNN model retraining manually whenever you add new skills or seed data.

### Triggering Retraining via API Docs (Swagger UI)
1. Navigate to your running backend docs page:
   `https://your-backend-service.onrender.com/docs`
2. Scroll to the **`skills`** section and locate the endpoint:
   `POST /api/v1/skills/retrain`
3. Click **Try it out**.
4. Add the header value `X-Admin-Token` matching your `SECRET_KEY`.
5. Click **Execute**. The API will immediately return `{"status": "GNN model retraining started in the background."}` and process the GNN training in the background.

### Triggering Retraining via Terminal/cURL
You can also trigger it from any command prompt:
```bash
curl -X POST "https://your-backend-service.onrender.com/api/v1/skills/retrain" \
     -H "accept: application/json" \
     -H "X-Admin-Token: YOUR_SECRET_KEY"
```
