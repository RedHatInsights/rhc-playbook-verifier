#!/bin/bash
set -euo pipefail

cd ../
venv=$(mktemp --directory)
python3 -m venv "${venv}"
# shellcheck source=/dev/null
source "${venv}/bin/activate"
pip install .

# for debugging
python3 --version
pip freeze

python3 -m unittest discover python/tests/integration/
