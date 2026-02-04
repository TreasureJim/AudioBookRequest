from pydantic import BaseModel

class Torrent(BaseModel):
    save_path: str            # Torrent save path
    creation_date: int        # Torrent creation date (Unix timestamp)
    piece_size: int           # Torrent piece size (bytes)
    comment: str              # Torrent comment
    total_wasted: int         # Total data wasted for torrent (bytes)
    total_uploaded: int       # Total data uploaded for torrent (bytes)
    total_uploaded_session: int  # Total data uploaded this session (bytes)
    total_downloaded: int     # Total data downloaded for torrent (bytes)
    total_downloaded_session: int  # Total data downloaded this session (bytes)
    up_limit: int             # Torrent upload limit (bytes/s)
    dl_limit: int             # Torrent download limit (bytes/s)
    time_elapsed: int         # Torrent elapsed time (seconds)
    seeding_time: int         # Torrent elapsed time while complete (seconds)
    nb_connections: int       # Torrent connection count
    nb_connections_limit: int  # Torrent connection count limit
    share_ratio: float        # Torrent share ratio
    addition_date: int        # When this torrent was added (unix timestamp)
    completion_date: int      # Torrent completion date (unix timestamp)
    created_by: str           # Torrent creator
    dl_speed_avg: int         # Torrent average download speed (bytes/second)
    dl_speed: int             # Torrent download speed (bytes/second)
    eta: int                  # Torrent ETA (seconds)
    last_seen: int            # Last seen complete date (unix timestamp)
    peers: int                # Number of peers connected to
    peers_total: int          # Number of peers in the swarm
    pieces_have: int          # Number of pieces owned
    pieces_num: int           # Number of pieces of the torrent
    reannounce: int           # Number of seconds until the next announce
    seeds: int                # Number of seeds connected to
    seeds_total: int          # Number of seeds in the swarm
    total_size: int           # Torrent total size (bytes)
    up_speed_avg: int         # Torrent average upload speed (bytes/second)
    up_speed: int             # Torrent upload speed (bytes/second)
    isPrivate: bool           # True if torrent is from a private tracker
