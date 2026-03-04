from typing import Annotated

from aiohttp import ClientSession
from fastapi import APIRouter, Depends, Form, Response, Security
from pydantic import BaseModel
from sqlmodel import Session

from app.internal.audiobookshelf.client import FolderAvailability, abs_check_paths_available
from app.internal.auth.authentication import APIKeyAuth, DetailedUser

from app.internal.models import GroupEnum
from app.internal.postprocessing.config import postprocessing_config
from app.internal.audiobookshelf.config import abs_config
from app.util.connection import get_connection
from app.util.db import get_session

router = APIRouter(prefix="/postprocessing")


class PostProcessingResponse(BaseModel):
    auto_moving: bool
    auto_moving_dependencies_valid: bool
    required_folders: list[FolderAvailability]


@router.get("")
async def read_postprocessing(
    session: Annotated[Session, Depends(get_session)],
    client_session: Annotated[ClientSession, Depends(get_connection)],
    admin_user: Annotated[DetailedUser, Security(APIKeyAuth(GroupEnum.admin))],
):
    _ = admin_user
    auto_moving = postprocessing_config.get_auto_moving(session)
    abs_valid = abs_config.is_valid(session)
    if abs_valid:
        folders = await abs_check_paths_available(session, client_session) or []
    else:
        folders = []

    return PostProcessingResponse(
        auto_moving=auto_moving or False, 
        auto_moving_dependencies_valid=abs_valid,
        required_folders=folders
    )


@router.put("/auto-moving")
def update_postprocessing_auto_moving(
    session: Annotated[Session, Depends(get_session)],
    admin_user: Annotated[DetailedUser, Security(APIKeyAuth(GroupEnum.admin))],
    check_auto_moving: Annotated[bool, Form()],
):
    _ = admin_user
    postprocessing_config.set_auto_moving(session, check_auto_moving)
    return Response(status_code=204)
