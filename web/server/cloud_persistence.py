"""Cloud persistence shim.

On Cloud Run, the container filesystem is ephemeral — anything written to
disk is lost when the instance scales to zero.  The GCS-backed storage
layer in ``storage.py`` (enabled when ``GCS_BUCKET`` is set) transparently
persists all data to the provisioned Cloud Storage bucket.

``restore_watchlist()`` and ``backup_watchlist()`` are preserved as public
API hooks for callers in ``app.py`` and ``queries.py``.  With GCS enabled
they are no-ops because the underlying IO already reads/writes the bucket.
"""

from __future__ import annotations

import logging
from pathlib import Path

log = logging.getLogger(__name__)


def _gcs_active() -> bool:
    try:
        from web.server import gcs
        return gcs.is_enabled()
    except ImportError:
        return False


def restore_watchlist(data_dir: str | Path) -> None:
    """Restore watchlist from GCS (no-op — GCS is the primary backend)."""
    if _gcs_active():
        log.debug("restore_watchlist: GCS active, data is already cloud-backed")
    else:
        log.debug("restore_watchlist: no GCS bucket configured; local filesystem only")


def backup_watchlist(data_dir: str | Path) -> None:
    """Backup watchlist to GCS (no-op — GCS is the primary backend)."""
    if _gcs_active():
        log.debug("backup_watchlist: GCS active, data is already cloud-backed")
    else:
        log.debug("backup_watchlist: no GCS bucket configured; local filesystem only")
