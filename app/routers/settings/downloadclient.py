from typing import Annotated

from aiohttp import ClientSession
from fastapi import APIRouter, Depends, Form, Request, Response, Security
from sqlmodel import Session

from app.internal.auth.authentication import ABRAuth, DetailedUser
from app.internal.models import GroupEnum
from app.util.connection import get_connection
from app.util.db import get_session
from app.util.log import logger
from app.util.templates import template_response

from app.routers.api.settings.downloadclient import (
    read_downclient as api_read_downclient,
    update_downclient_base_url as api_update_downclient_base_url,
    update_downclient_username as api_update_downclient_username,
    update_downclient_password as api_update_downclient_password,
    test_downclient_connection as api_test_downclient_connection,
)

router = APIRouter(prefix="/downloadclient")


@router.get("")
async def read_downclient(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    client_session: Annotated[ClientSession, Depends(get_connection)],
    admin_user: Annotated[DetailedUser, Security(ABRAuth(GroupEnum.admin))],
):
    response = await api_read_downclient(
        session=session,
        client_session=client_session,
        admin_user=admin_user,
    )
    return template_response(
        "settings_page/downloadclient.html",
        request,
        admin_user,
        {
            "page": "downloadclient",
            "downloadclient_base_url": response.base_url,
            "downloadclient_username": response.username,
            "downloadclient_password": response.password,
        },
    )


@router.put("/base-url")
def update_downclient_base_url(
    base_url: Annotated[str, Form()],
    session: Annotated[Session, Depends(get_session)],
    admin_user: Annotated[DetailedUser, Security(ABRAuth(GroupEnum.admin))],
):
    api_update_downclient_base_url(
        base_url=base_url, session=session, admin_user=admin_user
    )
    return Response(status_code=204, headers={"HX-Refresh": "true"})


@router.put("/username")
def update_downclient_username(
    username: Annotated[str, Form()],
    session: Annotated[Session, Depends(get_session)],
    admin_user: Annotated[DetailedUser, Security(ABRAuth(GroupEnum.admin))],
):
    api_update_downclient_username(
        username=username, session=session, admin_user=admin_user
    )
    return Response(status_code=204, headers={"HX-Refresh": "true"})


@router.put("/password")
def update_downclient_password(
    password: Annotated[str, Form()],
    session: Annotated[Session, Depends(get_session)],
    admin_user: Annotated[DetailedUser, Security(ABRAuth(GroupEnum.admin))],
):
    api_update_downclient_password(
        password=password, session=session, admin_user=admin_user
    )
    return Response(status_code=204, headers={"HX-Refresh": "true"})


@router.get("/test-connection")
async def test_connection(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    client_session: Annotated[ClientSession, Depends(get_connection)],
    admin_user: Annotated[DetailedUser, Security(ABRAuth(GroupEnum.admin))],
):
    resp = await api_test_downclient_connection(
        session=session, client_session=client_session, admin_user=admin_user
    )

    logger.error(resp)
    return template_response(
        "components/connection_test_result.html",
        request,
        admin_user,
        {"conn_success": resp.success, "conn_resp_info": resp.reason},
    )
