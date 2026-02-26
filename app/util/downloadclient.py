import asyncio
from typing import Annotated, Optional

from fastapi import Depends
from sqlmodel import Session, select
from app.internal.audiobookshelf.client import background_abs_trigger_scan
from app.internal.audiobookshelf.config import abs_config
from app.internal.downloadclient.client import qBittorrentClient
from app.internal.downloadclient.config import downclient_config
from app.internal.downloadclient.types import TorrentStatus
from app.internal.models import Audiobook
from app.util.db import get_session
from app.util.log import logger


download_client: Optional[qBittorrentClient] = None

async def initialise_global_downloadclient(session: Session):
    global download_client
    if not downclient_config.is_valid(session):
        logger.debug("Download client config is not valid")
        return

    base_url = downclient_config.get_base_url(session)
    username = downclient_config.get_username(session)
    password =  downclient_config.get_password(session)
    assert base_url is not None and username is not None and password is not None

    download_client = qBittorrentClient(base_url, username, password)
    await download_client.login()

async def get_global_downloadclient(session: Annotated[Session, Depends(get_session)]):
    if not download_client:
        logger.debug("Initialised global download client")
        await initialise_global_downloadclient(session)

    return download_client

async def check_download_progress_task(stop_event: asyncio.Event):
    """A task that runs every 5 seconds until stopped."""
    task_id = id(asyncio.current_task()) # Unique ID for this task instance
    logger.debug(f"Background task {task_id} started.")
    try:
        while not stop_event.is_set():
            await check_books()

            try:
                await asyncio.wait_for(stop_event.wait(), timeout=5) # Wait for 5 seconds or until stopped
            except asyncio.TimeoutError:
                pass # Timeout means we continue the loop
            
    except asyncio.CancelledError:
        print(f"Background task {task_id} cancelled.")
    finally:
        print(f"Background task {task_id} stopped.")

async def check_books():
    session = next(get_session())
    abs_config_valid = abs_config.is_valid(session)

    books = session.exec(select(Audiobook).where(Audiobook.downloaded).where(Audiobook.download_client_hash is not None).where(Audiobook.download_progress < 100)).all()
    book_hashes = [book.download_client_hash for book in books if book.download_client_hash]

    down_client = await get_global_downloadclient(session)
    if not down_client:
        logger.error("Could not access global download client")
        return
    torrents = await down_client.torrent_list(hashes=book_hashes)

    for torrent in torrents:
        book = next((book for book in books if book.download_client_hash == torrent.hash), None)
        if not book:
            logger.error(f"Could not match torrent hash {torrent.hash} with book in DB")
            continue
        
        progress = int(torrent.progress)

        book.download_progress = progress
        if progress >= 100:
            await book_download_completed(book, torrent, abs_config_valid)

        session.add(book)

    session.commit()

async def book_download_completed(book: Audiobook, torrent: TorrentStatus, abs_valid: bool):
    if abs_valid:
        await background_abs_trigger_scan()

    move_book()
    raise Unfinished()
