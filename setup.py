import pathlib
from setuptools import setup

# The directory containing this file
HERE = pathlib.Path(__file__).parent

# The text of the README file
README = (HERE / "README.md").read_text()

# This call to setup() does all the work
setup(
    name="nestedarchive",
    version="0.2.4",
    description="Seamless reading of nested archives",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/omertuc/nestedarchive",
    author="Omer Tuchfeld",
    author_email="omer@tuchfeld.dev",
    license="MIT",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
    ],
    packages=["nestedarchive"],
    include_package_data=False,
    install_requires=["requests"],
)
