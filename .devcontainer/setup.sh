#!/bin/bash

echo "=== Setting up SkillGraph ==="

# Backend setup
cd /workspaces/SkillGraph/backend

python -m venv venv
source venv/bin/activate

pip install torch==2.4.1 torchvision==0.19.1 torchaudio==2.4.1 --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt

# Frontend setup
cd /workspaces/SkillGraph/frontend

npm install

echo "=== Setup Complete ==="