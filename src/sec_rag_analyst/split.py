"""Split the 150 FinanceBench questions into dev, held-out, and a quick-debug subset."""
import random
from collections import defaultdict


def make_split(questions: list[dict], seed: int = 42, held_out_size: int = 50, quick_size: int = 30) -> dict:
    """Return {"dev": [ids], "held_out": [ids], "quick": [ids]}.

    Rules (see docs/superpowers/specs/2026-11-07-eval-harness-design.md):
    - ids are the `financebench_id` values.
    - held_out has `held_out_size` questions, dev has all the rest; no id in both.
    - Each `question_type` group is split in the same proportion, so dev and held_out
      both contain a mix of metrics-generated, domain-relevant and novel-generated.
    - quick is `quick_size` ids taken from dev only.
    - Same seed, same input -> same output.
    """
    groups = defaultdict(list)
    for q in questions:
        groups[q["question_type"]].append(q["financebench_id"])
    # print(groups)

    rng = random.Random(seed)  # one generator, reused for every random choice below

    # how many held-out questions each group gives: proportional share, rounded down,
    # then the leftover seats go one each to the groups with the largest remainders
    total = len(questions)
    labels = sorted(groups)
    shares = {label: held_out_size * len(groups[label]) / total for label in labels}
    counts = {label: int(shares[label]) for label in labels}
    leftover = held_out_size - sum(counts.values())
    # print({"Shares":shares, "Counts":counts, "Leftovers": leftover})
    by_remainder = sorted(labels, key=lambda label: shares[label] - counts[label], reverse=True)
    for label in by_remainder[:leftover]:
        counts[label] += 1

    held_out, dev = [], []
    for label in labels:  # sorted labels, so the order of random draws is fixed
        ids = sorted(groups[label])  # sorted first, so the shuffle does not depend on file order
        rng.shuffle(ids)
        held_out += ids[: counts[label]]
        dev += ids[counts[label] :]

    quick = rng.sample(dev, quick_size)  # a subset of dev, not extra questions
    return {"dev": dev, "held_out": held_out, "quick": quick}
