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

Currently supported extensions:
- tar
- tar.gz

Currently tested operating systems:
- linux
