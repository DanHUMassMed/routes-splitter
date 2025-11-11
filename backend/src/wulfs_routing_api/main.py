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


@app.get("/health", tags=["Status"])
async def health_check():
    """
    Simple health check endpoint to confirm the API is running.
    """
    return {"status": "ok"}

@app.get("/routes", tags=["Routing"])
async def list_routes():
    """Lists all previously generated routes."""
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")
    response = supabase.table('routes').select("*").order('created_at', desc=True).execute()
    return response.data


@app.get("/routes/{route_id}", tags=["Routing"])
async def get_route_details(route_id: int):
    """Gets all stops and customer details for a specific route."""
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    # Fetch stops for the given route_id and join with customer info
    response = supabase.table('stops').select('*, customers(*)').eq('route_id', route_id).execute()
    
    if not response.data:
        raise HTTPException(status_code=404, detail="Route not found")
        
    return response.data

class JobResponse(BaseModel):
    job_id: str

@app.post("/routes/generate", response_model=JobResponse, tags=["Routing"])
async def generate_routes(
    orders_file: UploadFile = File(...),
    num_vehicles: int = Form(...),
    split_mode: str = Form(...),
    route_date_str: str = Form(...),
    hq_lat: float = Form(...),
    hq_lon: float = Form(...),
):
    """
    Accepts order data and triggers a background task to generate routes.
    """
    try:
        orders_content = await orders_file.read()
        orders_content_b64 = base64.b64encode(orders_content).decode('utf-8')

        task = generate_routing_task.delay(
            orders_file_content_b64=orders_content_b64,
            num_vehicles=num_vehicles,
            split_mode=split_mode,
            route_date_str=route_date_str,
            hq_lat=hq_lat,
            hq_lon=hq_lon,
        )
        return {"job_id": task.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start job: {e}")

class StatusResponse(BaseModel):
    job_id: str
    status: str

@app.get("/routes/status/{job_id}", response_model=StatusResponse, tags=["Routing"])
async def get_job_status(job_id: str):
    """
    Checks the status of a background route generation job.
    """
    task_result = AsyncResult(job_id, app=celery_app)
    return {
        "job_id": job_id,
        "status": task_result.status
    }

class ResultResponse(BaseModel):
    job_id: str
    status: str
    result: dict | None = None
    
@app.get("/routes/result/{job_id}", response_model=ResultResponse, tags=["Routing"])
async def get_job_result(job_id: str):
    """
    Retrieves the result of a completed route generation job.
    """
    task_result = AsyncResult(job_id, app=celery_app)
    if not task_result.ready():
        raise HTTPException(status_code=202, detail="Job is not yet complete.")

    if task_result.successful():
        return {
            "job_id": job_id,
            "status": task_result.status,
            "result": task_result.result,
        }
    else: # Task failed
        return {
            "job_id": job_id,
            "status": "FAILURE",
            "result": {"error": str(task_result.info)}, # The exception info
        }
