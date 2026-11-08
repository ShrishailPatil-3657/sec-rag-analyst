import pytest

from sec_rag_analyst.metrics import gold_pages, retrieval_scores, summarize


def q(*pages):
    return {"evidence": [{"evidence_page_num": p} for p in pages]}


def test_gold_pages_removes_duplicates():
    assert gold_pages(q(3, 3, 7)) == {3, 7}


def test_hit_on_first_chunk():
    s = retrieval_scores({10}, [10, 4, 5, 6, 7])
    assert s == {"hit_any": True, "hit_all": True, "fraction": 1.0, "rr": 1.0}


def test_hit_at_rank_three():
    s = retrieval_scores({10}, [1, 2, 10, 4, 5])
    assert s["hit_any"] and s["rr"] == pytest.approx(1 / 3)


def test_miss():
    s = retrieval_scores({10}, [1, 2, 3, 4, 5])
    assert s == {"hit_any": False, "hit_all": False, "fraction": 0.0, "rr": 0.0}


def test_partial_hit_on_two_page_question():
    s = retrieval_scores({10, 20}, [10, 1, 2, 3, 4])
    assert s["hit_any"] and not s["hit_all"] and s["fraction"] == 0.5


def test_only_first_k_count():
    s = retrieval_scores({10}, [1, 2, 3, 4, 5, 10], k=5)
    assert not s["hit_any"]


def test_repeated_page_does_not_double_count():
    s = retrieval_scores({10, 20}, [10, 10, 10, 10, 10])
    assert s["fraction"] == 0.5


def test_summarize():
    scores = [
        {"hit_any": True, "hit_all": True, "fraction": 1.0, "rr": 1.0},
        {"hit_any": True, "hit_all": False, "fraction": 0.5, "rr": 0.5},
        {"hit_any": False, "hit_all": False, "fraction": 0.0, "rr": 0.0},
        {"hit_any": False, "hit_all": False, "fraction": 0.0, "rr": 0.0},
    ]
    assert summarize(scores) == {"hit_rate": 0.5, "full_recall": 0.25, "mean_fraction": 0.375, "mrr": 0.375}
