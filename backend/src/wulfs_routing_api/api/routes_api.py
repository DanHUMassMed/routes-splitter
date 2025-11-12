import base64
import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi import FastAPI, HTTPException
from wulfs_routing_api.models.stops.supabase_stop import SupabaseStop
from wulfs_routing_api.services.stops_service import StopService
from wulfs_routing_api.models.routes.supabase_route import SupabaseRoute
from wulfs_routing_api.services.route_service import RouteService
from wulfs_routing_api.celery_app import celery_app
from wulfs_routing_api.tasks.celery_tasks import generate_routing_task
from wulfs_routing_api.models.supabase_db import supabase
from pydantic import BaseModel
from celery.result import AsyncResult
import logging
logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "WARNING").upper())

router = APIRouter()

def get_service() -> RouteService:
    return RouteService(SupabaseRoute())

@router.get("/routes", tags=["Routing"])
async def list_routes(service: RouteService = Depends(get_service)):
    """Lists all previously generated routes."""
    try:
        return service.list_routes()
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/routes/{route_id}/stops", tags=["Routing"])
async def get_stops_for_route(route_id: int):
    """Gets all stops details for a specific route."""
    try:
        service = StopService(SupabaseStop())
        return service.get_stops_for_route(route_id)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))

class JobResponse(BaseModel):
    job_id: str

@router.post("/routes/generate", response_model=JobResponse, tags=["Routing"])
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

@router.get("/routes/{job_id}/status", response_model=StatusResponse, tags=["Routing"])
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
    
@router.get("/routes/{job_id}/results", response_model=ResultResponse, tags=["Routing"])
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
