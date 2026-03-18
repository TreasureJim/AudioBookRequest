from sqlmodel import Session
from app.internal.downloadclient.client import qBittorrentClient
from app.internal.downloadclient.config import DownclientMisconfigured, downclient_config
from app.internal.downloadclient.types import Category
from app.internal.folders import FolderAvailability, path_accessible


async def check_downloadclient_category_folders_available(
    session: Session, downloadclient: qBittorrentClient
) -> FolderAvailability:
    downclient_config.raise_if_invalid(session)
    if not downclient_config.get_category(session):
        raise DownclientMisconfigured("Download client has no configured category")
    category = downclient_config.get_category(session)
    assert category

    def matching_cat(cat: Category):
        return category == cat.name

    categories = await downloadclient.get_categories()
    match = next(filter(matching_cat, categories), None)

    if not match:
        raise DownclientMisconfigured("Download client has a selected category that does not exist")

    return FolderAvailability(path=match.savePath, accessible=path_accessible(match.savePath))
