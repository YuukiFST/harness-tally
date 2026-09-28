"""Every tracked path must fit Windows MAX_PATH inside pip's clone directory.

pip clones a git pin to %TEMP%\\pip-install-<8>\\harness-tally_<32 hex>\\ (about 100
characters). On 2026-09-28 capture paths of 154+ characters made that clone fail with
"Filename too long", so the harness-bench pin could not install on Windows.
"""

import subprocess
from pathlib import Path

MAX_TRACKED_PATH = 125
REPO = Path(__file__).resolve().parents[1]


def test_tracked_paths_fit_in_pip_clone_on_windows() -> None:
    listed = subprocess.run(["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True).stdout
    too_long = [path for path in listed.splitlines() if len(path) > MAX_TRACKED_PATH]
    assert too_long == []
