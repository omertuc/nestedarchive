#!/bin/bash

set -exo pipefail

if ! git diff-index --quiet HEAD --; then
    echo Dirty git
    exit 1
fi

python3 -m pip install twine wheel
python3 setup.py sdist bdist_wheel

set +x
echo @@@@@@@@@@@@@@@@@@@@@@@
echo @@@@@@@@@@@@@@@@@@@@@@@
echo @----Twine Check------@
echo @@@@@@@@@@@@@@@@@@@@@@@
echo @@@@@@@@@@@@@@@@@@@@@@@
set -x
twine check dist/*

if [[ $1 != --production ]]; then
    twine upload --repository-url https://test.pypi.org/legacy/ dist/* $@
fi 
