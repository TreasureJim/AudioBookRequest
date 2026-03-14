from typing import Annotated, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, Response, Security
from pydantic import BaseModel
from sqlmodel import Session

from app.internal.auth.authentication import APIKeyAuth, DetailedUser

from app.internal.downloadclient.client import qBittorrentClient
from app.internal.downloadclient.config import DownclientMisconfigured, downclient_config
from app.internal.downloadclient.types import Category
from app.internal.models import GroupEnum
from app.util.downloadclient import get_global_downloadclient, initialise_global_downloadclient
from app.util.db import get_session

router = APIRouter(prefix="/downloadclient")

class DownclientResponse(BaseModel):
    base_url: str
    username: str
    password: str
    selected_category: str
    categories: list[Category]


@router.get("")
async def read_downclient(
    session: Annotated[Session, Depends(get_session)],
    # client_session: Annotated[ClientSession, Depends(get_connection)],
    admin_user: Annotated[DetailedUser, Security(APIKeyAuth(GroupEnum.admin))],
    download_client: Annotated[Optional[qBittorrentClient], Depends(get_global_downloadclient)]
):
    _ = admin_user
    base_url = downclient_config.get_base_url(session) or ""
    username = downclient_config.get_username(session) or ""
    password = downclient_config.get_password(session) or ""
    selected_category = downclient_config.get_category(session) or ""

    if download_client:
        categories = await download_client.get_categories()
    else:
        categories = []

    return DownclientResponse(base_url=base_url, username=username, password=password, selected_category=selected_category, categories=categories)


@router.put("/base-url")
def update_downclient_base_url(
    base_url: Annotated[str, Form()],
    session: Annotated[Session, Depends(get_session)],
    admin_user: Annotated[DetailedUser, Security(APIKeyAuth(GroupEnum.admin))],
):
    _ = admin_user
    downclient_config.set_base_url(session, base_url)
    return Response(status_code=204)


@router.put("/username")
def update_downclient_username(
    username: Annotated[str, Form()],
    session: Annotated[Session, Depends(get_session)],
    admin_user: Annotated[DetailedUser, Security(APIKeyAuth(GroupEnum.admin))],
):
    _ = admin_user
    downclient_config.set_username(session, username)
    return Response(status_code=204)


@router.put("/password")
def update_downclient_password(
    password: Annotated[str, Form()],
    session: Annotated[Session, Depends(get_session)],
    admin_user: Annotated[DetailedUser, Security(APIKeyAuth(GroupEnum.admin))],
):
    _ = admin_user
    downclient_config.set_password(session, password)
    return Response(status_code=204)

async def update_downclient_category(
    category: Annotated[str, Form()],
    session: Annotated[Session, Depends(get_session)],
    admin_user: Annotated[DetailedUser, Security(APIKeyAuth(GroupEnum.admin))],
    download_client: Annotated[Optional[qBittorrentClient], Depends(get_global_downloadclient)]
):
    _ = admin_user
    if not download_client:
        return Response(status_code=500)

    def match_cat(cat: Category):
        return category == cat.name
    if not ( match := next(filter(match_cat, await download_client.get_categories()), None) ):
        raise HTTPException(status_code=422, detail="Value does not match a valid category")
    if match.savePath == "":
        raise HTTPException(status_code=422, detail="Category must have a path set")

    downclient_config.set_category(session, match.name)
    return Response(status_code=204)


class DownclientLoginResponse(BaseModel):
    success: bool
    reason: str


@router.get("/test-connection")
async def test_downclient_connection(
    session: Annotated[Session, Depends(get_session)],
    admin_user: Annotated[DetailedUser, Security(APIKeyAuth(GroupEnum.admin))],
    background_task: BackgroundTasks,
) -> DownclientLoginResponse:
    _ = admin_user

    try:
        downclient_config.raise_if_invalid(session)
    except DownclientMisconfigured as e:
        return DownclientLoginResponse(success=False, reason=f"Config is not valid: {e}")

    base_url = downclient_config.get_base_url(session)
    assert base_url
    username = downclient_config.get_username(session) or ""
    password = downclient_config.get_password(session) or ""

    local_download_client = qBittorrentClient(base_url, username, password)
    try:
        await local_download_client.login()
    except qBittorrentClient.LoginUnauthorizedException:
        return DownclientLoginResponse(success=False, reason="Unauthorized")
    except qBittorrentClient.LoginIPBlockedException:
        return DownclientLoginResponse(
            success=False, reason="IP blocked. Too many login attempts."
        )
    except Exception as e:
        return DownclientLoginResponse(success=False, reason=str(e))
    else:
        background_task.add_task(initialise_global_downloadclient, session)
        return DownclientLoginResponse(success=True, reason="")
