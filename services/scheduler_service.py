"""
Adquify Scheduler Service
==========================
Servicio de programación de tareas automáticas usando APScheduler.

Funcionalidades:
- Programar scrapers en intervalos regulares
- Generar reportes automáticos
- Enviar notificaciones periódicas
- Gestión de jobs via API
"""

import os
import logging
from datetime import datetime
from typing import List, Dict, Optional, Callable
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AdquifyScheduler:
    """Scheduler para automatización de tareas en Adquify"""
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.scheduler = AsyncIOScheduler(
            jobstores={'default': MemoryJobStore()},
            job_defaults={
                'coalesce': True,
                'max_instances': 1,
                'misfire_grace_time': 60
            }
        )
        
        # Track job metadata
        self.job_metadata: Dict[str, dict] = {}
        
        # Event listeners
        self.scheduler.add_listener(self._on_job_executed, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(self._on_job_error, EVENT_JOB_ERROR)
        
        self._initialized = True
        logger.info("✅ AdquifyScheduler initialized")
    
    def _on_job_executed(self, event):
        """Callback when job completes successfully"""
        job_id = event.job_id
        if job_id in self.job_metadata:
            self.job_metadata[job_id]['last_run'] = datetime.utcnow().isoformat()
            self.job_metadata[job_id]['runs'] = self.job_metadata[job_id].get('runs', 0) + 1
        logger.info(f"✅ Job '{job_id}' executed successfully")
    
    def _on_job_error(self, event):
        """Callback when job fails"""
        job_id = event.job_id
        if job_id in self.job_metadata:
            self.job_metadata[job_id]['last_error'] = str(event.exception)
            self.job_metadata[job_id]['errors'] = self.job_metadata[job_id].get('errors', 0) + 1
        logger.error(f"❌ Job '{job_id}' failed: {event.exception}")
    
    def start(self):
        """Start the scheduler"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("🚀 Scheduler started")
    
    def stop(self):
        """Stop the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("🛑 Scheduler stopped")
    
    def add_interval_job(
        self,
        job_id: str,
        func: Callable,
        hours: int = 0,
        minutes: int = 0,
        seconds: int = 0,
        description: str = "",
        **kwargs
    ) -> dict:
        """
        Add a job that runs at fixed intervals
        
        Args:
            job_id: Unique identifier for the job
            func: Async function to execute
            hours, minutes, seconds: Interval timing
            description: Human-readable description
            **kwargs: Arguments to pass to the function
        """
        trigger = IntervalTrigger(
            hours=hours,
            minutes=minutes,
            seconds=seconds
        )
        
        job = self.scheduler.add_job(
            func,
            trigger,
            id=job_id,
            replace_existing=True,
            kwargs=kwargs
        )
        
        self.job_metadata[job_id] = {
            'type': 'interval',
            'interval': f"{hours}h {minutes}m {seconds}s",
            'description': description,
            'created_at': datetime.utcnow().isoformat(),
            'status': 'active'
        }
        
        logger.info(f"📅 Added interval job: {job_id} (every {hours}h {minutes}m {seconds}s)")
        return self.get_job_info(job_id)
    
    def add_cron_job(
        self,
        job_id: str,
        func: Callable,
        cron_expr: str = None,
        hour: int = None,
        minute: int = 0,
        day_of_week: str = None,
        description: str = "",
        **kwargs
    ) -> dict:
        """
        Add a job that runs on a cron schedule
        
        Args:
            job_id: Unique identifier
            func: Async function to execute
            cron_expr: Full cron expression (optional)
            hour, minute, day_of_week: Individual cron fields
            description: Human-readable description
        """
        if cron_expr:
            trigger = CronTrigger.from_crontab(cron_expr)
        else:
            trigger = CronTrigger(
                hour=hour,
                minute=minute,
                day_of_week=day_of_week
            )
        
        job = self.scheduler.add_job(
            func,
            trigger,
            id=job_id,
            replace_existing=True,
            kwargs=kwargs
        )
        
        schedule_str = cron_expr or f"{minute} {hour} * * {day_of_week or '*'}"
        self.job_metadata[job_id] = {
            'type': 'cron',
            'schedule': schedule_str,
            'description': description,
            'created_at': datetime.utcnow().isoformat(),
            'status': 'active'
        }
        
        logger.info(f"📅 Added cron job: {job_id} ({schedule_str})")
        return self.get_job_info(job_id)
    
    def remove_job(self, job_id: str) -> bool:
        """Remove a scheduled job"""
        try:
            self.scheduler.remove_job(job_id)
            if job_id in self.job_metadata:
                del self.job_metadata[job_id]
            logger.info(f"🗑️ Removed job: {job_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove job {job_id}: {e}")
            return False
    
    def pause_job(self, job_id: str) -> bool:
        """Pause a job"""
        try:
            self.scheduler.pause_job(job_id)
            if job_id in self.job_metadata:
                self.job_metadata[job_id]['status'] = 'paused'
            logger.info(f"⏸️ Paused job: {job_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to pause job {job_id}: {e}")
            return False
    
    def resume_job(self, job_id: str) -> bool:
        """Resume a paused job"""
        try:
            self.scheduler.resume_job(job_id)
            if job_id in self.job_metadata:
                self.job_metadata[job_id]['status'] = 'active'
            logger.info(f"▶️ Resumed job: {job_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to resume job {job_id}: {e}")
            return False
    
    def run_job_now(self, job_id: str) -> bool:
        """Trigger a job to run immediately"""
        try:
            job = self.scheduler.get_job(job_id)
            if job:
                self.scheduler.modify_job(job_id, next_run_time=datetime.now())
                logger.info(f"🏃 Triggered immediate run: {job_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to run job {job_id}: {e}")
            return False
    
    def get_job_info(self, job_id: str) -> Optional[dict]:
        """Get detailed info about a job"""
        job = self.scheduler.get_job(job_id)
        if not job:
            return None
        
        meta = self.job_metadata.get(job_id, {})
        return {
            'id': job_id,
            'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
            **meta
        }
    
    def list_jobs(self) -> List[dict]:
        """List all scheduled jobs"""
        jobs = []
        for job in self.scheduler.get_jobs():
            info = self.get_job_info(job.id)
            if info:
                jobs.append(info)
        return jobs
    
    def get_stats(self) -> dict:
        """Get scheduler statistics"""
        jobs = self.scheduler.get_jobs()
        active = sum(1 for j in jobs if j.next_run_time)
        paused = len(jobs) - active
        
        total_runs = sum(m.get('runs', 0) for m in self.job_metadata.values())
        total_errors = sum(m.get('errors', 0) for m in self.job_metadata.values())
        
        return {
            'running': self.scheduler.running,
            'total_jobs': len(jobs),
            'active_jobs': active,
            'paused_jobs': paused,
            'total_runs': total_runs,
            'total_errors': total_errors
        }


# ========== PREDEFINED TASKS ==========

async def scraper_task(supplier_code: str):
    """Task to run a scraper for a supplier"""
    import httpx
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"http://localhost:8001/scrapers/run/{supplier_code}",
                timeout=300
            )
            logger.info(f"Scraper task for {supplier_code}: {response.status_code}")
        except Exception as e:
            logger.error(f"Scraper task failed for {supplier_code}: {e}")


async def report_task():
    """Task to generate and send catalog report"""
    import httpx
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "http://localhost:8001/internal-catalog/export/csv",
                timeout=60
            )
            logger.info(f"Report generated: {response.json()}")
        except Exception as e:
            logger.error(f"Report task failed: {e}")


# ========== GLOBAL INSTANCE ==========

scheduler = AdquifyScheduler()


def get_scheduler() -> AdquifyScheduler:
    """Get the global scheduler instance"""
    return scheduler
