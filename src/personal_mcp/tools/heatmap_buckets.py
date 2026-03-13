from __future__ import annotations

from typing import Final

HEATMAP_BUCKET_COUNT: Final[int] = 5
HEATMAP_MAX_BUCKET_INDEX: Final[int] = HEATMAP_BUCKET_COUNT - 1


def shipped_density_bucket_index(shipped_density: int) -> int:
    """Map heatmap-ready shipped density into the shared bucket contract.

    Issue #257 fixed the v1 thresholds used by Issue #355:
    - bucket 0: 0
    - bucket 1: 1..4
    - bucket 2: 5..9
    - bucket 3: 10..19
    - bucket 4: 20+
    """
    if shipped_density <= 0:
        return 0
    if shipped_density <= 4:
        return 1
    if shipped_density <= 9:
        return 2
    if shipped_density <= 19:
        return 3
    return 4
