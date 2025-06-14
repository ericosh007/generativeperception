"""
GPL API Routes
REST API endpoints for the web interface
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, Optional

api_router = APIRouter()

# Global state (in production, use proper state management)
processing_state = {
    "is_processing": False,
    "current_source": None,
    "frames_processed": 0,
    "telemetry": {}
}


class ProcessingRequest(BaseModel):
    source: str  # "webcam" or file path
    

class ProcessingResponse(BaseModel):
    status: str
    message: str
    

@api_router.get("/status")
async def get_status() -> Dict[str, Any]:
    """Get current processing status"""
    return {
        "is_processing": processing_state["is_processing"],
        "current_source": processing_state["current_source"],
        "frames_processed": processing_state["frames_processed"]
    }


@api_router.post("/process/start")
async def start_processing(
    request: ProcessingRequest,
    background_tasks: BackgroundTasks
) -> ProcessingResponse:
    """Start video processing"""
    if processing_state["is_processing"]:
        raise HTTPException(status_code=400, detail="Processing already in progress")
    
    processing_state["is_processing"] = True
    processing_state["current_source"] = request.source
    processing_state["frames_processed"] = 0
    
    # Note: In the actual implementation, this would trigger the processing
    # For now, we'll just update the state
    
    return ProcessingResponse(
        status="started",
        message=f"Started processing from {request.source}"
    )


@api_router.post("/process/stop")
async def stop_processing() -> ProcessingResponse:
    """Stop video processing"""
    if not processing_state["is_processing"]:
        raise HTTPException(status_code=400, detail="No processing in progress")
    
    processing_state["is_processing"] = False
    processing_state["current_source"] = None
    
    return ProcessingResponse(
        status="stopped",
        message="Processing stopped"
    )


@api_router.get("/telemetry/current")
async def get_current_telemetry() -> Dict[str, Any]:
    """Get current telemetry data"""
    return processing_state.get("telemetry", {})


@api_router.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint"""
    return {"status": "healthy", "service": "gpl"}