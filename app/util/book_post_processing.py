import os
from pathlib import Path
import posixpath
import shutil

import aiohttp
import rapidfuzz
from rapidfuzz import fuzz, utils
from sqlmodel import Session

from app.internal.audiobookshelf.client import abs_get_library
from app.internal.audiobookshelf.config import abs_config
from app.internal.models import Audiobook, AudiobookSeriesLink, Author
from app.util.log import logger


def match_book_to_author_path(
    session: Session, book: Audiobook, abs_library_paths: list[str]
) -> Author:
    """Returns folder path of matched author
    If no author can be matched then it will pick the first author and generate a theoretical folder name from author name
    NOTE: it will not create folders
    """
    saved_author = next(
        (author for author in book.authors if author.save_path is not None), None
    )
    if saved_author:
        return saved_author

    abs_authors: list[str] = []
    abs_authors_full_path: list[str] = []

    for path in abs_library_paths:
        dir_scan = os.listdir(path)
        abs_authors.extend(dir_scan)
        abs_authors_full_path.extend([f"{path}/{item}" for item in dir_scan])

    author_path = None
    matched_author = None
    for book_author in book.authors:
        best_match = rapidfuzz.process.extractOne(
            book_author.name,
            abs_authors,
            scorer=fuzz.partial_ratio,
            processor=utils.default_process,
        )
        if best_match and best_match[1] >= 90:
            matched_author = book_author
            author_path = abs_authors_full_path[best_match[2]]
            break

    if not author_path or not matched_author:
        author_path = posixpath.join(abs_library_paths[0], book.authors[0].name)
        matched_author = book.authors[0]

    matched_author.save_path = author_path
    session.add(matched_author)
    session.commit()

    return matched_author


def match_book_to_series(book: Audiobook, author_path: str) -> AudiobookSeriesLink:
    """Returns matched Series
    If no series can be matched then it will use the first series in the book and pick a theoretical path for it
    NOTE: this function does not create folders
    """
    try:
        abs_serieses = os.listdir(author_path)
    except FileNotFoundError:
        abs_serieses = []

    series_path = None
    matched_series = None
    for series_link in book.series_links:
        book_series = series_link.series.title
        best_match = rapidfuzz.process.extractOne(
            book_series,
            abs_serieses,
            scorer=fuzz.partial_ratio,
            processor=utils.default_process,
        )
        if best_match and best_match[1] >= 90:
            series_path = posixpath.join(author_path, best_match[0])
            matched_series = book.series_links[best_match[2]]
            break

    if not series_path or not matched_series:
        series_path = posixpath.join(author_path, book.series_links[0].series.title)
        matched_series = book.series_links[0]

    matched_series.series.save_path = series_path

    return matched_series


class MissingFile(Exception):
    path: str

    def __init__(self, path: str, **kargs: object) -> None:
        super().__init__(**kargs)
        self.path = path


def hard_link_book(
    session: Session, book: Audiobook, abs_library_paths: list[str], torrent_path: str
):
    if not os.path.exists(torrent_path):
        raise MissingFile(torrent_path)

    # author
    author = match_book_to_author_path(session, book, abs_library_paths)
    if not author.save_path:
        logger.error(
            f"Failed to hard link book: author ({author.name}/{author.asin}) has no save_path"
        )
        return
    torrent_path_is_folder = not os.path.isfile(torrent_path)

    if len(book.series_links) == 0:
        Path(author.save_path).mkdir(parents=True, exist_ok=True)
        book_path = posixpath.join(author.save_path, book.title)
        if torrent_path_is_folder:
            shutil.copytree(torrent_path, book_path, copy_function=os.link)
        else:
            os.mkdir(book_path)
            os.link(
                torrent_path, posixpath.join(book_path, os.path.basename(torrent_path))
            )

    # series
    series_link = match_book_to_series(book, author.save_path)
    if not series_link.series.save_path:
        logger.error(
            f"Failed to hard link book: series ({series_link.series.title}/{series_link.series.asin}) has not save_path"
        )
        return
    Path(series_link.series.save_path).mkdir(parents=True, exist_ok=True)

    book_path = posixpath.join(
        series_link.series.save_path, f"Book {series_link.sequence} - {book.title}"
    )

    if torrent_path_is_folder:
        shutil.copytree(torrent_path, book_path, copy_function=os.link)
    else:
        os.mkdir(book_path)
        os.link(torrent_path, posixpath.join(book_path, os.path.basename(torrent_path)))
