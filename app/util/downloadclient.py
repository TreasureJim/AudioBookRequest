import asyncio
from typing import Annotated, Optional, cast

import aiohttp
from fastapi import Depends
from sqlmodel import Session, select
from app.internal.audiobookshelf.client import (
    abs_get_library,
    background_abs_trigger_scan,
)
from app.internal.audiobookshelf.config import abs_config
from app.internal.downloadclient.client import qBittorrentClient
from app.internal.downloadclient.config import downclient_config
from app.internal.models import Audiobook
from app.util.book_post_processing import MissingFile, hard_link_book
from app.util.db import get_session
from app.util.log import logger


download_client: Optional[qBittorrentClient] = None


async def initialise_global_downloadclient(session: Session):
    global download_client
    if not downclient_config.is_valid(session):
        logger.debug("Download client config is not valid")
        return

    base_url = downclient_config.get_base_url(session)
    assert base_url
    username = downclient_config.get_username(session) or ""
    password = downclient_config.get_password(session) or ""

    download_client = qBittorrentClient(base_url, username, password)
    try:
        await download_client.login()
    except aiohttp.ClientConnectionError as e:
        logger.error("Failed to initialise download client: %s", e)
        download_client = None
    else:
        logger.debug("Initialised global download client")


async def get_global_downloadclient(
    session: Annotated[Session, Depends(get_session)],
) -> Optional[qBittorrentClient]:
    if not download_client:
        await initialise_global_downloadclient(session)

    return download_client


async def timeout_event(event: asyncio.Event, timeout: float):
    try:
        await asyncio.wait_for(
            event.wait(), timeout=timeout
        )  # Wait for x seconds or until stopped
    except asyncio.TimeoutError:
        pass

class DownloadMonitorManager:
    stop_event: asyncio.Event = asyncio.Event()
    task: Optional[asyncio.Task[None]] = None

    def start(self):
         self.task = asyncio.create_task(
                    download_monitor_task(self.stop_event)
            )

    async def stop(self):
        if self.task:
            self.stop_event.set()
            await asyncio.sleep(0.1)
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass  # Expected

            self.task = None


global_download_monitor_manager: DownloadMonitorManager = DownloadMonitorManager()

def start_download_monitor():
    global_download_monitor_manager.start()

async def stop_download_monitor():
    await global_download_monitor_manager.stop()


async def download_monitor_task(stop_event: asyncio.Event):
    """A task that runs every 5 seconds until stopped."""

    session = next(get_session())
    if not downclient_config.is_valid(session):
        return

    task_id = id(asyncio.current_task())  # Unique ID for this task instance
    logger.debug(f"Background task {task_id} started.")
    try:
        abs_library_id = abs_config.get_library_id(session)
        if not abs_library_id:
            return
        async with aiohttp.ClientSession() as client_session:
            abs_library = await abs_get_library(abs_library_id, session, client_session)
            if not abs_library:
                return
            # abs_folders = [folder.fullPath for folder in abs_library.folders]
            # TODO REMOVE AFTER TESTING
            abs_folders = ["./books"]
        while not stop_event.is_set():
            down_client = await get_global_downloadclient(session)
            if not down_client:
                logger.error(
                    "Background task: Could not access download client. Timing out 30s"
                )
                await timeout_event(stop_event, 30.0)
                continue

            await match_downloaded_books(session, down_client)
            await check_books(session, down_client, abs_folders)

            await timeout_event(stop_event, 5.0)

    except asyncio.CancelledError:
        logger.info(f"Background task {task_id} cancelled.")
    except Exception as e:
        logger.exception("Background task ran into exception: %s", e)
    finally:
        logger.info(f"Background task {task_id} stopped.")


async def match_downloaded_books(session: Session, download_client: qBittorrentClient):
    # Find books where download has started or finished
    books = session.exec(
        select(Audiobook)
        .where(Audiobook.downloaded)
        .where(Audiobook.download_client_hash is None)
    ).all()

    torrent_matches = await download_client.batch_find_torrent(
        [book.asin for book in books]
    )
    for i, (id, torrent) in enumerate(torrent_matches):
        if not torrent:
            continue

        book = books[i]
        if book.asin != id and not (book := session.get(Audiobook, id)):
            continue
        book.download_client_hash = torrent.hash
        session.add(book)

    session.commit()


async def check_books(
    session: Session, download_client: qBittorrentClient, abs_folders: list[str]
):
    # Find books where download has started or finished
    books = session.exec(
        select(Audiobook)
        .where(Audiobook.downloaded)
        .where(Audiobook.download_client_hash is not None)
    ).all()
    book_hashes = [
        book.download_client_hash for book in books if book.download_client_hash
    ]

    torrents = await download_client.torrent_list(hashes=book_hashes)
    torrent_dict = {torrent.hash: torrent for torrent in torrents}

    moved_book = False
    for book in books:
        torrent = torrent_dict.get(cast(str, book.download_client_hash))
        if not torrent:
            logger.warning(
                f"Checking books: could not find book hash ( {book.title} - {book.download_client_hash} ) in download client. Removing from downloaded."
            )
            book.downloaded = False
            book.download_progress = 0
            book.download_client_hash = None
            continue

        book.download_progress = torrent.progress_percentage()

        if book.download_progress >= 100:
            moved_book = True
            try:
                hard_link_book(session, book, abs_folders, torrent.content_path)
                book.moved = True
            except MissingFile as e:
                logger.warning(
                    f"Checking books: Could not find book ( {book.title} - {book.download_client_hash} ) torrent path at {e.path}. Removing from downloaded"
                )
                book.downloaded = False
                book.download_progress = 0
                book.download_client_hash = None
                continue

        session.add(book)

    session.commit()
    if moved_book:
        await background_abs_trigger_scan()
