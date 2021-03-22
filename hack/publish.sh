#!/bin/bash

set -euxo pipefail

if git status; then
    echo "Dirty working directory"
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
