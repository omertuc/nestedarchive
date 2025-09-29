import os
import tarfile
from pathlib import Path
from typing import Union, List


def get(nested_archive_path: Union[str, Path], mode="r"):
    """
    See README.md for examples and documentations for this function
    """
    nested_archive_path = Path(nested_archive_path)
    return _get_recurse(nested_archive_path, cwd=Path.cwd(), mode=mode, original=nested_archive_path)


def get_all(nested_archive_path: Union[str, Path], mode="r") -> List[Path]:
    """
    Similar to get(), but returns all matches for glob patterns instead of just the first one.
    Returns a list of Path objects for all matches.
    
    Args:
        nested_archive_path: Path to the nested archive file or directory
        mode: File opening mode (default: "r" for text, "rb" for binary)
        
    Returns:
        List of Path objects for all matching files and directories.
        
    Examples:
        >>> # Get all .txt files in a nested archive
        >>> results = get_all("/tmp/archive.tar/foo*.txt")
        >>> for filepath in results:
        ...     print(f"File: {filepath}")
        ...     with open(filepath, 'r') as f:
        ...         content = f.read()
        ...         print(f"Content: {content}")
        
        >>> # Get all items matching a pattern (could be files or directories)
        >>> results = get_all("/tmp/archive.tar/bar.tar/*")
        >>> for path in results:
        ...     if path.is_dir():
        ...         print(f"Directory: {path}")
        ...     else:
        ...         print(f"File: {path}")
    """
    nested_archive_path = Path(nested_archive_path)
    return _get_all_recurse(nested_archive_path, cwd=Path.cwd(), mode=mode, original=nested_archive_path)


def _get_recurse(nested_archive_path: Path, cwd: Path, mode: str, original: Path) -> Union[Path, Union[str, bytes]]:
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

    # We reached the end of the path
    if len(rest_of_segments) == 0:
        if current.is_dir():
            return current

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

    # Non-terminal case - process candidates and recurse
    return _process_candidates(current, rest_of_segments, cwd, mode, original)


def _get_all_recurse(nested_archive_path: Path, cwd: Path, mode: str, original: Path) -> List[Path]:
    """
    Recursively processes nested archives and returns ALL matches for glob patterns.
    Similar to _get_recurse but collects all results instead of returning the first match.
    Returns Path objects for all matches (both files and directories).
    """
    root_segment, *rest_of_segments = nested_archive_path.parts
    current = cwd / root_segment

    # Terminal case - we reached the end of the path
    if len(rest_of_segments) == 0:
        # Get ALL matches for glob pattern (could be files, directories, or both)
        matches = list(current.parent.glob(current.name))
        if not matches:
            other_files = os.linesep.join(map(lambda path: path.name, current.parent.iterdir()))
            raise FileNotFoundError(
                f"Couldn't find any files matching {current}, but I found these other files:{os.linesep}{other_files}")

        # Return all matches as Path objects
        return matches

    # Non-terminal case - process candidates and collect all results
    return _process_all_candidates(current, rest_of_segments, cwd, mode, original)


def _process_candidates(current: Path, rest_of_segments: list, cwd: Path, mode: str, original: Path) -> Union[Path, Union[str, bytes]]:
    """
    Process candidates for non-terminal case (when there are more path segments to process).
    Handles glob patterns and tries each candidate until one succeeds.
    
    Args:
        current: Current path segment being processed
        rest_of_segments: Remaining path segments to process
        cwd: Current working directory
        mode: File opening mode
        original: Original path for error reporting
        
    Returns:
        Result from the first successful candidate
        
    Raises:
        FileNotFoundError: If no candidates succeed
    """
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
                    ex = ValueError(f"Python's tarfile module failed to open {candidate}, file type unsupported")
                    ex.__cause__ = e
                    exceptions.append(e)

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


def _process_all_candidates(current: Path, rest_of_segments: list, cwd: Path, mode: str, original: Path) -> List[Path]:
    """
    Process candidates for non-terminal case and collect ALL results for glob patterns.
    Similar to _process_candidates but collects all successful results instead of returning the first one.
    Returns Path objects for all matches (both files and directories).
    
    Args:
        current: Current path segment being processed
        rest_of_segments: Remaining path segments to process
        cwd: Current working directory
        mode: File opening mode
        original: Original path for error reporting
        
    Returns:
        List of all successful results from all candidates
        
    Raises:
        FileNotFoundError: If no candidates succeed
    """
    all_results = []
    exceptions = []
    
    for candidate in current.parent.glob(current.name) if current.name != "" else (current,):
        try:
            if candidate.is_dir():
                # Simply recurse into regular directories, no unarchiving needed
                results = _get_all_recurse(Path(*rest_of_segments), cwd=candidate, mode=mode, original=original)
                all_results.extend(results)
            else:
                # Handle archive extraction and recurse
                extracted = cwd / _nestedarchive_extracted_tar_name(candidate.name)
                
                if not extracted.exists():
                    try:
                        tarfile.open(candidate).extractall(path=extracted)
                    except tarfile.ReadError as e:
                        ex = ValueError(f"Python's tarfile module failed to open {candidate}, file type unsupported")
                        ex.__cause__ = e
                        exceptions.append(ex)
                        continue
                
                results = _get_all_recurse(Path(*rest_of_segments), cwd=extracted, mode=mode, original=original)
                all_results.extend(results)
        except FileNotFoundError as e:
            exceptions.append(e)
    
    if not all_results and exceptions:
        encountered_message = (f". Errors encountered:{os.linesep}{os.linesep.join(map(str, exceptions))}"
                               if len(exceptions) != 0 else
                               "")
        raise FileNotFoundError(f"Couldn't find any files matching {original}{encountered_message}")
    
    return all_results


def _nestedarchive_extracted_tar_name(original_archive):
    return Path(f".nestedarchive-extracted.{original_archive}")
