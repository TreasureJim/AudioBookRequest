from typing import Optional
from aiohttp import ClientSession
from sqlmodel import Session

from app.internal.downloadclient.client import qBittorrentClient
from app.internal.downloadclient.config import downclient_config
from app.internal.models import Audiobook, EventEnum, ProwlarrSource, User
from app.internal.notifications import send_all_notifications
from app.internal.prowlarr.util import prowlarr_config
from app.internal.torrents import get_torrent_info_hash
from app.util.downloadclient import get_global_downloadclient

import app.internal.prowlarr.prowlarr as prowlarr_client
from app.internal.audiobookshelf.config import abs_config
import app.internal.audiobookshelf.client as abs_client
from app.util.log import logger


def format_audiobook_str(audiobook: Audiobook) -> str:
    if len(audiobook.series_links) > 0:
        return f"{audiobook.title} {audiobook.authors[0].name} / #{audiobook.series_links[0].sequence} {audiobook.series_links[0].series.title}"
    return f"{audiobook.title} - {audiobook.authors[0].name}"


class DownloadError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)


async def start_download(
    session: Session,
    client_session: ClientSession,
    book: Audiobook,
    guid: str,
    torrent_url: str,
    indexer_id: int,
    requester: User,
    prowlarr_source: Optional[ProwlarrSource],
    rename_torrent: Optional[str],
):
    book_downloaded = False
    torrent = None

    if downclient_config.is_valid(session):
        download_client = await get_global_downloadclient(session)
        if not download_client:
            raise DownloadError("Could not retrieve download client")

        try:
            torrent = await download_client.start_download(
                torrent_url,
                book.asin,
                downclient_config.get_category(session),
                rename_torrent,
            )
        except qBittorrentClient.DownloadedTorrentNotIdentified as e:
            raise DownloadError(
                f"Could not find added torrent in download client with ID: {e.id}"
            ) from e
        except qBittorrentClient.TorrentFileInvalid as e:
            raise DownloadError(f"Provided torrent url is invalid: {e.url}") from e
        else:
            book_downloaded = True

    elif prowlarr_config.is_valid(session):
        resp = await prowlarr_client.prowlarr_start_download(
            session=session,
            client_session=client_session,
            guid=guid,
            indexer_id=indexer_id,
            requester=requester,
            book_asin=book.asin,
            prowlarr_source=prowlarr_source,
        )
        if resp.ok:
            book_downloaded = True
        else:
            raise DownloadError("Failed to start download")

    else:
        raise DownloadError("No config setup for downloading")

    if book_downloaded:
        await announce_download(book.asin, prowlarr_source, client_session, requester)

        book.downloaded = True
        if torrent:
            book.download_client_hash = torrent.hash 
        session.add(book)
        session.commit()

        # Try to trigger an ABS scan to pick up new media
        try:
            if abs_config.is_valid(session):
                await abs_client.abs_trigger_scan(session, client_session)
        except Exception:
            pass


async def start_download_with_rename(
    session: Session,
    client_session: ClientSession,
    guid: str,
    torrent_url: str,
    indexer_id: int,
    requester: User,
    book: Audiobook,
    prowlarr_source: Optional[ProwlarrSource],
):
    rename = format_audiobook_str(book)
    await start_download(
        session=session,
        client_session=client_session,
        guid=guid,
        torrent_url=torrent_url,
        indexer_id=indexer_id,
        requester=requester,
        book=book,
        prowlarr_source=prowlarr_source,
        rename_torrent=rename,
    )


async def announce_download(
    book_asin: str,
    prowlarr_source: Optional[ProwlarrSource],
    client_session: ClientSession,
    requester: User,
):
    # Find additional metadata/replacements to pass along notifications
    additional_replacements: dict[str, str] = {"bookASIN": book_asin}
    if prowlarr_source:
        if prowlarr_source.download_url and prowlarr_source.protocol == "torrent":
            if info_hash := await get_torrent_info_hash(
                client_session, prowlarr_source.download_url
            ):
                additional_replacements["torrentInfoHash"] = info_hash
        elif prowlarr_source.magnet_url and prowlarr_source.protocol == "torrent":
            info_hash = prowlarr_source.magnet_url.replace("magnet:?", "")
            info_hash = info_hash.replace("xt=urn:btih:", "")
            info_hash = info_hash.split("&")[0]
            additional_replacements["torrentInfoHash"] = info_hash

        additional_replacements["sourceSizeMB"] = str(prowlarr_source.size_MB)
        additional_replacements["sourceTitle"] = prowlarr_source.title
        additional_replacements["indexerName"] = prowlarr_source.indexer
        additional_replacements["sourceProtocol"] = prowlarr_source.protocol

    logger.debug("Download successfully started", book_asin=book_asin)
    await send_all_notifications(
        EventEnum.on_successful_download,
        requester,
        book_asin,
        additional_replacements,
    )
