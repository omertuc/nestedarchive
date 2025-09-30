import tarfile
from pathlib import Path
from typing import Union, Generator
import logging

logging.basicConfig(level=logging.INFO)


def get(nested_archive_path: Union[str, Path], mode="r"):
    """
    See README.md for examples and documentations for this function
    """
    nested_archive_path = Path(nested_archive_path)
    try:
        return next(_get_recurse(nested_archive_path, cwd=Path.cwd(), mode=mode, original=nested_archive_path))
    except StopIteration:
        raise FileNotFoundError(f"Couldn't find any file or directory matching: {nested_archive_path}") from None


def get_all(nested_archive_path: Union[str, Path]):
    nested_archive_path = Path(nested_archive_path)
    return list(_get_recurse(nested_archive_path, cwd=Path.cwd(), mode=None, original=nested_archive_path))


def _get_recurse(nested_archive_path: Path, cwd: Path, mode: str | None, original: Path) -> Generator[Union[bytes, str, Path]]:
    """
    Recursively strips path components from left to right, each time
    updating cwd to point to the current directory.

    If an archive is encountered in the path, it's implicitly extracted, with
    the contents stored as a sibling directory with name derived using the
    _nestedarchive_extracted_tar_name function, and then recursion continues
    with that new directory as cwd.

    This is done until the final path component is encountered, in that case,
    the file contents are read (using mode as the mode) and returned.

    If the final path component is a directory, the path of the directory is
    returned.
    """
    root_segment, *rest_of_segments = nested_archive_path.parts

    current = cwd / root_segment

    logging.debug(f"Current segment: {current}, rest: {rest_of_segments}, cwd: {cwd}")

    # We reached the end of the path
    if len(rest_of_segments) == 0:
        logging.debug(f"Reached end of path, final segment: {current}")

        matches = list(current.parent.glob(current.name))

        logging.debug(f"Found {len(matches)} matches for {current}: {matches}")

        for match in matches:
            if match.is_dir():
                logging.debug(f"Glob found a directory, returning path {current}")
                yield current
                continue

            try:
                logging.debug(f"Reading file {match} with mode {mode}")
                with open(match, "rb" if mode is None else mode) as f:
                    logging.debug(f"Successfully opened file {match}, yielding contents")
                    yield f.read()
            except FileNotFoundError as e:
                raise FileNotFoundError("File not found - this shouldn't happen, expected to fail earlier") from e
            except UnicodeDecodeError as e:
                raise RuntimeError("""Looks like you're trying to get a non utf-8 encoded file, try using the mode="rb" kwarg for the get method""") from e

        logging.debug(f"Finished processing all matches for {current}")

        return

    logging.debug(f"Looking for {current.name} in {cwd}")
    for candidate in current.parent.glob(current.name) if current.name != "" else (current,):
        logging.debug(f"Considering candidate: {candidate}")

        if candidate.is_dir():
            # Simply recurse into regular directories, no unarchiving needed
            yield from _get_recurse(Path(*rest_of_segments),
                                    cwd=candidate, mode=mode, original=original)
            return
        else:
            # If we reached this point, it means the user tried to "recurse" into an archive -
            # try to extract it an then recurse into that extracted directory

            extracted = cwd / _nestedarchive_extracted_tar_name(candidate.name)

            logging.debug(f"Extracting archive {candidate} to {extracted}")
            if not extracted.exists():
                try:
                    tarfile.open(candidate).extractall(path=extracted, filter='data')
                except tarfile.ReadError as e:
                    raise RuntimeError(f"Failed to recurse into archive {candidate}, file type unsupported") from e

            logging.debug(f"Recursing into extracted archive at {extracted}")
            yield from _get_recurse(nested_archive_path=Path(*rest_of_segments),
                                    cwd=extracted, mode=mode, original=original)
            continue


def _nestedarchive_extracted_tar_name(original_archive):
    return Path(f".nestedarchive-extracted.{original_archive}")
