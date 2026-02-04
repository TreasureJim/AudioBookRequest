from functools import wraps
import posixpath
from types import FunctionType
from typing import Optional
from aiohttp import ClientSession
import aiohttp

from app.util.log import logger

class qBittorrentClient:
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url: str = base_url
        self.username: str = username
        self.password: str = password
        self.http_session: ClientSession = aiohttp.ClientSession(base_url=base_url)
        self.sid: Optional[str] = None

    async def login(self) -> str:
        data = {
            "username": self.username,
            "password": self.password
        }

        url = posixpath.join(self.base_url, "api/v2/auth/login")
        
        async with self.http_session.post(
            url, 
            data=data,
            headers={
                "Referer": self.base_url,
            }
        ) as resp:
            if resp.status == 403:
                logger.error("qBittorrent: Too many login attempts. IP is blocked.")
                raise qBittorrentClient.LoginIPBlockedException()
            if not resp.ok:
                logger.error(
                    "qBittorrent: failed to send login",
                    status=resp.status, reason=resp.reason,
                )
                raise qBittorrentClient.LoginException()

            sid = resp.cookies.get("SID")
            if not sid:
                raise qBittorrentClient.LoginUnauthorizedException()

            return str(sid)

    class LoginException(Exception):
        pass

    class LoginUnauthorizedException(Exception):
        pass

    class LoginIPBlockedException(Exception):
        pass

    def authorised(func: FunctionType):
        def wrapper(self):
            if self.sid is None:
                self.login()
            func
        return wrapper

    def bad_login(self):
        self.sid = None
        raise qBittorrentClient.LoginUnauthorizedException()

    def check_bad_login(self, status_code: int):
        if status_code == 401 or status_code == 403:
            self.bad_login()

    @authorised
    async def torrent_properties(self, hash: str):
        url = posixpath.join(self.base_url, "api/v2/torrents/properties")

        async with self.http_session.get(
            url,
            params={"hash": hash},
        ) as resp:
            self.check_bad_login(resp.status)
            if resp.status == 404:
                logger.info(f"Downloadclient torrent {hash} wasn't found.")
                raise qBittorrentClient.TorrentNotFound(hash)

            raise Exception("TODO!")



    class TorrentNotFound(Exception):
        hash: str

        def __init__(self, hash: str, **kargs: object) -> None:
            super().__init__(**kargs)
            self.hash = hash
