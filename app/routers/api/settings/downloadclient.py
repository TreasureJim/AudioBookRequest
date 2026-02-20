from typing import Annotated

from fastapi import APIRouter, Depends, Form, Response, Security
from pydantic import BaseModel
from sqlmodel import Session

from app.internal.auth.authentication import APIKeyAuth, DetailedUser

from app.internal.downloadclient.client import qBittorrentClient
from app.internal.downloadclient.config import downclient_config
from app.internal.models import GroupEnum
from app.util.db import get_session
from app.util.downloadclient import get_global_downloadclient

router = APIRouter(prefix="/downloadclient")


class DownclientResponse(BaseModel):
    base_url: str
    username: str
    password: str


@router.get("")
async def read_downclient(
    session: Annotated[Session, Depends(get_session)],
    # client_session: Annotated[ClientSession, Depends(get_connection)],
    admin_user: Annotated[DetailedUser, Security(APIKeyAuth(GroupEnum.admin))],
):
    _ = admin_user
    base_url = downclient_config.get_base_url(session) or ""
    username = downclient_config.get_username(session) or ""
    password = downclient_config.get_password(session) or ""

    return DownclientResponse(
        base_url=base_url,
        username=username,
        password=password
    )


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

class DownclientLoginResponse(BaseModel):
    success: bool
    reason: str

@router.get("/test-connection")
async def test_downclient_connection(
    session: Annotated[Session, Depends(get_session)],
    # client_session: Annotated[ClientSession, Depends(get_connection)],
    admin_user: Annotated[DetailedUser, Security(APIKeyAuth(GroupEnum.admin))],
    download_client: Annotated[qBittorrentClient, Depends(get_global_downloadclient)]
) -> DownclientLoginResponse:
    _ = admin_user
    downclient_config.raise_if_invalid(session)

    try:
        await download_client.login()
    except qBittorrentClient.LoginUnauthorizedException:
        return DownclientLoginResponse(
            success=False,
            reason="Unauthorized"
        )
    except qBittorrentClient.LoginIPBlockedException:
        return DownclientLoginResponse(
            success=False,
            reason="IP blocked. Too many login attempts."
        )
    except Exception as e:
        return DownclientLoginResponse(
            success=False,
            reason=str(e)
        )
    else:
        return DownclientLoginResponse(
            success=True,
            reason=""
        )
