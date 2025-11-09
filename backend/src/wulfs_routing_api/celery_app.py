from celery import Celery

# For now, we'll hardcode the default local Redis instance.
# In a real app, this would come from environment variables.
REDIS_URL = "redis://localhost:6379/0"

celery_app = Celery(
    "tasks",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["wulfs_routing_api.tasks.celery_tasks"], # Points to the file where tasks are defined
)

celery_app.conf.update(
    task_track_started=True,
    result_expires=3600, # Keep results for 1 hour
)

if __name__ == "__main__":
    celery_app.start()