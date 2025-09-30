import pytest
import tempfile
import tarfile
import os
from pathlib import Path
from typing import List, Union
import shutil

from nestedarchive.get import get, get_all


@pytest.fixture
def temp_dir():
    """Create a temporary directory that gets cleaned up after tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def simple_file_content():
    """Simple text content for test files."""
    return "Hello, World!"


@pytest.fixture
def binary_file_content():
    """Binary content for test files."""
    return b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"


@pytest.fixture
def create_simple_file(temp_dir, simple_file_content):
    """Create a simple text file."""
    def _create_file(filename: str, content: str = None) -> Path:
        content = content or simple_file_content
        file_path = temp_dir / filename
        file_path.write_text(content)
        return file_path
    return _create_file


@pytest.fixture
def create_binary_file(temp_dir, binary_file_content):
    """Create a binary file."""
    def _create_file(filename: str, content: bytes = None) -> Path:
        content = content or binary_file_content
        file_path = temp_dir / filename
        file_path.write_bytes(content)
        return file_path
    return _create_file


@pytest.fixture
def create_tar_archive(temp_dir):
    """Create a tar archive with specified files."""
    def _create_tar(archive_name: str, files: List[dict]) -> Path:
        """
        Create a tar archive with files.
        
        Args:
            archive_name: Name of the archive file
            files: List of dicts with 'name' and 'content' keys
        """
        archive_path = temp_dir / archive_name
        
        with tarfile.open(archive_path, 'w') as tar:
            for file_info in files:
                # Create temporary file with content
                temp_file = temp_dir / f"temp_{file_info['name'].replace('/', '_')}"
                
                # Create parent directory if needed
                temp_file.parent.mkdir(parents=True, exist_ok=True)
                
                if isinstance(file_info['content'], bytes):
                    temp_file.write_bytes(file_info['content'])
                else:
                    temp_file.write_text(file_info['content'])
                
                # Add to tar with the desired name
                tar.add(temp_file, arcname=file_info['name'])
                
                # Clean up temp file
                temp_file.unlink()
        
        return archive_path
    return _create_tar


@pytest.fixture
def create_nested_structure(temp_dir, create_tar_archive, simple_file_content):
    """Create complex nested archive structures for testing."""
    def _create_structure(structure_type: str) -> dict:
        """
        Create different types of nested structures.
        
        Returns a dict with paths and expected contents for testing.
        """
        if structure_type == "simple_nested":
            # Create: outer.tar -> inner.tar -> file.txt
            inner_files = [{"name": "file.txt", "content": "Inner file content"}]
            inner_tar = create_tar_archive("inner.tar", inner_files)
            
            # Read inner.tar as bytes to put in outer.tar
            with open(inner_tar, 'rb') as f:
                inner_tar_bytes = f.read()
            
            outer_files = [{"name": "inner.tar", "content": inner_tar_bytes}]
            outer_tar = create_tar_archive("outer.tar", outer_files)
            
            return {
                "archive_path": outer_tar,
                "nested_path": "outer.tar/inner.tar/file.txt",
                "expected_content": "Inner file content"
            }
        
        elif structure_type == "multi_level":
            # Create: level1.tar -> level2.tar -> level3.tar -> deep_file.txt
            level3_files = [{"name": "deep_file.txt", "content": "Deep nested content"}]
            level3_tar = create_tar_archive("level3.tar", level3_files)
            
            with open(level3_tar, 'rb') as f:
                level3_bytes = f.read()
            
            level2_files = [{"name": "level3.tar", "content": level3_bytes}]
            level2_tar = create_tar_archive("level2.tar", level2_files)
            
            with open(level2_tar, 'rb') as f:
                level2_bytes = f.read()
            
            level1_files = [{"name": "level2.tar", "content": level2_bytes}]
            level1_tar = create_tar_archive("level1.tar", level1_files)
            
            return {
                "archive_path": level1_tar,
                "nested_path": "level1.tar/level2.tar/level3.tar/deep_file.txt",
                "expected_content": "Deep nested content"
            }
        
        elif structure_type == "multiple_files":
            # Create: archive.tar with multiple files at different levels
            files = [
                {"name": "root_file.txt", "content": "Root level file"},
                {"name": "subdir/sub_file.txt", "content": "Subdirectory file"}
            ]
            archive = create_tar_archive("multi.tar", files)
            
            return {
                "archive_path": archive,
                "files": {
                    "multi.tar/root_file.txt": "Root level file",
                    "multi.tar/subdir/sub_file.txt": "Subdirectory file"
                }
            }
        
        elif structure_type == "mixed_content":
            # Create archive with both text and binary content
            text_content = "Text file content"
            binary_content = b"\x00\x01\x02\x03Binary data\x04\x05\x06"
            
            files = [
                {"name": "text.txt", "content": text_content},
                {"name": "binary.bin", "content": binary_content}
            ]
            archive = create_tar_archive("mixed.tar", files)
            
            return {
                "archive_path": archive,
                "text_path": "mixed.tar/text.txt",
                "binary_path": "mixed.tar/binary.bin",
                "text_content": text_content,
                "binary_content": binary_content
            }
    
    return _create_structure


def _flatten_generator(gen):
    """Helper function to flatten nested generators."""
    for item in gen:
        if hasattr(item, '__iter__') and not isinstance(item, (str, bytes, Path)):
            try:
                yield from _flatten_generator(item)
            except TypeError:
                yield item
        else:
            yield item


class TestGet:
    """Test the get() function (returns first match)."""
    
    def test_get_simple_file(self, create_simple_file, temp_dir):
        """Test getting a simple file."""
        file_path = create_simple_file("test.txt", "Test content")
        
        # Change to temp directory for relative path testing
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            result = get("test.txt")
            assert result == "Test content"
        finally:
            os.chdir(original_cwd)
    
    def test_get_binary_file(self, create_binary_file, temp_dir):
        """Test getting a binary file."""
        binary_content = b"Binary test data"
        file_path = create_binary_file("test.bin", binary_content)
        
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            result = get("test.bin", mode="rb")
            assert result == binary_content
        finally:
            os.chdir(original_cwd)
    
    def test_get_nested_archive(self, create_nested_structure, temp_dir):
        """Test getting file from nested archive."""
        structure = create_nested_structure("simple_nested")
        
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            result = get(structure["nested_path"])
            assert result == structure["expected_content"]
        finally:
            os.chdir(original_cwd)
    
    def test_get_deep_nested(self, create_nested_structure, temp_dir):
        """Test getting file from deeply nested archive."""
        structure = create_nested_structure("multi_level")
        
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            result = get(structure["nested_path"])
            assert result == structure["expected_content"]
        finally:
            os.chdir(original_cwd)
    
    def test_get_file_not_found(self, temp_dir):
        """Test get() raises FileNotFoundError for non-existent files."""
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            with pytest.raises(FileNotFoundError):
                get("nonexistent.txt")
        finally:
            os.chdir(original_cwd)
    
    def test_get_unicode_decode_error(self, create_binary_file, temp_dir):
        """Test get() raises RuntimeError for binary files opened in text mode."""
        # Create a file with non-UTF-8 content
        binary_content = b"\x80\x81\x82\x83"  # Invalid UTF-8
        create_binary_file("invalid_utf8.txt", binary_content)
        
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            with pytest.raises(RuntimeError, match="non utf-8 encoded file"):
                get("invalid_utf8.txt")  # Default mode is "r" (text)
        finally:
            os.chdir(original_cwd)


class TestGetAll:
    """Test the get_all() function (returns all matches)."""
    
    def test_get_all_single_file(self, create_simple_file, temp_dir):
        """Test get_all() with a single file."""
        file_path = create_simple_file("test.txt", "Single file content")
        
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            results = get_all("test.txt")
            assert len(results) == 1
            assert results[0] == b"Single file content"
        finally:
            os.chdir(original_cwd)
    
    def test_get_all_multiple_files(self, create_nested_structure, temp_dir):
        """Test get_all() with multiple files matching pattern."""
        structure = create_nested_structure("multiple_files")
        
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            
            # Test getting specific files
            for file_path, expected_content in structure["files"].items():
                results = get_all(file_path)
                assert len(results) == 1
                assert results[0] == expected_content.encode()
        finally:
            os.chdir(original_cwd)
    
    def test_get_all_glob_pattern(self, temp_dir, create_simple_file):
        """Test get_all() with glob patterns."""
        # Create multiple files with similar names
        create_simple_file("test1.txt", "Content 1")
        create_simple_file("test2.txt", "Content 2")
        create_simple_file("other.txt", "Other content")
        
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            
            # This should match test1.txt and test2.txt
            results = get_all("test*.txt")
            assert len(results) == 2
            assert b"Content 1" in results
            assert b"Content 2" in results
            assert b"Other content" not in results
        finally:
            os.chdir(original_cwd)
    
    def test_get_all_binary_files(self, create_nested_structure, temp_dir):
        """Test get_all() with binary content."""
        structure = create_nested_structure("mixed_content")
        
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            
            # Test text file
            text_results = get_all(structure["text_path"])
            assert len(text_results) == 1
            assert text_results[0] == structure["text_content"].encode()
            
            # Test binary file
            binary_results = get_all(structure["binary_path"])
            assert len(binary_results) == 1
            assert binary_results[0] == structure["binary_content"]
        finally:
            os.chdir(original_cwd)
    
    def test_get_all_empty_result(self, temp_dir):
        """Test get_all() returns empty list when no files match."""
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            results = get_all("nonexistent*.txt")
            assert results == []
        finally:
            os.chdir(original_cwd)
    
    def test_get_all_nested_with_multiple_matches(self, temp_dir, create_tar_archive):
        """Test get_all() with nested archives containing multiple matching files."""
        # Create archive with multiple files that could match a pattern
        files = [
            {"name": "log1.txt", "content": "Log entry 1"},
            {"name": "log2.txt", "content": "Log entry 2"},
            {"name": "readme.txt", "content": "Readme content"}
        ]
        archive = create_tar_archive("logs.tar", files)
        
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            
            # Test getting specific files
            results1 = get_all("logs.tar/log1.txt")
            assert len(results1) == 1
            assert results1[0] == b"Log entry 1"
            
            results2 = get_all("logs.tar/log2.txt")
            assert len(results2) == 1
            assert results2[0] == b"Log entry 2"
            
            # Test pattern matching
            log_results = get_all("logs.tar/log*.txt")
            assert len(log_results) == 2
            assert b"Log entry 1" in log_results
            assert b"Log entry 2" in log_results
        finally:
            os.chdir(original_cwd)


class TestCompatibility:
    """Test compatibility between get() and get_all()."""
    
    def test_get_vs_get_all_single_match(self, create_simple_file, temp_dir):
        """Test that get() returns the same as get_all()[0] for single matches."""
        create_simple_file("unique.txt", "Unique content")
        
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            
            get_result = get("unique.txt", mode="rb")
            get_all_results = get_all("unique.txt")
            
            assert len(get_all_results) == 1
            assert get_result == get_all_results[0]
        finally:
            os.chdir(original_cwd)
    
    def test_get_returns_first_match(self, temp_dir, create_simple_file):
        """Test that get() returns the first match when multiple files match."""
        create_simple_file("match1.txt", "First match")
        create_simple_file("match2.txt", "Second match")
        
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            
            get_result = get("match*.txt", mode="rb")
            get_all_results = get_all("match*.txt")
            
            assert len(get_all_results) == 2
            assert get_result == get_all_results[0]
            assert b"First match" in get_all_results
            assert b"Second match" in get_all_results
        finally:
            os.chdir(original_cwd)


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_directory_access(self, temp_dir):
        """Test accessing directories."""
        subdir = temp_dir / "subdir"
        subdir.mkdir()
        
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            
            # get() should return the Path object for directories
            result = get("subdir")
            assert isinstance(result, Path)
            assert result.name == "subdir"
            
            # get_all() should also work with directories
            results = get_all("subdir")
            assert len(results) == 1
            assert isinstance(results[0], Path)
            assert results[0].name == "subdir"
        finally:
            os.chdir(original_cwd)
    
    def test_extraction_directory_creation(self, create_nested_structure, temp_dir):
        """Test that extraction directories are created properly."""
        structure = create_nested_structure("simple_nested")
        
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            
            # First access should create extraction directory
            result = get(structure["nested_path"])
            assert result == structure["expected_content"]
            
            # Check that extraction directory exists
            expected_extraction_dir = temp_dir / ".nestedarchive-extracted.outer.tar"
            assert expected_extraction_dir.exists()
            assert expected_extraction_dir.is_dir()
            
            # Second access should use existing extraction directory
            result2 = get(structure["nested_path"])
            assert result2 == structure["expected_content"]
        finally:
            os.chdir(original_cwd)
    
    def test_invalid_archive_format(self, temp_dir, create_simple_file):
        """Test handling of invalid archive files."""
        # Create a file that looks like an archive but isn't
        fake_tar = create_simple_file("fake.tar", "This is not a real tar file")
        
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            
            with pytest.raises(RuntimeError):
                get("fake.tar/somefile.txt")
        finally:
            os.chdir(original_cwd)