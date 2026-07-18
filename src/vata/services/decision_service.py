import json
import math
import re
from collections import Counter
from typing import Dict, Iterable

from langchain_community.chat_models import ChatLiteLLM
from langchain_core.messages import SystemMessage, HumanMessage

from ..agents.config_loader import get_agent_config
from . import storage


# --- BM25 ranking (Okapi BM25) ---

_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")
_BM25_K1 = 1.5
_BM25_B = 0.75


def _tokenize(text: str) -> list[str]:
    if not text:
        return []
    return [t.lower() for t in _TOKEN_RE.findall(text)]


def bm25_score(documents: list[list[str]], query_tokens: list[str]) -> list[float]:
    """Return a BM25 score for each document.

    documents: list of token lists.
    query_tokens: tokenized query.
    """
    n = len(documents)
    if n == 0 or not query_tokens:
        return [0.0] * n

    doc_lens = [len(d) for d in documents]
    avgdl = sum(doc_lens) / n if n else 0.0

    # Document frequency per query term
    df: Counter = Counter()
    for d in documents:
        for term in set(query_tokens):
            if term in d:
                df[term] += 1

    # IDF (with +1 floor to avoid negatives on common terms)
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


def _index_doc_text(entry: dict) -> str:
    parts = [
        entry.get("summary", "") or "",
        " ".join(entry.get("tags", []) or []),
        entry.get("content_snippet", "") or "",
    ]
    return " ".join(parts)


# --- Search ---


_TOP_K_CATEGORIES = 5
_TOP_K_ASSETS_PER_CATEGORY = 15


def evaluate_nodes_for_query(query: str) -> Dict:
    config = get_agent_config("decision_ai")

    chat_model = ChatLiteLLM(
        model=config.get("model"),
        api_key=config.get("api_key") or None,
        api_base=config.get("api_base") or None,
        temperature=config.get("parameters", {}).get("temperature", 0.1),
        max_tokens=config.get("parameters", {}).get("max_tokens", 1000),
    )

    index = storage.load_index()
    if not index:
        return {"message": "Decision generated", "count": 0, "data": []}

    query_tokens = _tokenize(query)

    # --- Pass 1: rank categories via aggregated BM25 over their members ---
    category_overviews = []
    cat_docs: list[list[str]] = []
    cat_ids: list[str] = []

    for cid in storage.list_category_ids():
        members = storage.read_members(cid)
        if not members:
            continue
        meta_path = storage.meta_path(cid)
        category_name = cid
        if meta_path.exists():
            meta = storage.read_json(meta_path)
            if isinstance(meta, dict):
                category_name = meta.get("category", cid)

        agg_text_parts: list[str] = []
        all_tags: list[str] = []
        for aid in members:
            entry = index.get(aid)
            if not entry:
                continue
            agg_text_parts.append(_index_doc_text(entry))
            all_tags.extend(entry.get("tags", []) or [])

        agg_text = " ".join(agg_text_parts)
        cat_ids.append(cid)
        cat_docs.append(_tokenize(agg_text))
        category_overviews.append({
            "category_id": cid,
            "category_name": category_name,
            "keywords": list(dict.fromkeys(all_tags))[:20],
            "summary_snippet": agg_text[:500],
        })

    if not category_overviews:
        return {"message": "Decision generated", "count": 0, "data": []}

    cat_scores = bm25_score(cat_docs, query_tokens)
    ranked = sorted(zip(cat_ids, cat_scores), key=lambda x: x[1], reverse=True)
    bm25_top = [cid for cid, s in ranked[:_TOP_K_CATEGORIES] if s > 0]

    # Ask LLM to confirm/expand among the top BM25 candidates only.
    candidate_overviews = [c for c in category_overviews if c["category_id"] in bm25_top]
    relevant_category_ids: list[str] = []

    if candidate_overviews:
        cat_system_prompt = (
            "You are a category classification engine. Given a User Query and a list of "
            "Categories (with keywords and summaries), determine which categories are "
            "relevant. Return strictly a JSON array of category IDs, e.g. [\"id1\", \"id2\"]. "
            "Return [] if none match."
        )
        cat_user_message = (
            f"Query: {query}\n\nCategories:\n{json.dumps(candidate_overviews, indent=2)}"
        )
        try:
            cat_response = chat_model.invoke([
                SystemMessage(content=cat_system_prompt),
                HumanMessage(content=cat_user_message),
            ])
            cat_res_content = clean_json_response(cat_response.content)
            parsed = json.loads(cat_res_content)
            if isinstance(parsed, list):
                relevant_category_ids = [str(cid) for cid in parsed if cid in bm25_top]
        except Exception as e:
            print(f"Failed to identify relevant categories: {e}")

    if not relevant_category_ids:
        relevant_category_ids = bm25_top[:1]  # fallback to top BM25 category

    if not relevant_category_ids:
        return {"message": "Decision generated", "count": 0, "data": []}

    # --- Pass 2: BM25-rank assets within relevant categories, then ask LLM ---
    final_relevant_results: list[dict] = []
    asset_system_prompt = config.get("system_prompt", "")

    for category_id in relevant_category_ids:
        meta_path = storage.meta_path(category_id)
        if not meta_path.exists():
            continue
        meta = storage.read_json(meta_path)
        category_name = meta.get("category", "unknown") if isinstance(meta, dict) else "unknown"

        members = storage.read_members(category_id)
        scored: list[tuple[str, float, dict]] = []
        member_docs: list[list[str]] = []
        member_entries: list[tuple[str, dict]] = []
        for aid in members:
            entry = index.get(aid)
            if not entry:
                continue
            member_entries.append((aid, entry))
            member_docs.append(_tokenize(_index_doc_text(entry)))

        scores = bm25_score(member_docs, query_tokens)
        scored = [(aid, score, entry) for (aid, entry), score in zip(member_entries, scores)]
        scored.sort(key=lambda x: x[1], reverse=True)
        top = [s for s in scored if s[1] > 0][:_TOP_K_ASSETS_PER_CATEGORY]
        if not top:
            continue

        chunk = [{
            "asset_id": aid,
            "category": category_name,
            "summary": entry.get("summary", ""),
            "tags": entry.get("tags", []),
            "content_snippet": entry.get("content_snippet", ""),
        } for aid, _, entry in top]

        nodes_context = json.dumps(chunk, indent=2)
        user_msg = (
            f"Query: {query}\n\nNodes in category '{category_name}':\n{nodes_context}"
        )
        try:
            response = chat_model.invoke([
                SystemMessage(content=asset_system_prompt),
                HumanMessage(content=user_msg),
            ])
            res_content = clean_json_response(response.content)
            parsed = json.loads(res_content)
            if isinstance(parsed, list):
                for match in parsed:
                    matched_id = str(match.get("asset_id"))
                    node = next((n for n in chunk if n["asset_id"] == matched_id), None)
                    if node:
                        final_relevant_results.append({
                            "asset_id": node["asset_id"],
                            "category": node["category"],
                            "category_id": category_id,
                            "summary": node["summary"],
                            "tags": node["tags"],
                            "match_reason": match.get("reason", ""),
                            "content_snippet": node["content_snippet"],
                        })
        except Exception as e:
            print(f"Failed to parse assets for category {category_id}: {e}")
            continue

    return {
        "message": "Decision generated",
        "count": len(final_relevant_results),
        "data": final_relevant_results,
    }


def clean_json_response(content: str) -> str:
    content = content.strip()
    if content.startswith("```json"):
        content = content.split("```json", 1)[1].split("```", 1)[0].strip()
    elif content.startswith("```"):
        content = content.split("```", 1)[1].split("```", 1)[0].strip()
    return content
