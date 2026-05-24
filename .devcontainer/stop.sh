#!/bin/bash

echo "=== Stopping SkillGraph ==="

pkill -f "uvicorn app.main:app"
pkill -f "next dev"

cd /workspaces/SkillGraph/infrastructure/docker
docker compose down

echo "=== SkillGraph Stopped ==="