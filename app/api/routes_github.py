import hmac
import hashlib
import logging
from fastapi import APIRouter, Request, HTTPException, Header
from app.core.config import settings
from app.schemas.review import ReviewRequest
from app.services.review_orchestrator import ReviewOrchestrator
from app.repositories.review_repository import ReviewRepository
import uuid

logger = logging.getLogger(__name__)

router = APIRouter()
orchestrator = ReviewOrchestrator()
repo = ReviewRepository()

def verify_github_signature(payload: bytes, signature_header: str) -> bool:
    if not signature_header:
        return False
    
    secret = settings.GITHUB_WEBHOOK_SECRET.encode("utf-8")
    hash_object = hmac.new(secret, msg=payload, digestmod=hashlib.sha256)
    expected_signature = "sha256=" + hash_object.hexdigest()
    
    return hmac.compare_digest(expected_signature, signature_header)

@router.post("/webhooks/github")
async def github_webhook(request: Request, x_hub_signature_256: str = Header(None)):
    payload = await request.body()
    
    if not verify_github_signature(payload, x_hub_signature_256):
        logger.warning("Rejected webhook: Invalid or missing GitHub signature")
        raise HTTPException(status_code=401, detail="Invalid GitHub signature")
    
    data = await request.json()
    event_type = request.headers.get("X-GitHub-Event")
    
    if event_type == "pull_request":
        action = data.get("action")
        pr = data.get("pull_request", {})
        pr_number = pr.get("number")
        repo_name = data.get("repository", {}).get("full_name")
        
        if action in ["opened", "synchronize", "reopened"]:
            # If code snippet/patch is provided directly in test payloads, run analysis
            code_snippet = data.get("code") or pr.get("diff_snippet")
            findings_count = 0
            review_id = f"gh_pr_{pr_number}_{uuid.uuid4().hex[:6]}"
            
            if code_snippet:
                req = ReviewRequest(
                    language="cpp",
                    code=code_snippet,
                    filename=data.get("filename", "pr_patch.cpp")
                )
                findings = orchestrator.run_review(req)
                repo.save_review(review_id, "completed", findings)
                findings_count = len(findings)

            return {
                "status": "accepted",
                "message": f"Review processed for PR #{pr_number} in {repo_name}",
                "review_id": review_id if code_snippet else None,
                "findings_count": findings_count
            }
            
    return {"status": "ignored", "message": f"Event '{event_type}' not processed"}
