from personal_mcp.tools.heatmap_buckets import shipped_density_bucket_index


def test_shipped_density_bucket_index_boundaries() -> None:
    assert shipped_density_bucket_index(-3) == 0
    assert shipped_density_bucket_index(0) == 0
    assert shipped_density_bucket_index(1) == 1
    assert shipped_density_bucket_index(4) == 1
    assert shipped_density_bucket_index(5) == 2
    assert shipped_density_bucket_index(9) == 2
    assert shipped_density_bucket_index(10) == 3
    assert shipped_density_bucket_index(19) == 3
    assert shipped_density_bucket_index(20) == 4
    assert shipped_density_bucket_index(138) == 4
