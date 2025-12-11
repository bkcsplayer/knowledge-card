"""
Upload API Router
Handles file uploads (images, documents)
"""

import os
import uuid
import aiofiles
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from typing import List
from datetime import datetime

router = APIRouter(prefix="/api/v1/upload", tags=["Upload"])

# Upload directory
UPLOAD_DIR = "/app/uploads"
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
ALLOWED_DOC_TYPES = {"application/pdf", "text/plain", "text/markdown"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Ensure upload directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(f"{UPLOAD_DIR}/images", exist_ok=True)
os.makedirs(f"{UPLOAD_DIR}/documents", exist_ok=True)


@router.post("/image")
async def upload_image(file: UploadFile = File(...)):
    """
    Upload an image file
    
    Supports: JPEG, PNG, GIF, WebP
    Max size: 10MB
    """
    # Validate file type
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_IMAGE_TYPES)}"
        )
    
    # Read file content
    content = await file.read()
    
    # Validate file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Max 10MB")
    
    # Generate unique filename
    ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = f"{UPLOAD_DIR}/images/{filename}"
    
    # Save file
    async with aiofiles.open(filepath, "wb") as f:
        await f.write(content)
    
    return {
        "status": "success",
        "filename": filename,
        "url": f"/api/v1/upload/images/{filename}",
        "size": len(content),
        "content_type": file.content_type,
        "uploaded_at": datetime.utcnow().isoformat()
    }


@router.post("/images/batch")
async def upload_images_batch(files: List[UploadFile] = File(...)):
    """Upload multiple images at once"""
    results = []
    
    for file in files:
        if file.content_type not in ALLOWED_IMAGE_TYPES:
            results.append({
                "filename": file.filename,
                "status": "error",
                "message": "Invalid file type"
            })
            continue
        
        content = await file.read()
        
        if len(content) > MAX_FILE_SIZE:
            results.append({
                "filename": file.filename,
                "status": "error", 
                "message": "File too large"
            })
            continue
        
        ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
        filename = f"{uuid.uuid4().hex}.{ext}"
        filepath = f"{UPLOAD_DIR}/images/{filename}"
        
        async with aiofiles.open(filepath, "wb") as f:
            await f.write(content)
        
        results.append({
            "original_name": file.filename,
            "filename": filename,
            "url": f"/api/v1/upload/images/{filename}",
            "status": "success",
            "size": len(content)
        })
    
    return {
        "total": len(files),
        "successful": sum(1 for r in results if r.get("status") == "success"),
        "results": results
    }


@router.get("/images/{filename}")
async def get_image(filename: str):
    """Serve an uploaded image"""
    filepath = f"{UPLOAD_DIR}/images/{filename}"
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Image not found")
    
    return FileResponse(filepath)


@router.delete("/images/{filename}")
async def delete_image(filename: str):
    """Delete an uploaded image"""
    filepath = f"{UPLOAD_DIR}/images/{filename}"
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Image not found")
    
    os.remove(filepath)
    
    return {"status": "deleted", "filename": filename}


@router.get("/list/images")
async def list_images():
    """List all uploaded images"""
    images_dir = f"{UPLOAD_DIR}/images"
    
    if not os.path.exists(images_dir):
        return {"images": [], "count": 0}
    
    files = []
    for filename in os.listdir(images_dir):
        filepath = os.path.join(images_dir, filename)
        if os.path.isfile(filepath):
            stat = os.stat(filepath)
            files.append({
                "filename": filename,
                "url": f"/api/v1/upload/images/{filename}",
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
    
    # Sort by modified time (newest first)
    files.sort(key=lambda x: x["modified"], reverse=True)
    
    return {"images": files, "count": len(files)}

