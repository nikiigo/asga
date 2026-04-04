#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="${ROOT_DIR}/.venv/bin/python"

if [[ ! -x "${VENV_PYTHON}" ]]; then
  echo "Missing ${VENV_PYTHON}. Create the virtualenv first." >&2
  exit 1
fi

"${VENV_PYTHON}" -m PyInstaller --noconfirm asga.spec

echo "Built release artifact:"
echo "${ROOT_DIR}/dist/asga"
