import os
from pathlib import Path
import posixpath
import shutil
from typing import Any, Callable, Optional

import rapidfuzz
from rapidfuzz import fuzz, utils
from sqlmodel import Session

from app.internal.models import Audiobook, AudiobookSeriesLink, Author
from app.internal.postprocessing.config import postprocessing_config
from app.util.log import logger


def match_book_to_author_path(
    session: Session, book: Audiobook, abs_library_paths: list[str]
) -> Optional[Author]:
    """Returns folder path of matched author
    If no author can be matched then it will pick the first author and generate a theoretical folder name from author name
    NOTE: it will not create folders
    """
    if len(book.authors) == 0:
        return None

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


def match_book_to_series(
    book: Audiobook, author_path: str
) -> Optional[AudiobookSeriesLink]:
    """Returns matched Series
    If no series can be matched then it will use the first series in the book and pick a theoretical path for it
    NOTE: this function does not create folders
    """
    if len(book.series_links) == 0:
        return None
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


def post_process_downloaded_book(
    session: Session, book: Audiobook, abs_library_paths: list[str], torrent_path: str
):
    if not os.path.exists(torrent_path):
        raise MissingFile(torrent_path)

    # author
    if not (author := match_book_to_author_path(session, book, abs_library_paths)):
        logger.error(f"Failed to link book (asin {book.asin}), no author associated.")
        return

    if not author.save_path:
        logger.error(
            f"Failed to hard link book: author ({author.name}/{author.asin}) has no save_path"
        )
        return

    if len(book.series_links) == 0:
        Path(author.save_path).mkdir(parents=True, exist_ok=True)
        book_path = posixpath.join(author.save_path, book.title)

        logger.info(f"Linking book {book.asin} from {torrent_path} to {book_path}")
        process_files_to_location(
            torrent_path,
            book_path,
            postprocessing_config.get_disable_hardlinking(session) or False,
        )
        return

    # series
    series_link = match_book_to_series(book, author.save_path)
    assert series_link

    if not series_link.series.save_path:
        logger.error(
            f"Failed to hard link book: series ({series_link.series.title}/{series_link.series.asin}) has not save_path"
        )
        return
    Path(series_link.series.save_path).mkdir(parents=True, exist_ok=True)

    book_path = posixpath.join(
        series_link.series.save_path, f"Book {series_link.sequence} - {book.title}"
    )

    logger.info(f"Linking book {book.asin} from {torrent_path} to {book_path}")
    process_files_to_location(
        torrent_path,
        book_path,
        postprocessing_config.get_disable_hardlinking(session) or False,
    )


def process_files_to_location(src: str, dest: str, disable_hardlinking: bool):
    def log_cross_error(e: str):
        logger.warning(
            "Failed linking file: Detected a cross link error. Hard linking cannot function across different filesystems, if on docker consider using a single volume: %s",
            e,
        )

    def _is_cross_device_error_arg(arg: Any) -> bool: # pyright: ignore[reportExplicitAny, reportAny]
        """Check if a single argument represents a cross-device link error."""
        # Must be a tuple or list
        if not isinstance(arg, (tuple, list)):
            return False
        
        # Must have exactly 3 elements
        if len(arg) != 3: # pyright: ignore[reportUnknownArgumentType]
            return False
        
        # Third element must be a string with error indicators
        third = arg[2]  # pyright: ignore[reportUnknownVariableType]
        if not isinstance(third, str):
            return False
        
        return "[Errno 18]" in third or "Cross-device link" in third

    if not disable_hardlinking:
        try:
            _process_files_to_location_with_copy_function(src, dest, os.link)
        except shutil.Error as e:
            # Check if any argument matches the cross-device link pattern
            for arg in e.args: # pyright: ignore[reportAny]
                if _is_cross_device_error_arg(arg):
                    log_cross_error(str(e))
                    break

                logger.exception("Shutil Error: Failed to hard link file, attempting to copy")
        except OSError as e:
            if e.errno == 18:
                log_cross_error(str(e))
            else:
                logger.exception("OSError: Failed to hard link file, attempting to copy")
        except Exception:
            logger.exception("Unknown Error: Failed to hard link file, attempting to copy")
        else:
            return

    try:
        logger.info("Trying to copy now")
        _process_files_to_location_with_copy_function(src, dest, shutil.copy2)
    except Exception:
        logger.exception("Failed to copy file, aborting")
        return
    else:
        return


def _process_files_to_location_with_copy_function(
    src: str, dest: str, copy_function: Callable[[str, str], object]
):
    if not os.path.isfile(src):
        shutil.copytree(src, dest, copy_function=copy_function, dirs_exist_ok=True)
        return

    else:
        os.makedirs(dest, exist_ok=True)
        copy_function(src, posixpath.join(dest, os.path.basename(src)))
        return
