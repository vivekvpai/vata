"""Search / find: BM25 pre-filter over categories, then over assets within
the relevant categories, then an optional LLM re-rank pass. Ported from the
original vata `decision_service.py`, adapted to the Mongo storage layer.
Runs fully on BM25 alone (no LLM required) when no model is configured.
"""

import json
import math
import os
import re
from collections import Counter

from . import storage

_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")
_BM25_K1 = 1.5
_BM25_B = 0.75

_TOP_K_CATEGORIES = 5
_TOP_K_ASSETS_PER_CATEGORY = 15

_LLM_MODEL = os.getenv("VATA_LLM_MODEL")


def _tokenize(text: str) -> list[str]:
    if not text:
        return []
    return [t.lower() for t in _TOKEN_RE.findall(text)]


def bm25_score(documents: list[list[str]], query_tokens: list[str]) -> list[float]:
    n = len(documents)
    if n == 0 or not query_tokens:
        return [0.0] * n

    doc_lens = [len(d) for d in documents]
    avgdl = sum(doc_lens) / n if n else 0.0

    df: Counter = Counter()
    for d in documents:
        for term in set(query_tokens):
            if term in d:
                df[term] += 1

    idf = {
        term: math.log(1.0 + (n - df.get(term, 0) + 0.5) / (df.get(term, 0) + 0.5))
        for term in set(query_tokens)
    }

    scores = []
    for i, doc in enumerate(documents):
        tf = Counter(doc)
        s = 0.0
        for term in query_tokens:
            f = tf.get(term, 0)
            if f == 0:
                continue
            denom = f + _BM25_K1 * (1 - _BM25_B + _BM25_B * (doc_lens[i] / (avgdl or 1.0)))
            s += idf[term] * (f * (_BM25_K1 + 1)) / denom
        scores.append(s)
    return scores


def _asset_doc_text(asset: dict) -> str:
    return " ".join([
        asset.get("title", "") or "",
        asset.get("description", "") or "",
        " ".join(asset.get("tags", []) or []),
        (asset.get("content", "") or "")[:500],
    ])


def _clean_json(content: str) -> str:
    content = content.strip()
    if content.startswith("```json"):
        content = content.split("```json", 1)[1].split("```", 1)[0].strip()
    elif content.startswith("```"):
        content = content.split("```", 1)[1].split("```", 1)[0].strip()
    return content


def _llm_invoke(system_prompt: str, user_message: str) -> str | None:
    if not _LLM_MODEL:
        return None
    try:
        import litellm

        response = litellm.completion(
            model=_LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.1,
            max_tokens=1000,
        )
        return response["choices"][0]["message"]["content"]
    except Exception as e:  # pragma: no cover
        print(f"[vata-mcp] decision_service: LLM call failed, using BM25-only result: {e}")
        return None


def evaluate_nodes_for_query(query: str) -> dict:
    query_tokens = _tokenize(query)
    categories = storage.list_categories()
    if not categories:
        return {"message": "Decision generated", "count": 0, "assets": [], "categories": []}

    # --- Pass 1: rank categories via aggregated BM25 over their members ---
    cat_docs: list[list[str]] = []
    cat_ids: list[str] = []
    cat_overviews = []

    for cat in categories:
        cid = cat["_id"]
        members = storage.list_assets_in_category(cid)
        if not members:
            continue
        agg_parts, all_tags = [], []
        for asset in members:
            agg_parts.append(_asset_doc_text(asset))
            all_tags.extend(asset.get("tags", []) or [])

        agg_text = " ".join(agg_parts)
        cat_ids.append(cid)
        cat_docs.append(_tokenize(agg_text))
        cat_overviews.append({
            "category_id": cid,
            "category_name": cat["category"],
            "keywords": list(dict.fromkeys(all_tags))[:20],
            "summary_snippet": agg_text[:500],
        })

    if not cat_overviews:
        return {"message": "Decision generated", "count": 0, "assets": [], "categories": []}

    cat_scores = bm25_score(cat_docs, query_tokens)
    ranked = sorted(zip(cat_ids, cat_scores), key=lambda x: x[1], reverse=True)
    bm25_top = [cid for cid, s in ranked[:_TOP_K_CATEGORIES] if s > 0]

    relevant_category_ids: list[str] = []
    candidate_overviews = [c for c in cat_overviews if c["category_id"] in bm25_top]

    if candidate_overviews and _LLM_MODEL:
        system_prompt = (
            "You are a category classification engine. Given a User Query and a list of "
            "Categories (with keywords and summaries), determine which categories are "
            'relevant. Return strictly a JSON array of category IDs, e.g. ["id1", "id2"]. '
            "Return [] if none match."
        )
        user_message = f"Query: {query}\n\nCategories:\n{json.dumps(candidate_overviews, indent=2)}"
        raw = _llm_invoke(system_prompt, user_message)
        if raw:
            try:
                parsed = json.loads(_clean_json(raw))
                if isinstance(parsed, list):
                    relevant_category_ids = [str(c) for c in parsed if c in bm25_top]
            except Exception as e:
                print(f"[vata-mcp] decision_service: failed to parse category response: {e}")

    if not relevant_category_ids:
        relevant_category_ids = bm25_top  # BM25-only: trust the ranking as-is

    if not relevant_category_ids:
        return {"message": "Decision generated", "count": 0, "assets": [], "categories": []}

    # --- Pass 2: BM25-rank assets within relevant categories ---
    results: list[dict] = []

    for cid in relevant_category_ids:
        cat = storage.get_category(cid)
        if not cat:
            continue
        category_name = cat["category"]
        members = storage.list_assets_in_category(cid)

        entries = [(a["_id"], a) for a in members]
        docs = [_tokenize(_asset_doc_text(a)) for a in members]

        scores = bm25_score(docs, query_tokens)
        scored = sorted(zip(entries, scores), key=lambda x: x[1], reverse=True)
        top = [(aid, asset, s) for (aid, asset), s in scored if s > 0][:_TOP_K_ASSETS_PER_CATEGORY]
        if not top:
            continue

        chunk = [{
            "asset_id": aid,
            "category": category_name,
            "title": asset.get("title", ""),
            "description": asset.get("description", ""),
            "tags": asset.get("tags", []),
            "content": asset.get("content", ""),
        } for aid, asset, _ in top]

        if _LLM_MODEL:
            system_prompt = (
                "You are a retrieval assistant. Given a query and a list of candidate "
                "notes (nodes), return the ones genuinely relevant to the query as a "
                'JSON array: [{"asset_id": "...", "reason": "..."}]. Return [] if none match.'
            )
            user_message = f"Query: {query}\n\nNodes in category '{category_name}':\n{json.dumps(chunk, indent=2)}"
            raw = _llm_invoke(system_prompt, user_message)
            matched = None
            if raw:
                try:
                    matched = json.loads(_clean_json(raw))
                except Exception as e:
                    print(f"[vata-mcp] decision_service: failed to parse asset response for {cid}: {e}")
            if isinstance(matched, list):
                for match in matched:
                    matched_id = str(match.get("asset_id"))
                    node = next((n for n in chunk if n["asset_id"] == matched_id), None)
                    if node:
                        results.append({**node, "category_id": cid, "match_reason": match.get("reason", "")})
                continue

        # BM25-only fallback: take the ranked chunk as-is
        for node in chunk:
            results.append({**node, "category_id": cid, "match_reason": "keyword match"})

    matched_categories = []
    seen_cids = set()
    for r in results:
        cid = r["category_id"]
        if cid in seen_cids:
            continue
        seen_cids.add(cid)
        cat = storage.get_category(cid)
        if cat:
            matched_categories.append({
                "category_id": cid,
                "category": cat["category"],
                "description": cat.get("description", ""),
                "match_count": sum(1 for r2 in results if r2["category_id"] == cid),
            })

    return {
        "message": "Decision generated",
        "count": len(results),
        "assets": results,
        "categories": matched_categories,
    }
