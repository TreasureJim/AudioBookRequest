import posixpath
from aiohttp import ClientSession
from sqlmodel import Session

from app.util.log import logger

from app.internal.downloadclient.config import downclient_config


class LoginException(Exception):
    def __init__(self, detail: str | None = None, **kwargs: object):
        super().__init__(**kwargs)
        self.detail: str | None = detail

class LoginUnauthorizedException(Exception):
    pass


cookie = ""

async def login(session: Session, client_session: ClientSession) -> str:
    base_url = downclient_config.get_base_url(session)
    if not base_url:
        logger.info("Download client: Failed to login because no base_url defined")
        raise LoginException("No base_url defined")

    username = downclient_config.get_username(session)
    password = downclient_config.get_password(session)

    data = ""
    if username and password:
        data = f"username={username}&password={password}"

    try:
        url = posixpath.join(base_url, "api/v2/auth/login")
        async with client_session.post(url, data=data) as resp:
            if not resp.ok:
                logger.error(
                    "Download client: failed to send login",
                    status=resp.status,
                    reason=resp.reason,
                )
                raise LoginException("Download client: failed to send login request")

            sid = resp.cookies.get("SID")
            if not sid:
                raise LoginUnauthorizedException()

            cookie = sid
            return str(sid)
    except Exception as e:
        raise LoginException("connection problem", e=e)
