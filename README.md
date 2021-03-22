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

This library will allow reading the contents of the files in this nested archive in
the following "seamless" manner:
```
nestedarchive.get("/tmp/foobar/foo.tar/foo1")
nestedarchive.get("/tmp/foobar/foo.tar/abc/def")
nestedarchive.get("/tmp/foobar/foo.tar/bar.tar/bar1")
nestedarchive.get("/tmp/foobar/foo.tar/bar.tar/foo3.tar.gz/foo4")
```

Globs are also supported - all matches are tried until one is found that (eventually) contains the expected file, e.g.:
```
- nestedarchive.get("/tmp/foobar/foo.tar/bar.tar/foo*.tar.gz/foo7")
```
Will first silently try `foo3.tar.gz` and fail because it does not contain `foo7`, then it will try `foo6.tar.gz` and
succeed because `foo6.tar.gz` contains `foo7`

Currently supported extensions:
- tar
- tar.gz

Currently tested operating systems:
- linux
