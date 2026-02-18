import asyncio
from typing import Annotated, Optional

from fastapi import Depends
from sqlmodel import Session
from app.internal.downloadclient.client import qBittorrentClient
from app.internal.downloadclient.config import downclient_config
from app.util.db import get_session
from app.util.log import logger


download_client: Optional[qBittorrentClient] = None

async def initialise_global_downloadclient(session: Session):
    global download_client
    if not downclient_config.is_valid(session):
        return

    base_url = downclient_config.get_base_url(session)
    username = downclient_config.get_username(session)
    password =  downclient_config.get_password(session)
    assert base_url is not None and username is not None and password is not None

    download_client = qBittorrentClient(base_url, username, password)
    await download_client.login()

async def get_global_downloadclient(session: Annotated[Session, Depends(get_session)]):
    if not download_client:
        await initialise_global_downloadclient(session)

    return download_client

async def check_download_progress_task(stop_event: asyncio.Event):
    """A task that runs every 5 seconds until stopped."""
    task_id = id(asyncio.current_task()) # Unique ID for this task instance
    logger.debug(f"Background task {task_id} started.")
    try:
        while not stop_event.is_set():
            # TODO: Check progress
            # Update database
            # If done then execute file linking/ moving function

            try:
                await asyncio.wait_for(stop_event.wait(), timeout=5) # Wait for 5 seconds or until stopped
            except asyncio.TimeoutError:
                pass # Timeout means we continue the loop
            
    except asyncio.CancelledError:
        print(f"Background task {task_id} cancelled.")
    finally:
        print(f"Background task {task_id} stopped.")
