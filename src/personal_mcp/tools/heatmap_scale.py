from __future__ import annotations

from typing import Final

# Issue #257 decision:
# keep zero-day handling explicit, then map filled shipped_density values
# through stable fixed buckets informed by the 2026-03-12 audit snapshot.
SHIPPED_DENSITY_FILLED_BUCKET_MAXES: Final[tuple[int, ...]] = (4, 9, 19)


def shipped_density_bucket(count: int) -> int:
    """Return the stable bucket index for one shipped heatmap day."""
    if count <= 0:
        return 0
    for index, upper_bound in enumerate(SHIPPED_DENSITY_FILLED_BUCKET_MAXES, start=1):
        if count <= upper_bound:
            return index
    return len(SHIPPED_DENSITY_FILLED_BUCKET_MAXES) + 1
