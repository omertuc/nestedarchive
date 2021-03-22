import tempfile
import os
import posixpath
import shutil
import tarfile
from pathlib import Path
from urllib.parse import urlsplit, unquote
from typing import Union

import requests


def get(nested_archive_path: Union[str, Path], mode="r"):
    """
    Allows simplified access to files in nested archives.

    For example, given an archive placed in /tmp/foobar/foo.tar with this structure:
    foo.tar
        - foo1
        - foo2
        - bar.tar
           - bar1
           - bar2
           - foo3.tar.gz
                - foo4
                - foo5
        - abc/
           - def
           - ghi

    This function will allow reading the contents of the files in this nested archive in
    the following "seamless" manner:
        - nestedarchive.get("/tmp/foobar/foo.tar/foo1")
        - nestedarchive.get("/tmp/foobar/foo.tar/abc/def")
        - nestedarchive.get("/tmp/foobar/foo.tar/bar.tar/bar1")
        - nestedarchive.get("/tmp/foobar/foo.tar/bar.tar/foo3.tar.gz/foo4")

    Currently supported extensions:
        - tar
        - tar.gz

    Currently tested operating systems:
        - linux
    """
    return _get_recurse(nested_archive_path, cwd=Path.cwd(), mode=mode)


class RemoteNestedArchive:
    """
    Takes care of downloading and temporarily storing remote archives. Also
    provides a helper `.get` method that calls this library's get method on
    the downloaded archive.

    Example usage:
        >> archive = nestedarchive.RemoteNestedArchive("https://example.com/downloads/some.tar")
        >> contents = archive.get("/tmp/foobar/foo.tar/bar.tar/foo3.tar.gz/foo4")

    Note that this class creates a temporary directory to store the archive, and
    that temporary directory along with anything in it automatically gets deleted
    once the class instance is destructed.
    """
    def __init__(self, root_archive_url: str, delete=True):
        self.root_archive_url = root_archive_url
        self.tmpdir = Path(tempfile.mkdtemp())
        self.downloaded = False
        self.delete = delete

    @property
    def root_tar_file_path(self) -> Path:
        return self.tmpdir / _url2filename(self.root_archive_url)

    def _download_if_needed(self):
        if self.downloaded:
            return

        with requests.get(self.root_archive_url, allow_redirects=True, stream=True) as response:
            response.raise_for_status()
            with open(self.root_tar_file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

        self.downloaded = True

    def __del__(self):
        if not self.downloaded or not self.delete:
            return

        try:
            shutil.rmtree(self.tmpdir)
        except FileNotFoundError:
            pass

    def get(self, path: Union[Path, str], **kwargs):
        """
        Check `get`'s definition for available keyword arguments
        """
        self._download_if_needed()
        return get(self.root_tar_file_path / Path(path), **kwargs)


def _get_recurse(nested_archive_path: Path, cwd: Path, mode: str):
    print(nested_archive_path, cwd, mode)
    """
    Recursively strips path components from left to right, each time
    updating cwd to point to the current directory.

    If an archive is encountered in the path, it's implicitly extracted, with
    the contents stored as a sibling directory with name derived using the
    _nestedarchive_extracted_tar_name function, and then recursion continues
    with that new directory as cwd.

    This is done until the final path component is encountered, in that case,
    the file contents are read (using mode as the mode) and returned.
    """
    root_segment, *rest_of_segments = Path(nested_archive_path).parts

    current = cwd / root_segment

    # We reached the end of the path
    if len(rest_of_segments) == 0:
        if current.is_dir():
            raise ValueError("The final segment cannot be a directory")

        try:
            with open(current, mode) as f:
                return f.read()
        except FileNotFoundError as e:
            other_files = os.linesep.join(map(lambda path: path.name, current.parent.iterdir()))
            raise RuntimeError(f"Couldn't open {current}, but I found these other files:{os.linesep}{other_files}") from e

    # Simply recurse into regular directories, no unarchiving needed
    if current.is_dir():
        return _get_recurse(Path(*rest_of_segments), cwd=current, mode=mode)

    # If we reached this point, it means the user tried to "recurse" into an archive -
    # try to extract it an then recurse into that extracted directory

    extracted = cwd / _nestedarchive_extracted_tar_name(current.name)
    try:
        tarfile.open(current).extractall(path=extracted)
    except tarfile.ReadError as e:
        raise ValueError(f"Python's tarfile module failed to open {current}, file type unsupported") from e

    return _get_recurse(nested_archive_path=Path(*rest_of_segments), cwd=extracted, mode=mode)


def _nestedarchive_extracted_tar_name(original_archive):
    return Path(f".nestedarchive-extracted.{original_archive}")


# From https://gist.github.com/zed/c2168b9c52b032b5fb7d
def _url2filename(url):
    """Return basename corresponding to url.
    >>> print(url2filename('http://example.com/path/to/file%C3%80?opt=1'))
    fileÀ
    >>> print(url2filename('http://example.com/slash%2fname')) # '/' in name
    Traceback (most recent call last):
    ...
    ValueError
    """
    urlpath = urlsplit(url).path
    basename = posixpath.basename(unquote(urlpath))
    if os.path.basename(basename) != basename or unquote(posixpath.basename(urlpath)) != basename:
        raise ValueError  # reject '%2f' or 'dir%5Cbasename.ext' on Windows
    return basename
