from functools import wraps
import posixpath
from typing import Any, Awaitable, Callable, Optional, ParamSpec, TypeVar
from urllib.parse import quote_plus
from aiohttp import ClientSession
import aiohttp
import string
import secrets

from pydantic import TypeAdapter

from app.internal.downloadclient.types import (
    TorrentStatus,
    TorrentProperties,
    torrent_status_sort_fields,
)
from app.util.log import logger

# Define ParamSpec to capture the exact parameters of the decorated function
P = ParamSpec("P")
# Define TypeVar for the return type, constrained to Awaitable for async functions
R = TypeVar("R", bound=Awaitable[Any])  # pyright: ignore[reportExplicitAny]


def authorised(func: Callable[P, R]) -> Callable[P, R]:
    @wraps(func)
    async def wrapper(self: qBittorrentClient, *args: P.args, **kwargs: P.kwargs) -> R:
        # P.args and P.kwargs ensure the wrapper's signature matches func's,
        # with 'self' explicitly typed, which is crucial for instance methods.

        if not self.is_authorised():
            print("Client not authorized. Attempting to log in...")
            await self.login()
            if not self.is_authorised():
                raise qBittorrentClient.LoginUnauthorizedException()

        return await func(self, *args, **kwargs)  # pyright: ignore[reportUnknownVariableType, reportCallIssue]

    return wrapper  # pyright: ignore[reportReturnType]


def generate_rand_id() -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(16))


class qBittorrentClient:
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url: str = base_url
        self.username: str = username
        self.password: str = password
        self.http_session: ClientSession = aiohttp.ClientSession(base_url=base_url)
        self.sid: Optional[str] = None

    def is_authorised(self) -> bool:
        return self.sid is not None

    async def login(self) -> str:
        data = {"username": self.username, "password": self.password}

        url = posixpath.join(self.base_url, "api/v2/auth/login")

        async with self.http_session.post(
            url,
            data=data,
            headers={
                "Referer": self.base_url,
            },
        ) as resp:
            if resp.status == 403:
                logger.error("qBittorrent: Too many login attempts. IP is blocked.")
                raise qBittorrentClient.LoginIPBlockedException()
            if not resp.ok:
                logger.error(
                    "qBittorrent: failed to send login",
                    status=resp.status,
                    reason=resp.reason,
                )
                raise qBittorrentClient.LoginException()

            if not (resp.ok or str(await resp.read()) == "Ok."):
                raise qBittorrentClient.LoginUnauthorizedException()

            sid = resp.cookies.get("SID")
            if sid:
                self.sid = str(sid)

            return str(sid)

    class LoginException(Exception):
        pass

    class LoginUnauthorizedException(Exception):
        pass

    class LoginIPBlockedException(Exception):
        pass

    def bad_login(self):
        self.sid = None
        raise qBittorrentClient.LoginUnauthorizedException()

    def check_bad_login(self, status_code: int):
        if status_code == 401 or status_code == 403:
            self.bad_login()

    @authorised
    async def torrent_properties(self, hash: str) -> TorrentProperties:
        url = posixpath.join(self.base_url, "api/v2/torrents/properties")

        async with self.http_session.get(
            url,
            params={"hash": hash},
        ) as resp:
            self.check_bad_login(resp.status)
            if resp.status == 404:
                logger.info(f"Downloadclient torrent {hash} wasn't found.")
                raise qBittorrentClient.TorrentNotFound(hash)

            return TorrentProperties.model_validate_json(await resp.text())

    class TorrentNotFound(Exception):
        hash: str

        def __init__(self, hash: str, **kargs: object) -> None:
            super().__init__(**kargs)
            self.hash = hash

    class DownloadedTorrentNotIdentified(Exception):
        id: str

        def __init__(self, id: str, **kargs: object) -> None:
            super().__init__(**kargs)
            self.id = id

    @authorised
    async def start_download(
        self, torrent_url: str, category: Optional[str], rename: Optional[str] = None
    ) -> TorrentStatus:
        """Start downloading the `torrent_url` and return the hash string of the torrent"""
        valid_prefixes = ["http://", "https://", "magnet:", "bc://bt/"]
        if not torrent_url.startswith(tuple(valid_prefixes)):
            raise qBittorrentClient.UrlInvalid(torrent_url)

        id = generate_rand_id()
        if rename is None:
            rename = id
        else:
            rename = f"{id} - {rename}"

        form = aiohttp.FormData(default_to_multipart=True, quote_fields=False)
        form.add_field("urls", torrent_url)
        if category:
            category = quote_plus(category)
            form.add_field("category", category)
        # if rename:
        form.add_field("rename", rename)

        url = posixpath.join(self.base_url, "api/v2/torrents/add")
        async with self.http_session.post(url, data=form) as resp:
            if resp.status == 415:
                raise qBittorrentClient.TorrentFileInvalid(torrent_url)

        if torrent := await self.find_torrent(id, recently_added=True):
            return torrent
        else:
            raise qBittorrentClient.DownloadedTorrentNotIdentified(id)

    @authorised
    async def torrent_list(
        self,
        category: Optional[str] = None,
        sort: Optional[torrent_status_sort_fields] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        hashes: Optional[list[str]] = None,
    ) -> list[TorrentStatus]:
        params: dict[str, str] = {}

        if limit:
            params["limit"] = str(limit)
        if offset:
            params["offset"] = str(offset)
        if category:
            params["category"] = quote_plus(category)
        if sort:
            params["sort"] = sort
        if hashes and len(hashes) > 0:
            params["hashes"] = "|".join(hashes)

        url = posixpath.join(self.base_url, "api/v2/torrents/info")

        async with self.http_session.get(url, params=params) as resp:
            self.check_bad_login(resp.status)

            adapter = TypeAdapter(list[TorrentStatus])
            return adapter.validate_json(await resp.read())

    async def find_torrent(
        self, id: str, recently_added: bool
    ) -> Optional[TorrentStatus]:
        def filter_torrent(torrent: TorrentStatus) -> bool:
            return id in torrent.name

        if recently_added:
            torrents = await self.torrent_list(sort="added_on", limit=10)
            res = list(filter(filter_torrent, torrents))
            if len(res) > 0:
                return res[0]

        torrents = await self.torrent_list()
        res = list(filter(filter_torrent, torrents))
        if len(res) > 0:
            return res[0]

    class TorrentFileInvalid(Exception):
        url: str

        def __init__(self, url: str, **kargs: object) -> None:
            super().__init__(**kargs)
            self.url = url

    class UrlInvalid(Exception):
        url: str

        def __init__(self, url: str, **kargs: object) -> None:
            super().__init__(*kargs)
            self.url = url
