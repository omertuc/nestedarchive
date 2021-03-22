#!/bin/bash

set -eo pipefail

if [[ -z "$1" ]]; then
    echo "
Bumps the version where needed.

Modifies the patch component by default, manually change this script to minor/major if
you wish to bump other components.

Requires the bumpversion command (python3 -m pip install bumpversion)

USAGE: $0 current_version new_version"
exit 1
fi

current_version=$1
shift

bumpversion --current-version $current_version patch setup.py nestedarchive/__init__.py $@
