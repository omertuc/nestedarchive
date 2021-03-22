#!/bin/bash

if [[ -z "$1" ]]; then
    echo "
Publish to pypi. Pass --production to upload to actual pypi

Don't forget to bump the version!

Requires twine and wheel:
python3 -m pip install twine wheel

USAGE: $0 [--production|--test]"
exit 1
fi

set -exo pipefail

if ! git diff-index --quiet HEAD --; then
    echo Dirty git
    exit 1
fi

rm -rf dist/*
rm -rf build/*

python3 setup.py sdist bdist_wheel

set +x
echo @@@@@@@@@@@@@@@@@@@@@@@
echo @@@@@@@@@@@@@@@@@@@@@@@
echo @----Twine Check------@
echo @@@@@@@@@@@@@@@@@@@@@@@
echo @@@@@@@@@@@@@@@@@@@@@@@
set -x
twine check dist/*

deploy_env=$1
shift

if [[ $deploy_env != --production ]]; then
    twine upload --repository-url https://test.pypi.org/legacy/ dist/* --verbose $@
else
    twine upload --repository-url dist/* --verbose $@
fi 
