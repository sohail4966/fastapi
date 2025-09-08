#  all api endpoints related to indicators
"""
    This code defines an API router for handling CRUD operations on indicators using FastAPI.
    The router includes endpoints for creating, listing, retrieving, updating, and deleting indicators.
"""

from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException
from clickhouse_connect.driver.client import Client
from app.dependency import get_db_client
from app.indicators.repo import IndicatorCreate, IndicatorOut, IndicatorUpdate
from app.indicators.service import IndicatorService
import logging

indicator_router = APIRouter(prefix="/indicators", tags=["indicators"])
logger = logging.getLogger(__name__)

def get_service(client: Client = Depends(get_db_client)):
    return IndicatorService(client)


@indicator_router.post("/", response_model=Dict[str, str])
async def create_indicator(payload: IndicatorCreate, svc: IndicatorService = Depends(get_service)):
    """
    Asynchronously create a new indicator using the provided payload and IndicatorService.
    @param payload: IndicatorCreate - The payload containing information for creating the indicator.
    @param svc: IndicatorService - The service used for creating the indicator.
    @returns: dict - A dictionary containing the UUID of the created indicator.
    """
    """Create a new indicator. Returns the UUID of created indicator."""
    try:
            iid = svc.create_indicator(payload)
            return {"id": iid}
    except HTTPException:
            raise
    except Exception as ex:
            logger.info("create_indicator error")
            raise HTTPException(status_code=500, detail=str(ex))

@indicator_router.get("/", response_model=List[IndicatorOut])
async def list_indicators(limit: int = 100, offset: int = 0, svc: IndicatorService = Depends(get_service)):
    """
    List indicators asynchronously with optional limit and offset parameters.
    @param limit - The maximum number of items to retrieve (default is 100).
    @param offset - The offset from where to start retrieving items (default is 0).
    @param svc - An instance of the IndicatorService class (obtained from get_service dependency).
    @return A list of items retrieved based on the limit and offset parameters.
    """
    items = svc.list_indicators(limit=limit, offset=offset)
    return items    


@indicator_router.get("/{id_or_name}", response_model=IndicatorOut)
async def get_indicator(id_or_name: str, svc: IndicatorService = Depends(get_service)):
        """
            Retrieve an indicator from the service by its ID or name.
            @param id_or_name - The ID or name of the indicator to retrieve.
            @raises HTTPException with status code 404 and detail message "indicator not found" if the indicator is not found.
            @return The retrieved indicator.
            """
        item = svc.get_indicator(id_or_name)
        if not item:
            raise HTTPException(status_code=404, detail="indicator not found")
        return item


@indicator_router.put("/{id}")
async def update_indicator(id: str, payload: IndicatorUpdate, svc: IndicatorService = Depends(get_service)):
    """
    Update an indicator asynchronously using the provided id and payload.
    @param id - The id of the indicator to update.
    @param payload - The data to update the indicator with.
    @param svc - The IndicatorService dependency.
    @raises HTTPException if the indicator is not found.
    @return A dictionary indicating the status of the update.
    """
    ok = svc.update_indicator(id, payload)
    if not ok:
        raise HTTPException(status_code=404, detail="indicator not found")
    return {"status": "ok"}


@indicator_router.delete("/{id}")
async def delete_indicator(id: str, svc: IndicatorService = Depends(get_service)):
    """
        Delete an indicator with the given ID using the service.
        @param id - The ID of the indicator to be deleted.
        @raises HTTPException if the deletion fails.
        @return A dictionary with the status of the deletion.
    """
    ok = svc.delete_indicator(id)
    if not ok:
            raise HTTPException(status_code=500, detail="failed to delete")
    return {"status": "ok"}