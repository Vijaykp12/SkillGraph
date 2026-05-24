#!/bin/bash

echo "=== Starting SkillGraph Services ==="

# Start databases
cd /workspaces/SkillGraph/infrastructure/docker
docker compose up postgres redis neo4j -d

sleep 15

# Start backend
cd /workspaces/SkillGraph/backend
source venv/bin/activate

nohup bash -c 'PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port 8000' > backend.log 2>&1 &

# Start frontend
cd /workspaces/SkillGraph/frontend

nohup npm run dev > frontend.log 2>&1 &

echo "=== SkillGraph Started ==="