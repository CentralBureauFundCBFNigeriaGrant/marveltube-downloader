from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
import subprocess
import os
import uuid
import time
import json
from datetime import datetime

app = FastAPI(title="MarvelTube Downloader")

# In-memory job queue (for simplicity; persistent in production)
jobs = {}  # job_id: { status, url, supabase_url, created_at }

@app.get("/")
def root():
    return {"status": "alive", "service": "MarvelTube Downloader", "jobs_pending": len([j for j in jobs.values() if j['status'] == 'pending'])}

@app.post("/submit-job")
async def submit_job(url: str = Query(..., description="YouTube video URL")):
    """
    GitHub calls this to submit a download job.
    Returns a job_id that the Android app will poll for.
    """
    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "status": "pending",
        "url": url,
        "supabase_url": None,
        "created_at": datetime.now().isoformat()
    }
    
    print(f"Job {job_id} submitted: {url}")
    return {"job_id": job_id, "status": "pending"}

@app.get("/poll-job")
async def poll_job(job_id: str = Query(..., description="Job ID to check")):
    """
    GitHub polls this to check if the Android app has completed the download.
    """
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job_id": job_id, "status": job["status"], "supabase_url": job.get("supabase_url")}

@app.get("/next-job")
async def next_job():
    """
    The Android app calls this to get the next pending job.
    """
    pending_jobs = [(jid, j) for jid, j in jobs.items() if j['status'] == 'pending']
    if not pending_jobs:
        return {"has_job": False}
    
    # Get the oldest pending job
    job_id, job = pending_jobs[0]
    job['status'] = 'in_progress'
    
    return {
        "has_job": True,
        "job_id": job_id,
        "url": job['url']
    }

@app.post("/complete-job")
async def complete_job(
    job_id: str = Query(..., description="Job ID"),
    supabase_url: str = Query(..., description="Supabase URL of uploaded video")
):
    """
    The Android app calls this when upload is complete.
    """
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job['status'] = 'completed'
    job['supabase_url'] = supabase_url
    job['completed_at'] = datetime.now().isoformat()
    
    print(f"Job {job_id} completed: {supabase_url}")
    return {"status": "ok"}

@app.get("/health")
def health():
    return {"status": "ok"}

# Cleanup old jobs (older than 1 hour)
@app.on_event("startup")
async def cleanup_old_jobs():
    import threading
    def cleanup():
        while True:
            time.sleep(600)  # Every 10 minutes
            now = datetime.now()
            to_delete = []
            for jid, job in jobs.items():
                created = datetime.fromisoformat(job['created_at'])
                if (now - created).seconds > 3600:
                    to_delete.append(jid)
            for jid in to_delete:
                del jobs[jid]
    threading.Thread(target=cleanup, daemon=True).start()
