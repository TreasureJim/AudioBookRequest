from typing import Literal
from pydantic import BaseModel
from enum import Enum


class TorrentProperties(BaseModel):
    save_path: str  # Torrent save path
    creation_date: int  # Torrent creation date (Unix timestamp)
    piece_size: int  # Torrent piece size (bytes)
    comment: str  # Torrent comment
    total_wasted: int  # Total data wasted for torrent (bytes)
    total_uploaded: int  # Total data uploaded for torrent (bytes)
    total_uploaded_session: int  # Total data uploaded this session (bytes)
    total_downloaded: int  # Total data downloaded for torrent (bytes)
    total_downloaded_session: int  # Total data downloaded this session (bytes)
    up_limit: int  # Torrent upload limit (bytes/s)
    dl_limit: int  # Torrent download limit (bytes/s)
    time_elapsed: int  # Torrent elapsed time (seconds)
    seeding_time: int  # Torrent elapsed time while complete (seconds)
    nb_connections: int  # Torrent connection count
    nb_connections_limit: int  # Torrent connection count limit
    share_ratio: float  # Torrent share ratio
    addition_date: int  # When this torrent was added (unix timestamp)
    completion_date: int  # Torrent completion date (unix timestamp)
    created_by: str  # Torrent creator
    dl_speed_avg: int  # Torrent average download speed (bytes/second)
    dl_speed: int  # Torrent download speed (bytes/second)
    eta: int  # Torrent ETA (seconds)
    last_seen: int  # Last seen complete date (unix timestamp)
    peers: int  # Number of peers connected to
    peers_total: int  # Number of peers in the swarm
    pieces_have: int  # Number of pieces owned
    pieces_num: int  # Number of pieces of the torrent
    reannounce: int  # Number of seconds until the next announce
    seeds: int  # Number of seeds connected to
    seeds_total: int  # Number of seeds in the swarm
    total_size: int  # Torrent total size (bytes)
    up_speed_avg: int  # Torrent average upload speed (bytes/second)
    up_speed: int  # Torrent upload speed (bytes/second)
    isPrivate: bool  # True if torrent is from a private tracker


class TorrentState(Enum):
    """Possible states of a torrent"""

    ERROR = "error"
    MISSING_FILES = "missingFiles"
    UPLOADING = "uploading"
    PAUSED_UP = "pausedUP"
    QUEUED_UP = "queuedUP"
    STALLED_UP = "stalledUP"
    CHECKING_UP = "checkingUP"
    FORCED_UP = "forcedUP"
    ALLOCATING = "allocating"
    DOWNLOADING = "downloading"
    META_DL = "metaDL"
    STOPPED_DL = "stoppedDL"
    PAUSED_DL = "pausedDL"
    QUEUED_DL = "queuedDL"
    STALLED_DL = "stalledDL"
    CHECKING_DL = "checkingDL"
    FORCED_DL = "forcedDL"
    CHECKING_RESUME_DATA = "checkingResumeData"
    MOVING = "moving"
    UNKNOWN = "unknown"


torrent_status_sort_fields = Literal[
    "hash",
    "name",
    "magnet_uri",
    "category",
    "tags",
    "content_path",
    "save_path",
    "tracker",
    "is_private",
    "num_complete",
    "num_incomplete",
    "num_seeds",
    "num_leechs",
    "size",
    "total_size",
    "progress",
    "availability",
    "downloaded",
    "uploaded",
    "completed",
    "downloaded_session",
    "uploaded_session",
    "amount_left",
    "dlspeed",
    "upspeed",
    "dl_limit",
    "up_limit",
    "ratio",
    "max_ratio",
    "ratio_limit",
    "max_seeding_time",
    "seeding_time_limit",
    "seeding_time",
    "eta",
    "time_active",
    "added_on",
    "completion_on",
    "last_activity",
    "seen_complete",
    "state",
    "priority",
    "auto_tmm",
    "force_start",
    "seq_dl",
    "f_l_piece_prio",
    "super_seeding",
    "reannounce",
]


class TorrentStatus(BaseModel):
    """Represents a torrent in qBittorrent"""

    # Basic info
    hash: str
    name: str
    magnet_uri: str
    category: str
    tags: str  # Comma-concatenated tag list

    # Paths
    content_path: str
    save_path: str

    # Tracker info
    tracker: str
    private: bool
    num_complete: int  # seeds in swarm
    num_incomplete: int  # leechers in swarm
    num_seeds: int  # connected seeds
    num_leechs: int  # connected leechers

    # Sizes and progress
    size: int  # selected files size
    total_size: int  # all files size
    progress: float  # percentage/100
    availability: float  # percentage of file pieces available

    # Data transferred
    downloaded: int
    uploaded: int
    completed: int  # amount completed (bytes)
    downloaded_session: int
    uploaded_session: int
    amount_left: int

    # Speeds and limits
    dlspeed: int
    upspeed: int
    dl_limit: int  # -1 if unlimited
    up_limit: int  # -1 if unlimited

    # Ratios and timing
    ratio: float
    max_ratio: float
    ratio_limit: float  # TODO: clarify difference from max_ratio
    max_seeding_time: int
    seeding_time_limit: int  # TODO: clarify difference from max_seeding_time
    seeding_time: int
    eta: int
    time_active: int

    # Timestamps
    added_on: int  # Unix epoch
    completion_on: int  # Unix epoch
    last_activity: int  # Unix epoch
    seen_complete: int  # Unix epoch

    # State and settings
    state: TorrentState
    priority: int  # -1 if disabled or in seed mode
    auto_tmm: bool  # Automatic Torrent Management
    force_start: bool
    seq_dl: bool  # sequential download
    f_l_piece_prio: bool  # first last piece prioritized
    super_seeding: bool

    # Other
    reannounce: int  # time until next tracker reannounce

    def __post_init__(self):
        """Convert string state to enum if needed"""
        if isinstance(self.state, str):
            try:
                self.state = TorrentState(self.state)
            except ValueError:
                self.state = TorrentState.UNKNOWN

    @property
    def is_downloading(self) -> bool:
        """Check if torrent is currently downloading"""
        return self.state in [
            TorrentState.DOWNLOADING,
            TorrentState.META_DL,
            TorrentState.FORCED_DL,
            TorrentState.QUEUED_DL,
            TorrentState.STALLED_DL,
        ]

    @property
    def is_uploading(self) -> bool:
        """Check if torrent is currently uploading/seeding"""
        return self.state in [
            TorrentState.UPLOADING,
            TorrentState.FORCED_UP,
            TorrentState.QUEUED_UP,
            TorrentState.STALLED_UP,
        ]

    @property
    def is_paused(self) -> bool:
        """Check if torrent is paused"""
        return self.state in [TorrentState.PAUSED_DL, TorrentState.PAUSED_UP]

    @property
    def is_errored(self) -> bool:
        """Check if torrent is in error state"""
        return self.state in [TorrentState.ERROR, TorrentState.MISSING_FILES]

    @property
    def is_checking(self) -> bool:
        """Check if torrent is being checked"""
        return self.state in [
            TorrentState.CHECKING_UP,
            TorrentState.CHECKING_DL,
            TorrentState.CHECKING_RESUME_DATA,
        ]

    @property
    def is_completed(self) -> bool:
        """Check if torrent has completed downloading"""
        return self.progress >= 1.0

    def progress_percentage(self) -> int:
        return int(self.progress * 100)

class Category(BaseModel):
    name: str
    savePath: str
