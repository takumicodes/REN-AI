"""
Media & Assets API Endpoints
Provides authenticated, path-traversal-protected media delivery and asset metadata inspection.
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import FileResponse
from typing import Optional

from ren.media.image_asset import image_asset_manager
from api.user_session import get_current_user_id

router = APIRouter(prefix="/assets", tags=["Assets"])


@router.get("/images/{asset_id}")
async def get_image_asset(
    asset_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Securely serves generated image media.
    Guarantees user ownership, path-traversal protection, and proper MIME headers.
    """
    asset = image_asset_manager.get_asset(asset_id, user_id=user_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Image asset not found or access denied.")

    file_path = image_asset_manager.get_asset_file_path(asset_id)
    if not file_path or not file_path.exists():
        raise HTTPException(status_code=404, detail="Media file unavailable.")

    # Path traversal protection
    base_dir = image_asset_manager.base_dir.resolve()
    if not str(file_path.resolve()).startswith(str(base_dir)):
        raise HTTPException(status_code=403, detail="Access to path forbidden.")

    return FileResponse(
        path=str(file_path),
        media_type=asset.mime_type,
        headers={"Cache-Control": "public, max-age=86400"}
    )


@router.get("/images/{asset_id}/info")
async def get_image_asset_info(
    asset_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Returns pure JSON asset metadata without filesystem paths."""
    asset = image_asset_manager.get_asset(asset_id, user_id=user_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset metadata not found.")
    return asset.to_dict()
