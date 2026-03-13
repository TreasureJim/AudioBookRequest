from aiohttp import ClientSession
from torf import BdecodeError, MetainfoError, ReadError, Torrent

from app.util.connection import USER_AGENT
from app.util.log import logger


async def get_torrent_info_hash(
    client_session: ClientSession, download_url: str
) -> str | None:
    logger.debug("Fetching torrent info hash", download_url=download_url)
    async with client_session.get(
        download_url, headers={"User-Agent": USER_AGENT}
    ) as r:
        if not r.ok:
            logger.error("Failed to fetch torrent", download_url=download_url)
            return None
        content = await r.read()
        try:
            tor = Torrent.read_stream(content)
            return tor.infohash
        except (MetainfoError, ReadError, BdecodeError) as e:
            logger.error(
                "Error reading torrent info hash",
                download_url=download_url,
                error=str(e),
            )
