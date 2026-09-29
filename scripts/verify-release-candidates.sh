#!/bin/bash
# Read-only verification of the complete downloaded release inventory.
# Installed-package checks use the format-specific jobs; physical acceptance is separate.
set -euo pipefail
candidate_dir=$(realpath "${1:?Usage: verify-release-candidates.sh DIRECTORY VERSION SOURCE_REVISION}")
version=${2:?An explicit release version is required}
revision=${3:?An explicit source commit is required}
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
python3 "$script_dir/release_inventory.py" verify "$candidate_dir" \
    --version "$version" --revision "$revision"
printf 'Release inventory verified. Installed-package and physical acceptance remain separate gates.\n'
