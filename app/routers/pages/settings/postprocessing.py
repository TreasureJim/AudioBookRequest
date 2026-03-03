from typing import Annotated

from fastapi import APIRouter, Depends, Form, Response, Security
from pydantic import BaseModel
from sqlmodel import Session

from app.internal.auth.authentication import ABRAuth, DetailedUser
from app.internal.downloadclient.client import qBittorrentClient
from app.internal.models import GroupEnum
from app.util.db import get_session
from app.util.templates import catalog_response

router = APIRouter(prefix="/postprocessing")

class Folder(BaseModel):
    path: str
    accessible: bool

@router.get("")
async def read_downclient(
    # request: Request,
    session: Annotated[Session, Depends(get_session)],
    # client_session: Annotated[ClientSession, Depends(get_connection)],
    admin_user: Annotated[DetailedUser, Security(ABRAuth(GroupEnum.admin))],
):
    folders = [
        Folder(path="poop", accessible=True),
        Folder(path="pee", accessible=False),
    ]
    auto_moving_config_valid=True
    auto_moving = True and auto_moving_config_valid

    return catalog_response(
        "Settings.PostProcessing",
        user=admin_user,
        page="postprocessing",
        auto_moving=auto_moving,
        auto_moving_config_valid=auto_moving_config_valid,
        required_folders=folders
    )


# @router.put("/base-url")
# def update_downclient_base_url(
#     base_url: Annotated[str, Form()],
#     session: Annotated[Session, Depends(get_session)],
#     admin_user: Annotated[DetailedUser, Security(ABRAuth(GroupEnum.admin))],
# ):
#     api_update_downclient_base_url(
#         base_url=base_url, session=session, admin_user=admin_user
#     )
#     return Response(status_code=204, headers={"HX-Refresh": "true"})
#

