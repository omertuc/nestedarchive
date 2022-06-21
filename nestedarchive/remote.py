import shutil
import tempfile
import posixpath
import os
from pathlib import Path
from typing import Union
from urllib.parse import urlsplit, unquote

import nestedarchive
import requests

class RemoteNestedArchive:
    """
    Takes care of downloading and temporarily storing remote archives. Also
    provides a helper `.get` method that calls this library's get method on
    the downloaded archive.

    Example usage:
    >>> archive = nestedarchive.RemoteNestedArchive("https://example.com/downloads/some.tar")
    >>> contents = archive.get("/tmp/foobar/foo.tar/bar.tar/foo3.tar.gz/foo4")

    Note that this class creates a temporary directory to store the archive, and
    that temporary directory along with anything in it automatically gets deleted
    once the class instance is destructed.
    """
    def __init__(self, root_archive_url: str, delete=True, init_download=False):
        self.root_archive_url = root_archive_url
        self.tmpdir = Path(tempfile.mkdtemp())
        self.downloaded = False
        self.delete = delete

        if init_download:
            self._download_if_needed()

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
        return nestedarchive.get(self.root_tar_file_path / Path(path), **kwargs)


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
