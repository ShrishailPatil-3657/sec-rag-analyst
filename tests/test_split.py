import json
from pathlib import Path

from sec_rag_analyst.split import make_split

DATA = Path("data/financebench/data/financebench_open_source.jsonl")


def load():
    return [json.loads(line) for line in DATA.read_text().splitlines()]


def test_sizes_and_no_overlap():
    s = make_split(load())
    assert len(s["held_out"]) == 50
    assert len(s["dev"]) == 100
    assert not set(s["dev"]) & set(s["held_out"])
    assert len(set(s["dev"]) | set(s["held_out"])) == 150


def test_quick_comes_from_dev():
    s = make_split(load())
    assert len(s["quick"]) == 30
    assert set(s["quick"]) <= set(s["dev"])


def test_balanced_across_question_groups():
    qs = load()
    label = {q["financebench_id"]: q["question_type"] for q in qs}
    s = make_split(qs)
    counts = {}
    for i in s["held_out"]:
        counts[label[i]] = counts.get(label[i], 0) + 1
    assert all(16 <= n <= 17 for n in counts.values()) and len(counts) == 3


def test_same_seed_same_split_and_different_seed_differs():
    qs = load()
    assert make_split(qs, seed=1) == make_split(qs, seed=1)
    assert make_split(qs, seed=1) != make_split(qs, seed=2)
