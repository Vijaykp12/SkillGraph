---
title: SkillGraph Backend
emoji: 🧬
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

# SkillGraph Workforce Intelligence Backend

This repository hosts the production-grade FastAPI backend for the SkillGraph workforce intelligence platform. It runs inside a Docker container on Hugging Face Spaces (CPU Basic tier with 2 vCPUs and 16GB of RAM).

## Features
* Precomputed GNN Fused Embeddings cache loading.
* FAISS-powered semantic vector lookups.
* Fast database timeouts for high resilience.
