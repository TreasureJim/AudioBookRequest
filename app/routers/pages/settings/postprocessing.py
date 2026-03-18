from typing import Annotated, Optional

from aiohttp import ClientSession
from fastapi import APIRouter, Depends, Form, Response, Security
from sqlmodel import Session

from app.internal.auth.authentication import ABRAuth, DetailedUser
from app.internal.downloadclient.client import qBittorrentClient
from app.internal.models import GroupEnum
from app.routers.api.settings.postprocessing import (
    read_postprocessing as api_read_postprocessing,
)
from app.routers.api.settings.postprocessing import (
    update_postprocessing_auto_moving as api_update_postprocessing_auto_moving,
    update_postprocessing_disable_hardlinking as api_update_postprocessing_disable_hardlinking,
)
from app.util.connection import get_connection
from app.util.db import get_session
from app.util.downloadclient import get_global_downloadclient
from app.util.templates import catalog_response

router = APIRouter(prefix="/postprocessing")


@router.get("")
async def read_postprocessing(
    # request: Request,
    session: Annotated[Session, Depends(get_session)],
    client_session: Annotated[ClientSession, Depends(get_connection)],
    admin_user: Annotated[DetailedUser, Security(ABRAuth(GroupEnum.admin))],
    downloadclient: Annotated[
        Optional[qBittorrentClient], Depends(get_global_downloadclient)
    ],
):
    results = await api_read_postprocessing(session, client_session, admin_user, downloadclient)

    return catalog_response(
        "Settings.PostProcessing",
        user=admin_user,
        page="postprocessing",
        auto_moving=results.auto_moving,
        auto_moving_dependencies_valid=results.auto_moving_dependencies_valid,
        required_folders=results.required_folders,
        disable_hardlinking=results.disable_hardlinking,
    )


@router.put("/hx-check-auto-moving")
async def update_postprocessing_auto_moving(
    session: Annotated[Session, Depends(get_session)],
    admin_user: Annotated[DetailedUser, Security(ABRAuth(GroupEnum.admin))],
    check_auto_moving: Annotated[bool, Form()],
):
    await api_update_postprocessing_auto_moving(
        check_auto_moving=check_auto_moving, session=session, admin_user=admin_user
    )
    return Response(status_code=204, headers={"HX-Refresh": "true"})

@router.put("/hx-check-disable-hardlinking")
async def update_postprocessing_disable_hardlinking(
    session: Annotated[Session, Depends(get_session)],
    admin_user: Annotated[DetailedUser, Security(ABRAuth(GroupEnum.admin))],
    check_disable_hardlinking: Annotated[bool, Form()],
):
    await api_update_postprocessing_disable_hardlinking(
        check_disable_hardlinking=check_disable_hardlinking, session=session, admin_user=admin_user
    )
    return Response(status_code=204, headers={"HX-Refresh": "true"})
