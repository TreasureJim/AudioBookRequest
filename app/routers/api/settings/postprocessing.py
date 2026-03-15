from typing import Annotated, Optional

from aiohttp import ClientSession
from fastapi import APIRouter, Depends, Form, Response, Security
from pydantic import BaseModel
from sqlmodel import Session

from app.internal.audiobookshelf.client import abs_check_paths_available
from app.internal.auth.authentication import APIKeyAuth, DetailedUser

from app.internal.downloadclient.client import qBittorrentClient
from app.internal.downloadclient.config import downclient_config
from app.internal.downloadclient.util import (
    check_downloadclient_category_folders_available,
)
from app.internal.folders import FolderAvailability
from app.internal.models import GroupEnum
from app.internal.postprocessing.config import postprocessing_config
from app.internal.audiobookshelf.config import abs_config
from app.util.connection import get_connection
from app.util.db import get_session
from app.util.downloadclient import (
    get_global_downloadclient,
    start_download_monitor,
    stop_download_monitor,
)

router = APIRouter(prefix="/postprocessing")


class PostProcessingResponse(BaseModel):
    auto_moving: bool
    auto_moving_dependencies_valid: bool
    required_folders: list[FolderAvailability]
    disable_hardlinking: bool


@router.get("")
async def read_postprocessing(
    session: Annotated[Session, Depends(get_session)],
    client_session: Annotated[ClientSession, Depends(get_connection)],
    admin_user: Annotated[DetailedUser, Security(APIKeyAuth(GroupEnum.admin))],
    downloadclient: Annotated[
        Optional[qBittorrentClient], Depends(get_global_downloadclient)
    ],
):
    _ = admin_user
    auto_moving = postprocessing_config.get_auto_moving(session)
    folders: list[FolderAvailability] = []

    if abs_valid := abs_config.is_valid(session):
        folders.extend(await abs_check_paths_available(session, client_session) or [])

    if (
        downclient_valid := (
            downclient_config.is_valid(session)
            and downclient_config.get_category(session) is not None
        )
    ) and downloadclient:
        folders.append(
            await check_downloadclient_category_folders_available(
                session, downloadclient
            )
        )

    if not (abs_valid and downclient_valid):
        auto_moving = False
        postprocessing_config.set_auto_moving(session, False)

    return PostProcessingResponse(
        auto_moving=auto_moving or False,
        auto_moving_dependencies_valid=abs_valid and downclient_valid,
        required_folders=folders,
        disable_hardlinking=postprocessing_config.get_disable_hardlinking(session) or False
    )


@router.put("/auto-moving")
async def update_postprocessing_auto_moving(
    session: Annotated[Session, Depends(get_session)],
    admin_user: Annotated[DetailedUser, Security(APIKeyAuth(GroupEnum.admin))],
    check_auto_moving: Annotated[bool, Form()],
):
    _ = admin_user
    postprocessing_config.set_auto_moving(session, check_auto_moving)
    if check_auto_moving:
        start_download_monitor()
    else:
        await stop_download_monitor()

    return Response(status_code=204)

@router.put("/disable-hardlinking")
async def update_postprocessing_disable_hardlinking(
    session: Annotated[Session, Depends(get_session)],
    admin_user: Annotated[DetailedUser, Security(APIKeyAuth(GroupEnum.admin))],
    check_disable_hardlinking: Annotated[bool, Form()],
):
    _ = admin_user
    postprocessing_config.set_disable_hardlinking(session, check_disable_hardlinking)

    return Response(status_code=204)
