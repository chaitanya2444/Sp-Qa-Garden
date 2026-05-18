from fastapi import APIRouter, HTTPException
from app.schemas import FailureInput, TriageOutput, TriageResultList
from app.services.triage_service import process_failure
from app.services import storage_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


from fastapi.concurrency import run_in_threadpool
from app.socket_manager import manager

@router.post("/triage", response_model=TriageOutput)
async def triage_failure(payload: FailureInput):
    """
    Process a test failure and return triage results.
    The result is automatically stored and can be retrieved later via GET endpoints.
    """
    try:
        logger.info(f"Received triage request for: {payload.test_name} (Run ID: {payload.run_id})")
        
        # Process the failure (natively async now)
        result = await process_failure(payload)
        
        # Persistence
        # Store the result and add the ID to the response
        result_id = storage_service.store_result(result)
        result["id"] = result_id
        
        # Broadcast to dashboard via WebSocket if run_id is present
        if payload.run_id:
            await manager.broadcast(payload.run_id, {
                "event": "completed",
                "agent": "triage",
                "status": "completed",
                "result": result
            })
        
        return result
    except Exception as e:
        # Log the full error for debugging
        logger.error(f"Error processing triage request: {e}", exc_info=True)
        
        # Fallback so the API never crashes with 500
        return TriageOutput(
            title="API Internal Error",
            description=f"Error while processing triage request: {str(e)}",
            raw_failure_text="",
            status="failed",
        )


@router.get("/triage/latest", response_model=TriageOutput)
def get_latest_triage_result():
    """
    Retrieve the most recently executed test result.
    This returns the latest triage result based on creation time.
    """
    result = storage_service.get_latest_result()
    if result is None:
        raise HTTPException(status_code=404, detail="No triage results found. Run a test first.")
    return result


@router.get("/triage/{result_id}", response_model=TriageOutput)
def get_triage_result(result_id: str):
    """
    Retrieve a specific triage result by its ID.
    """
    result = storage_service.get_result(result_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Triage result with ID '{result_id}' not found")
    return result


@router.post("/complete/{run_id}")
async def complete_run(run_id: str):
    """
    Signal that all failures for a run have been submitted.
    Ensures Triage turns Green (100%) even if 0 failures.
    """
    storage_service.mark_run_completed(run_id)
    
    # Broadcast completion to WebSocket
    results = storage_service.get_results_by_run_id(run_id)
    await manager.broadcast(run_id, {
        "event": "completed",
        "agent": "triage",
        "status": "completed",
        "percent": 100,
        "data": {"results": results}
    })
    
    return {"status": "completed", "run_id": run_id}


@router.get("/triage", response_model=TriageResultList)
def list_triage_results():
    """
    List all stored triage results.
    Returns results sorted by creation time (newest first).
    """
    results = storage_service.get_all_results()
    return TriageResultList(
        total=len(results),
        results=results
    )





@router.delete("/triage/{result_id}")
def delete_triage_result(result_id: str):
    """
    Delete a specific triage result by its ID.
    """
    deleted = storage_service.delete_result(result_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Triage result with ID '{result_id}' not found")
    return {"message": f"Triage result '{result_id}' deleted successfully"}


@router.get("/stats")
def get_triage_stats():
    """
    Get comprehensive statistics about bug triage activity.
    Returns metrics like total bugs generated, bugs by run, AI provider usage, etc.
    """
    all_results = storage_service.get_all_results()
    
    # Total bugs generated
    total_bugs = len(all_results)
    
    # Bugs by run_id
    bugs_by_run = {}
    for result in all_results:
        run_id = result.get("run_id", "unknown")
        bugs_by_run[run_id] = bugs_by_run.get(run_id, 0) + 1
    
    # AI provider usage (detect from description)
    ai_generated = 0
    rule_based = 0
    for result in all_results:
        desc = result.get("description", "")
        if "Bug description generation failed" in desc or desc.startswith("The test failed"):
            rule_based += 1
        else:
            ai_generated += 1
    
    # Recent activity (last 10 bugs)
    recent_bugs = sorted(
        all_results,
        key=lambda x: x.get("created_at", ""),
        reverse=True
    )[:10]
    
    # Bug categories (from triage_label)
    categories = {}
    for result in all_results:
        label = result.get("triage_label", "Unknown")
        categories[label] = categories.get(label, 0) + 1
    
    return {
        "total_bugs": total_bugs,
        "ai_generated_bugs": ai_generated,
        "rule_based_bugs": rule_based,
        "bugs_by_run": bugs_by_run,
        "bug_categories": categories,
        "recent_bugs": [
            {
                "id": bug.get("id"),
                "title": bug.get("title"),
                "created_at": bug.get("created_at"),
                "run_id": bug.get("run_id"),
                "category": bug.get("triage_label")
            }
            for bug in recent_bugs
        ]
    }

