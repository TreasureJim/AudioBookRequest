import posixpath
from aiohttp import ClientSession
import aiohttp
from sqlmodel import Session

from app.util.log import logger

from app.internal.downloadclient.config import downclient_config


class LoginException(Exception):
    def __init__(self, detail: str | None = None, **kwargs: object):
        super().__init__(**kwargs)
        self.detail: str | None = detail

class LoginUnauthorizedException(Exception):
    pass

class LoginIPBlockedException(Exception):
    pass


async def login(session: Session, client_session: ClientSession) -> str:
    downclient_config.raise_if_invalid(session)

    base_url = downclient_config.get_base_url(session)
    assert base_url is not None
    username = downclient_config.get_username(session)
    password = downclient_config.get_password(session)

    data = {}
    if username and password:
        data = {
            username: username,
            password: password
        }

    url = posixpath.join(base_url, "api/v2/auth/login")
    
    async with client_session.post(
        url, 
        data=data,
        headers={
            "Referer": base_url,
        }
    ) as resp:
        if resp.status == 403:
            logger.error("Download client: Too many login attempts. IP is blocked.")
            raise LoginIPBlockedException()
        if not resp.ok:
            logger.error(
                "Download client: failed to send login",
                status=resp.status, reason=resp.reason,
            )
            raise LoginException("Download client: failed to send login request")

        sid = resp.cookies.get("SID")
        if not sid:
            raise LoginUnauthorizedException()

        return str(sid)
