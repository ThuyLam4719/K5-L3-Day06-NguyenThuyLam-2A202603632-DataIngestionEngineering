"""TODO: evaluate retrieved evidence and preserve per-query traces."""
from typing import Any


def evaluate_query(question: dict[str, Any], hits: list[dict[str, Any]]) -> dict[str, Any]:
    """TODO: check source/page and enough gold evidence; keep hit@1 and hit@3 trace.

    Accept any documented alternative gold evidence. Do not infer human grounding
    or chunk coherence labels from exact string match.
    """
    import re
    import unicodedata

    def normalize(value: str) -> str:
        value = unicodedata.normalize("NFC", value or "")
        return re.sub(r"\s+", " ", value).strip().casefold()

    evidence = normalize(question.get("evidence_quote", ""))
    gold_source = str(question.get("gold_source_id", ""))
    gold_page = str(question.get("gold_page", ""))

    evaluated_hits = []
    for hit in hits:
        same_source = str(hit.get("document_id", "")) == gold_source
        same_page = str(hit.get("page", "")) == gold_page
        has_evidence = bool(evidence) and evidence in normalize(hit.get("text", ""))

        evaluated_hits.append({
            **hit,
            "gold_source_page_match": same_source and same_page,
            "contains_gold_evidence": same_source and same_page and has_evidence,
        })

    hit1 = bool(
        evaluated_hits
        and evaluated_hits[0]["contains_gold_evidence"]
    )
    hit3 = any(item["contains_gold_evidence"] for item in evaluated_hits[:3])

    return {
        "id": question.get("id"),
        "split": question.get("split"),
        "question": question.get("question"),
        "expected_answer": question.get("expected_answer"),
        "gold_source_id": question.get("gold_source_id"),
        "gold_page": question.get("gold_page"),
        "evidence_quote": question.get("evidence_quote"),
        "filter": question.get("filter"),
        "hit_at_1": hit1,
        "evidence_hit_at_3": hit3,
        "hits": evaluated_hits[:3],
    }


def summarize(traces: list[dict[str, Any]]) -> dict[str, Any]:
    groups = {}

    for trace in traces:
        key = (trace["strategy"], trace["split"])
        groups.setdefault(key, []).append(trace)

    summary = []
    for (strategy, split), items in sorted(groups.items()):
        total = len(items)
        hit1_count = sum(item["hit_at_1"] for item in items)
        hit3_count = sum(item["evidence_hit_at_3"] for item in items)

        summary.append({
            "strategy": strategy,
            "split": split,
            "questions": total,
            "hit_at_1": hit1_count,
            "hit_at_1_rate": hit1_count / total if total else 0,
            "evidence_hit_at_3": hit3_count,
            "evidence_hit_at_3_rate": hit3_count / total if total else 0,
        })

    return summary
