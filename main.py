from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
import subprocess
import os
import uuid
import time
import json
from datetime import datetime

app = FastAPI(title="MarvelTube Downloader")

jobs = {}

@app.get("/")
def root():
    return {"status": "alive", "service": "MarvelTube Downloader v2.0", "jobs_pending": len([j for j in jobs.values() if j['status'] == 'pending'])}

@app.get("/submit-job")
async def submit_job(url: str = Query(..., description="YouTube video URL")):
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
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job_id": job_id, "status": job["status"], "supabase_url": job.get("supabase_url")}

@app.get("/next-job")
async def next_job():
    pending_jobs = [(jid, j) for jid, j in jobs.items() if j['status'] == 'pending']
    if not pending_jobs:
        return {"has_job": False}
    job_id, job = pending_jobs[0]
    job['status'] = 'in_progress'
    return {"has_job": True, "job_id": job_id, "url": job['url']}

@app.post("/complete-job")
async def complete_job(
    job_id: str = Query(..., description="Job ID"),
    supabase_url: str = Query(..., description="Supabase URL of uploaded video")
):
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
