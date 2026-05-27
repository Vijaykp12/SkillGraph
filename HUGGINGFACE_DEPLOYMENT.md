# 🚀 Deploying SkillGraph Backend to Hugging Face Spaces (Free 16GB RAM / 2 vCPUs)

If you are hosting the backend on Render's Free Tier, you will experience **sluggish request speeds** and **long spin-up delays (cold starts)** because Render only provides a fraction of a shared CPU, 512MB of RAM, and shuts down the container after 15 minutes of inactivity.

**Hugging Face Spaces** offers a vastly superior free tier for Machine Learning APIs:
* **Memory**: **16 GB of RAM** (vs 512 MB on Render)
* **Compute**: **2 vCPU Cores** (vs ~0.1 core equivalent on Render)
* **Cold Starts**: None (the Space runs 24/7. It only goes to sleep after 48 hours of complete inactivity, and wakes up almost instantly).
* **Docker Support**: You can deploy using the exact same `backend/Dockerfile` we optimized.

---

## 📋 Step-by-Step Deployment Guide

### Step 1: Create a Hugging Face Space
1. Sign up/log in to [Hugging Face](https://huggingface.co/).
2. Click on your profile picture on the top right and select **New Space**.
3. Fill in the configuration:
   * **Space Name**: e.g., `skillgraph-backend`
   * **License**: Choose `apache-2.0` or `mit`
   * **Select the Space SDK**: Click **Docker** (Very Important)
   * **Docker Template**: Choose **Blank**
   * **Space Hardware**: Keep it on **CPU Basic (2 vCPUs, 16GB RAM) - Free**
   * **Visibility**: Public (so your frontend can access it)
4. Click **Create Space**.

---

### Step 2: Configure Environment Variables
Before pushing the code, configure your database credentials so the backend can connect to PostgreSQL, Neo4j, and Redis:
1. Inside your newly created Space, click on the **Settings** tab.
2. Scroll down to **Variables and secrets**.
3. Under **Variables**, add the following keys and values:
   * `POSTGRES_SERVER` = (Your hosted Postgres host)
   * `POSTGRES_USER` = (Your hosted Postgres user)
   * `POSTGRES_PASSWORD` = (Your hosted Postgres password)
   * `POSTGRES_DB` = (Your hosted Postgres DB name)
   * `NEO4J_URI` = (Your hosted Neo4j URI)
   * `NEO4J_USER` = (Your hosted Neo4j username)
   * `NEO4J_PASSWORD` = (Your hosted Neo4j password)
   * `REDIS_HOST` = (Your hosted Redis host)
   * `SECRET_KEY` = (Your API secret key)
4. (Optional) If you have any secrets, you can add them under **New Secret** instead of variables.

---

### Step 3: Push Your Code to Hugging Face
Hugging Face Spaces are backed by standard Git repositories. You can push the backend directory to Hugging Face:

1. Copy the Git URL of your Hugging Face Space (visible on the Space page, e.g., `https://huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE_NAME`).
2. Open your terminal in the backend directory (`D:\SkillGraph\home\claude\skillgraph\backend`) and initialize a new remote or push the subdirectory:

To push just the `backend` folder as the root of the space (required since the Dockerfile is in the backend root):
```bash
# Move into the backend folder
cd backend

# Initialize Git inside the backend directory (Hugging Face expects the Dockerfile at the root of the repo)
git init
git checkout -b main

# Configure remote with your username and write token embedded to bypass password authentication
git remote add hf https://YOUR_USERNAME:YOUR_WRITE_TOKEN@huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE_NAME

# Add files, making sure to include the data cache!
git add .
git commit -m "deploy: initial Hugging Face deployment"

# Force push to the Hugging Face remote
git push --force hf main
```

*Note: Replace `YOUR_USERNAME` with `vijayk12`, `YOUR_SPACE_NAME` with `skillgraph-backend`, and `YOUR_WRITE_TOKEN` with your Hugging Face User Access Token (which you can generate in your Hugging Face Profile Settings -> Access Tokens with the **Write** role).*

---

### Step 4: Access Your Live Backend
1. Once pushed, Hugging Face will automatically detect the `Dockerfile` in the root of the repository and start building.
2. Because of the **2 vCPU / 16GB RAM** specs, the build will finish in about 2 minutes.
3. Once the build is complete, your space will show a **Running** status.
4. Your API endpoint will be available at:
   `https://YOUR_USERNAME-YOUR_SPACE_NAME.hf.space`
   *(Example: `https://vijaykp12-skillgraph-backend.hf.space`)*
5. You can test it by going to `https://YOUR_USERNAME-YOUR_SPACE_NAME.hf.space/api/v1/` or `.../docs` in your browser.

---

### Step 5: Update Your Frontend API URL
Update the API URL in your Vercel configuration or frontend environment variables:
* Set **`NEXT_PUBLIC_API_URL`** to:
  `https://YOUR_USERNAME-YOUR_SPACE_NAME.hf.space/api/v1`
* Set **`NEXT_PUBLIC_WS_URL`** to:
  `wss://YOUR_USERNAME-YOUR_SPACE_NAME.hf.space/api/v1/assistant/ws/chat`

Your requests will now process instantly!
