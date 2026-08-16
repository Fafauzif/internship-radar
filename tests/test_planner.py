from internship_radar.planner import rotating_slice


def test_rotating_slice_respects_limit_and_wraps():
    items = [{"query": str(i)} for i in range(5)]
    out = rotating_slice(items, 3, seed=4)
    assert len(out) == 3
    assert len({x["query"] for x in out}) == 3


def test_rotating_slice_never_exceeds_available_items():
    items = [{"query": "a"}]
    assert len(rotating_slice(items, 10, seed=1)) == 1
