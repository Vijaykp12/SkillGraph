import asyncio
from celery import Celery
from celery.schedules import crontab
from app.core.config import settings
from app.ai.train import train_model

# Initialize Celery
celery_app = Celery(
    "skillgraph_tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

# Configuration settings
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Nightly schedule setup (Midnight daily)
celery_app.conf.beat_schedule = {
    "nightly-gnn-retraining": {
        "task": "app.workers.tasks.train_gnn_task",
        "schedule": crontab(hour=0, minute=0),
    },
}

@celery_app.task
def train_gnn_task():
    """
    Background worker task running GNN model retraining.
    Runs inside asyncio event loop since graph queries are async.
    """
    print("Celery Worker: Starting scheduled GNN retraining task...")
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    success = loop.run_until_complete(train_model())
    if success:
        print("Celery Worker: GNN model retraining completed successfully.")
        return "SUCCESS"
    else:
        print("Celery Worker: GNN retraining failed (see logs).")
        return "FAILED"
