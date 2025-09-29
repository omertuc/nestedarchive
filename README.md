<a href="https://pypi.org/project/nestedarchive/"><img alt="PyPI" src="https://img.shields.io/pypi/v/nestedarchive"></a>

Allows simplified access to files in nested archives.

# Example
Given an archive placed in `/tmp/foobar/foo.tar` with this structure:
```
foo.tar
    - foo1
    - foo2
    - bar.tar
       - bar1
       - bar2
       - foo3.tar.gz
            - foo4
            - foo5
       - foo6.tar.gz
            - foo7
            - foo8
    - abc/
       - def
       - ghi
```

This library provides two main functions for accessing files in nested archives:

## `get()` - Single File Access
Reads the contents of a single file in a nested archive:
```python
nestedarchive.get("/tmp/foobar/foo.tar/foo1")
nestedarchive.get("/tmp/foobar/foo.tar/abc/def")
nestedarchive.get("/tmp/foobar/foo.tar/bar.tar/bar1")
nestedarchive.get("/tmp/foobar/foo.tar/bar.tar/foo3.tar.gz/foo4")
```

Globs are supported - all matches are tried until one is found that (eventually) contains the expected file:
```python
nestedarchive.get("/tmp/foobar/foo.tar/bar.tar/foo*.tar.gz/foo7")
```
Will first silently try `foo3.tar.gz` and fail because it does not contain `foo7`, then it will try `foo6.tar.gz` and
succeed because `foo6.tar.gz` contains `foo7`

## `get_all()` - Multiple File Discovery
Returns all files and directories matching a glob pattern as Path objects:
```python
# Get all .txt files
results = nestedarchive.get_all("/tmp/foobar/foo.tar/*.txt")
for filepath in results:
    print(f"Found file: {filepath}")
    with open(filepath, 'r') as f:
        content = f.read()
        print(f"Content: {content}")

# Get all items in a directory (files and directories)
results = nestedarchive.get_all("/tmp/foobar/foo.tar/bar.tar/*")
for path in results:
    if path.is_dir():
        print(f"Directory: {path}")
    else:
        print(f"File: {path}")

# Get all files in nested archives
results = nestedarchive.get_all("/tmp/foobar/foo.tar/bar.tar/foo*.tar.gz/*")
for filepath in results:
    print(f"File in nested archive: {filepath}")
```

## API Comparison

| Function | Purpose | Returns | Use Case |
|----------|---------|---------|----------|
| `get()` | Read single file content | File content (str/bytes) or Path | Get specific file content |
| `get_all()` | Find multiple files/directories | List of Path objects | Discover and process multiple files |

## Installation and Usage

```python
import nestedarchive

# Single file access
content = nestedarchive.get("/path/to/archive.tar/file.txt")
print(content)

# Multiple file discovery
file_paths = nestedarchive.get_all("/path/to/archive.tar/*.log")
for path in file_paths:
    print(f"Log file: {path}")

# Working with remote archives
archive = nestedarchive.RemoteNestedArchive("https://example.com/archive.tar")
content = archive.get("/nested/path/file.txt")
file_paths = archive.get_all("/nested/path/*.txt")
```

Currently supported extensions:
- tar
- tar.gz

Currently tested operating systems:
- linux
