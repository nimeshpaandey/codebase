import logging
import uuid
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Path, Query
from app.schemas.review import ReviewRequest, ReviewResponse
from app.services.review_orchestrator import ReviewOrchestrator
from app.repositories.review_repository import ReviewRepository

logger = logging.getLogger(__name__)

router = APIRouter()
orchestrator = ReviewOrchestrator()
repo = ReviewRepository()

@router.post("/reviews", response_model=ReviewResponse)
def create_review(request: ReviewRequest):
    try:
        review_id = f"rev_{uuid.uuid4().hex[:12]}"
        
        # Run analyzers & LLM reasoning
        findings = orchestrator.run_review(request)
        
        # Persist review & findings
        repo.save_review(review_id, "completed", findings)
        
        return ReviewResponse(
            review_id=review_id,
            status="completed",
            findings=findings
        )
    except Exception as e:
        logger.exception(f"Error during review processing: {e}")
        raise HTTPException(status_code=500, detail=f"Review failed: {str(e)}")

@router.get("/reviews", response_model=List[Dict[str, Any]])
def list_reviews(limit: int = Query(default=20, ge=1, le=100)):
    """List recent code reviews."""
    return repo.list_reviews(limit=limit)

@router.get("/reviews/{review_id}", response_model=ReviewResponse)
def get_review(review_id: str = Path(..., title="The ID of the review to retrieve")):
    review_data = repo.get_review(review_id)
    if not review_data:
        raise HTTPException(status_code=404, detail=f"Review '{review_id}' not found")
        
    return ReviewResponse(**review_data)
