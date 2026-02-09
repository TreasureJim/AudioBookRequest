from typing import Optional

from sqlmodel import Session
from app.internal.downloadclient.client import qBittorrentClient
from app.internal.downloadclient.config import downclient_config


download_client: Optional[qBittorrentClient] = None

def initialise_client(session: Session):
    global download_client
    if not downclient_config.is_valid(session):
        return

    base_url = downclient_config.get_base_url(session)
    username = downclient_config.get_username(session)
    password =  downclient_config.get_password(session)
    assert base_url is not None and username is not None and password is not None

    download_client = qBittorrentClient(base_url, username, password)
