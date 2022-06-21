import os
import tarfile
from pathlib import Path
from typing import Union


def get(nested_archive_path: Union[str, Path], mode="r"):
    """
    See README.md for examples and documentations for this function
    """
    nested_archive_path = Path(nested_archive_path)
    return _get_recurse(nested_archive_path, cwd=Path.cwd(), mode=mode, original=nested_archive_path)


def _get_recurse(nested_archive_path: Path, cwd: Path, mode: str, original: Path):
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
    root_segment, *rest_of_segments = nested_archive_path.parts

    current = cwd / root_segment

    # We reached the end of the path
    if len(rest_of_segments) == 0:
        if current.is_dir():
            raise ValueError("The final segment cannot be a directory")

        try:
            current = next(current.parent.glob(current.name))
        except StopIteration:
            other_files = os.linesep.join(map(lambda path: path.name, current.parent.iterdir()))
            raise FileNotFoundError(
                f"Couldn't find a file matching {current}, but I found these other files:{os.linesep}{other_files}")

        try:
            with open(current, mode) as f:
                return f.read()
        except FileNotFoundError as e:
            raise FileNotFoundError("File not found - this shouldn't happen, expected to fail earlier") from e
        except UnicodeDecodeError as e:
            raise RuntimeError("""Looks like you're trying to get a non utf-8 encoded file, try using the mode="rb" kwarg for the get method""") from e

    # Support globs - see README for more information
    exceptions = []
    for candidate in current.parent.glob(current.name) if current.name != "" else (current,):
        try:
            if candidate.is_dir():
                # Simply recurse into regular directories, no unarchiving needed
                return _get_recurse(Path(*rest_of_segments),
                                    cwd=candidate, mode=mode, original=original)

            # If we reached this point, it means the user tried to "recurse" into an archive -
            # try to extract it an then recurse into that extracted directory

            extracted = cwd / _nestedarchive_extracted_tar_name(candidate.name)

            if not extracted.exists():
                try:
                    tarfile.open(candidate).extractall(path=extracted)
                except tarfile.ReadError as e:
                    raise ValueError(f"Python's tarfile module failed to open {candidate}, file type unsupported") from e

            return _get_recurse(nested_archive_path=Path(*rest_of_segments),
                                cwd=extracted, mode=mode, original=original)
        except FileNotFoundError as e:
            exceptions.append(e)
    else:
        encountered_message = (f". Errors encountered:{os.linesep}{os.linesep.join(map(str, exceptions))}"
                               if len(exceptions) != 0 else
                               "")
        raise FileNotFoundError(
            f"Couldn't find any files matching {original}{encountered_message}")


def _nestedarchive_extracted_tar_name(original_archive):
    return Path(f".nestedarchive-extracted.{original_archive}")
