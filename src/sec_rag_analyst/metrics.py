"""Retrieval metrics: did the right page(s) show up among the retrieved chunks? No LLM needed."""


def gold_pages(question: dict) -> set[int]:
    """The 0-based page indexes of a FinanceBench question's evidence, without duplicates."""
    return {e["evidence_page_num"] for e in question["evidence"]}


def retrieval_scores(gold: set[int], retrieved: list[int], k: int = 5) -> dict:
    """Score one question.

    gold:      the evidence page indexes (from gold_pages)
    retrieved: page_index of each retrieved chunk, best chunk first (may repeat a page)
    Only the first k entries of `retrieved` count.

    Return a dict with:
      hit_any   True if at least one gold page is among the first k
      hit_all   True if every gold page is among the first k
      fraction  gold pages found / number of gold pages (0.0 to 1.0)
      rr        reciprocal rank: 1 / (rank of the first chunk on a gold page), rank starting at 1;
                0.0 if none of the first k is on a gold page
    """
    top_k= retrieved[:k]
    found = gold & set(top_k)
    print(found)

    rr = 0.0
    for rank, page in enumerate(top_k, start=1):
        if page in gold:
            rr = 1 / rank
            break

    return {
    "hit_any": len(found) > 0,
    "hit_all": found == gold,
    "fraction": len(found) / len(gold),
    "rr": rr,
}

def summarize(scores: list[dict]) -> dict:
    """Average over questions: hit_any rate, hit_all rate, mean fraction, and MRR (mean of rr)."""
    n = len(scores)
    return {
        "hit_rate": sum(s["hit_any"] for s in scores) / n,
        "full_recall": sum(s["hit_all"] for s in scores) / n,
        "mean_fraction": sum(s["fraction"] for s in scores) / n,
        "mrr": sum(s["rr"] for s in scores) / n,
    }