"""Cloud persistence shim.

On Cloud Run, the container filesystem is ephemeral — anything written to
disk is lost when the instance scales to zero.  The previous implementation
backed the watchlist up to a Render environment variable via the Render API.

That Render code path is gone (we migrated to Google Cloud Run; see
``docs/superpowers/specs/2026-07-17-gcp-cloud-run-deploy-design.md``).

For now, both ``restore_watchlist()`` and ``backup_watchlist()`` are no-ops.
A future spec will mirror watchlist (and other data) to the provisioned GCS
bucket. The public function signatures are preserved so callers in
``app.py`` and ``queries.py`` stay unchanged.

Usage
-----
On app startup, call ``restore_watchlist()`` after ``storage.init_settings()``.
After every write to the watchlist JSON file, call ``backup_watchlist()``.
"""
from __future__ import annotations

import logging
from pathlib import Path

log = logging.getLogger(__name__)


def restore_watchlist(data_dir: str | Path) -> None:
    """No-op on Cloud Run. GCS mirroring is a future spec."""
    log.debug("restore_watchlist is a no-op on Cloud Run (GCS mirroring not yet enabled)")


def backup_watchlist(data_dir: str | Path) -> None:
    """No-op on Cloud Run. GCS mirroring is a future spec."""
    log.debug("backup_watchlist is a no-op on Cloud Run (GCS mirroring not yet enabled)")
