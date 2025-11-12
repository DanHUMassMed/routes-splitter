import base64
import os
import debugpy
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi import FastAPI, HTTPException
from wulfs_routing_api.celery_app import celery_app
from wulfs_routing_api.tasks.celery_tasks import generate_routing_task
from wulfs_routing_api.models.supabase_db import supabase
from pydantic import BaseModel
from celery.result import AsyncResult
from wulfs_routing_api.api import routes_api
import logging
logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "WARNING").upper())


if os.getenv("ACTIVATE_DEBUG") == "DEBUG" and os.getenv("RUN_MAIN") == "true":
    try:
        debugpy.listen(("0.0.0.0", 58979))
        print("Waiting for debugger to attach...")
        debugpy.wait_for_client()
    except RuntimeError:
        print("Debugpy already active — skipping listen()")

app = FastAPI()


app.include_router(routes_api.router, tags=["Routing"])