import os
import rapidfuzz
from rapidfuzz import fuzz, utils
import posixpath
import shutil

from app.internal.models import Audiobook, AudiobookSeriesLink

def match_book_to_author_path(book: Audiobook, abs_library_paths: list[str]) -> str:
    """ Returns path of matched author
        If no author can be matched then it will pick the first author and create folders as needed
    """
    # TODO: Check for already saved authors and series

    abs_authors: list[str] = []
    abs_authors_full_path: list[str] = []
    
    for path in abs_library_paths:
        dir_scan = os.listdir(path)
        abs_authors.extend(dir_scan)
        abs_authors_full_path.extend([f"{path}/{item}" for item in dir_scan])

    author_path = None
    for book_author in book.authors:
        best_match = rapidfuzz.process.extractOne(book_author, abs_authors, scorer=fuzz.partial_ratio, processor=utils.default_process)
        if best_match and best_match[1] >= 90:
            author_path = abs_authors_full_path[best_match[2]]
            break

    if not author_path:
        author_path = posixpath.join(abs_library_paths[0], book.authors[0])
        # Save new author path
        os.mkdir(author_path)

    return author_path

def match_book_to_series(book: Audiobook, author_path: str) -> tuple[str, AudiobookSeriesLink]:
    """ Returns tuple (path of series folder, matched series from book.series_links)
        If no series can be matched then it will pick the first series and create folders as needed
    """
    abs_serieses = os.listdir(author_path)

    series_path = None
    matched_series = None
    for series_link in book.series_links:
        book_series = series_link.series.title
        best_match = rapidfuzz.process.extractOne(book_series, abs_serieses, scorer=fuzz.partial_ratio, processor=utils.default_process)
        if best_match and best_match[1] >= 90:
            series_path = posixpath.join(author_path, best_match[0])
            matched_series = book.series_links[best_match[2]]
            break

    if not series_path or not matched_series:
        series_path = posixpath.join(author_path, book.series_links[0].series.title)
        matched_series = book.series_links[0]
        # Save new author path
        os.mkdir(series_path)

    return (series_path, matched_series)

class MissingFile(Exception):
    path: str

    def __init__(self, path: str, **kargs: object) -> None:
        super().__init__(**kargs)
        self.path = path

def hard_link_book(book: Audiobook, abs_library_paths: list[str], torrent_path: str):
    if not os.path.exists(torrent_path):
        raise MissingFile(torrent_path)

    # author
    author_path = match_book_to_author_path(book, abs_library_paths)
    torrent_path_is_folder = not os.path.isfile(torrent_path)

    if len(book.series_links) < 0:
        book_path = posixpath.join(author_path, book.title) 
        if torrent_path_is_folder:
            shutil.copytree(torrent_path, book_path, copy_function=os.link)
        else:
            os.mkdir(book_path)
            os.link(torrent_path, posixpath.join(book_path, os.path.basename(torrent_path)))

    # series
    (series_path, matched_series) = match_book_to_series(book, author_path)

    book_path = posixpath.join(series_path, f"Book {matched_series.sequence} - {book.title}")

    if torrent_path_is_folder:
        shutil.copytree(torrent_path, book_path, copy_function=os.link)
    else:
        os.mkdir(book_path)
        os.link(torrent_path, posixpath.join(book_path, os.path.basename(torrent_path)))
