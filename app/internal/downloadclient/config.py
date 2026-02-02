from typing import Literal, Optional

from sqlmodel import Session

from app.util.cache import StringConfigCache


class DownclientMisconfigured(ValueError):
    pass


DownclientConfigKey = Literal[
    "downclient_base_url",
    "downclient_username",
    "downclient_password",
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

downclient_config = DownclientConfig()
