from app.modules.analysis.scoring import clean_text_score


def test_no_findings_is_100():
    assert clean_text_score(1000, []) == (100.0, 0)


def test_empty_text_is_100():
    assert clean_text_score(0, [(0, 5)]) == (100.0, 0)


def test_single_span():
    score, flagged = clean_text_score(1000, [(0, 50)])
    assert flagged == 50
    assert score == 95.0


def test_duplicate_spans_count_once():
    score, flagged = clean_text_score(1000, [(10, 60), (10, 60)])
    assert flagged == 50
    assert score == 95.0


def test_overlapping_spans_merge():
    # [10,60) + [40,90) = [10,90) = 80 chars, not 100
    score, flagged = clean_text_score(1000, [(10, 60), (40, 90)])
    assert flagged == 80
    assert score == 92.0


def test_adjacent_spans_do_not_merge_gap():
    score, flagged = clean_text_score(100, [(0, 10), (20, 30)])
    assert flagged == 20
    assert score == 80.0


def test_spans_clamped_to_text():
    score, flagged = clean_text_score(100, [(-5, 10), (90, 200)])
    assert flagged == 20
    assert score == 80.0


def test_invalid_spans_ignored():
    score, flagged = clean_text_score(100, [(50, 50), (60, 40), (200, 300)])
    assert flagged == 0
    assert score == 100.0


def test_rounding_one_decimal():
    score, flagged = clean_text_score(3000, [(0, 40)])  # 1.333..% flagged
    assert flagged == 40
    assert score == 98.7
