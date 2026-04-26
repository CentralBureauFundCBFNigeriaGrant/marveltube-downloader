from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
import subprocess
import os
import uuid
import shutil

app = FastAPI(title="MarvelTube Downloader")

@app.get("/")
def root():
    return {"status": "alive", "service": "MarvelTube Downloader"}

@app.get("/download")
async def download_video(url: str = Query(..., description="YouTube video URL")):
    """
    Downloads a YouTube video and returns the MP4 file.
    The caller is responsible for deleting the file after use.
    """
    # Create a unique filename
    job_id = str(uuid.uuid4())[:8]
    output_template = f"/tmp/{job_id}.%(ext)s"
    
    try:
        # Download the video using yt-dlp
        cmd = [
            'yt-dlp',
            '-f', 'best[height<=1920]',
            '-o', output_template,
            '--no-playlist',
            '--restrict-filenames',
            '--socket-timeout', '30',
            '--retries', '3',
            url
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            raise HTTPException(
                status_code=400, 
                detail=f"Download failed: {result.stderr[:500]}"
            )
        
        # Find the downloaded file
        downloaded_file = None
        for f in os.listdir('/tmp'):
            if f.startswith(job_id) and f.endswith(('.mp4', '.mov', '.webm')):
                downloaded_file = f"/tmp/{f}"
                break
        
        if not downloaded_file:
            raise HTTPException(status_code=500, detail="File not found after download")
        
        # Return the file
        return FileResponse(
            downloaded_file,
            media_type="video/mp4",
            filename=f"marveltube_{job_id}.mp4",
            background=None  # File will be cleaned up after response
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health():
    return {"status": "ok"}
