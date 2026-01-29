"""
Adquify Scheduler API Router
=============================
Endpoints para gestionar tareas programadas.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from services.scheduler_service import get_scheduler, scraper_task, report_task

router = APIRouter(prefix="/scheduler", tags=["scheduler"])


# ========== MODELS ==========

class IntervalJobRequest(BaseModel):
    job_id: str
    supplier_code: Optional[str] = None
    hours: int = 0
    minutes: int = 0
    seconds: int = 0
    description: str = ""


class CronJobRequest(BaseModel):
    job_id: str
    supplier_code: Optional[str] = None
    cron_expr: Optional[str] = None
    hour: Optional[int] = None
    minute: int = 0
    day_of_week: Optional[str] = None
    description: str = ""


# ========== ENDPOINTS ==========

@router.get("/jobs")
def list_jobs():
    """Lista todas las tareas programadas"""
    scheduler = get_scheduler()
    return {
        "jobs": scheduler.list_jobs(),
        "stats": scheduler.get_stats()
    }


@router.get("/jobs/{job_id}")
def get_job(job_id: str):
    """Obtiene detalles de una tarea"""
    scheduler = get_scheduler()
    job = scheduler.get_job_info(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/jobs/interval")
def create_interval_job(request: IntervalJobRequest):
    """Crea una tarea que se ejecuta a intervalos regulares"""
    scheduler = get_scheduler()
    
    # Determine function based on job type
    if request.supplier_code:
        func = scraper_task
        kwargs = {"supplier_code": request.supplier_code}
    else:
        func = report_task
        kwargs = {}
    
    job = scheduler.add_interval_job(
        job_id=request.job_id,
        func=func,
        hours=request.hours,
        minutes=request.minutes,
        seconds=request.seconds,
        description=request.description,
        **kwargs
    )
    
    return {"success": True, "job": job}


@router.post("/jobs/cron")
def create_cron_job(request: CronJobRequest):
    """Crea una tarea con expresión cron"""
    scheduler = get_scheduler()
    
    if request.supplier_code:
        func = scraper_task
        kwargs = {"supplier_code": request.supplier_code}
    else:
        func = report_task
        kwargs = {}
    
    job = scheduler.add_cron_job(
        job_id=request.job_id,
        func=func,
        cron_expr=request.cron_expr,
        hour=request.hour,
        minute=request.minute,
        day_of_week=request.day_of_week,
        description=request.description,
        **kwargs
    )
    
    return {"success": True, "job": job}


@router.delete("/jobs/{job_id}")
def delete_job(job_id: str):
    """Elimina una tarea programada"""
    scheduler = get_scheduler()
    success = scheduler.remove_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"success": True, "message": f"Job {job_id} deleted"}


@router.post("/jobs/{job_id}/pause")
def pause_job(job_id: str):
    """Pausa una tarea"""
    scheduler = get_scheduler()
    success = scheduler.pause_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"success": True, "message": f"Job {job_id} paused"}


@router.post("/jobs/{job_id}/resume")
def resume_job(job_id: str):
    """Reanuda una tarea pausada"""
    scheduler = get_scheduler()
    success = scheduler.resume_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"success": True, "message": f"Job {job_id} resumed"}


@router.post("/jobs/{job_id}/run")
def run_job_now(job_id: str):
    """Ejecuta una tarea inmediatamente"""
    scheduler = get_scheduler()
    success = scheduler.run_job_now(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"success": True, "message": f"Job {job_id} triggered"}


@router.get("/stats")
def get_scheduler_stats():
    """Obtiene estadísticas del scheduler"""
    scheduler = get_scheduler()
    return scheduler.get_stats()
