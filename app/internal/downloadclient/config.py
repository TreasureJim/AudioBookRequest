from typing import Literal, Optional

from sqlmodel import Session

from app.util.cache import StringConfigCache


class DownclientMisconfigured(ValueError):
    pass


DownclientConfigKey = Literal[
    "downclient_base_url",
    "downclient_username",
    "downclient_password",
    "downclient_category",
    "downclient_rename_torrents",
]


class DownclientConfig(StringConfigCache[DownclientConfigKey]):
    def is_valid(self, session: Session) -> bool:
        return (
            self.get_base_url(session) is not None
            and self.get_username(session) is not None
            and self.get_password(session) is not None
        )

    def raise_if_invalid(self, session: Session):
        if not self.get_base_url(session):
            raise DownclientMisconfigured("Download client base url not set")
        if not self.get_username(session):
            raise DownclientMisconfigured("Download client username not set")
        if not self.get_password(session):
            raise DownclientMisconfigured("Download client password not set")

    def get_base_url(self, session: Session) -> Optional[str]:
        return self.get(session, "downclient_base_url")

    def set_base_url(self, session: Session, base_url: str):
        base_url = base_url.rstrip("/")
        self.set(session, "downclient_base_url", base_url)

    def get_username(self, session: Session) -> Optional[str]:
        return self.get(session, "downclient_username")

    def set_username(self, session: Session, username: str):
        self.set(session, "downclient_username", username)

    def get_password(self, session: Session) -> Optional[str]:
        return self.get(session, "downclient_password")

    def set_password(self, session: Session, password: str):
        self.set(session, "downclient_password", password)

    def get_category(self, session: Session) -> Optional[str]:
        self.get(session, "downclient_category")

    def set_category(self, session: Session, category: str):
        self.set(session, "downclient_category", category)

    def get_rename_torrents(self, session: Session) -> Optional[bool]:
        if b := self.get(session, "downclient_rename_torrents"):
            return b == "1"
        else: 
            return False

    def set_rename_torrents(self, session: Session, rename_torrents: bool):
        if rename_torrents:
            self.set(session, "downclient_rename_torrents", "1")
        else:
            self.set(session, "downclient_rename_torrents", "0")

downclient_config = DownclientConfig()
