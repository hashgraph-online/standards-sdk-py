#!/usr/bin/env bash
set -euo pipefail

"${PREFIX}/bin/python" -m pip install --disable-pip-version-check "hedera-sdk-py>=2.50.0,<3.0.0"
