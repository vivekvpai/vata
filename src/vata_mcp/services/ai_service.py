"""AI decision layer: category assignment + tag/summary suggestion.

Tries a real LLM via `litellm` when `VATA_LLM_MODEL` (+ credentials) is
configured. Otherwise falls back to a deterministic local heuristic so the
whole server runs with zero API keys during local/dummy development.
"""

import json
import os
import re
from collections import Counter

from . import storage

_LLM_MODEL = os.getenv("VATA_LLM_MODEL")
_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "for",
    "is", "are", "was", "were", "be", "been", "this", "that", "with", "as",
    "it", "its", "at", "by", "from", "i", "we", "you", "my", "our",
}
_WORD_RE = re.compile(r"[A-Za-z0-9']+")


def _use_llm() -> bool:
    return bool(_LLM_MODEL)


def _llm_invoke(system_prompt: str, user_message: str) -> str | None:
    """Best-effort LLM call. Returns None on any failure so callers fall
    back to the heuristic path instead of raising."""
    if not _use_llm():
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
            max_tokens=500,
        )
        return response["choices"][0]["message"]["content"]
    except Exception as e:  # pragma: no cover - network/config dependent
        print(f"[vata-mcp] ai_service: LLM call failed, falling back to heuristic: {e}")
        return None


def _clean_json(content: str) -> str:
    content = content.strip()
    if content.startswith("```json"):
        content = content.split("```json", 1)[1].split("```", 1)[0].strip()
    elif content.startswith("```"):
        content = content.split("```", 1)[1].split("```", 1)[0].strip()
    return content


def _keywords(text: str, top_n: int = 5) -> list[str]:
    words = [w.lower() for w in _WORD_RE.findall(text) if w.lower() not in _STOPWORDS and len(w) > 2]
    counts = Counter(words)
    return [w for w, _ in counts.most_common(top_n)]


def _heuristic_tags(content: str, existing_tags: list[str] | None) -> list[str]:
    if existing_tags:
        return existing_tags
    return _keywords(content, top_n=5)


def _heuristic_summary(content: str, existing_summary: str | None) -> str:
    if existing_summary:
        return existing_summary
    snippet = " ".join(content.split())
    return snippet[:140] + ("..." if len(snippet) > 140 else "")


def _heuristic_category(content: str, tags: list[str]) -> str:
    """Score existing categories by token overlap with content+tags; fall
    back to a new category named after the strongest keyword."""
    existing = storage.list_categories()
    content_tokens = set(_keywords(content, top_n=10)) | {t.lower() for t in tags}

    best_name = None
    best_score = 0
    for cat in existing:
        name_tokens = set(_WORD_RE.findall(cat["category"].lower()))
        score = len(content_tokens & name_tokens)
        member_ids = storage.members_of_category(cat["_id"])
        for aid in member_ids[:20]:
            asset = storage.get_asset(aid)
            if not asset:
                continue
            asset_tokens = set(asset.get("tags", [])) | set(_keywords(asset.get("main_content", ""), 10))
            score += len(content_tokens & asset_tokens)
        if score > best_score:
            best_score = score
            best_name = cat["category"]

    if best_name and best_score > 0:
        return best_name

    top_keywords = _keywords(content, top_n=1)
    return (top_keywords[0].capitalize() if top_keywords else "General")


async def decide_category_and_metadata(
    content: str, summary: str | None = None, tags: list[str] | None = None
) -> dict:
    """Returns {"category": str, "summary": str, "tags": list[str]}.

    Category may be an existing category name or a brand-new one; caller
    is responsible for resolving/creating the category_id.
    """
    existing_categories = [c["category"] for c in storage.list_categories()]

    if _use_llm():
        system_prompt = (
            "You are a filing assistant. Given new content and a list of existing "
            "categories, decide which single category it belongs to (reuse an "
            "existing one whenever it reasonably fits; only propose a new short "
            "category name when nothing fits). Also produce a one-sentence summary "
            "and up to 5 lowercase tags if not already provided. Respond strictly as "
            'JSON: {"category": "...", "summary": "...", "tags": ["...", ...]}'
        )
        user_message = (
            f"Existing categories: {json.dumps(existing_categories)}\n\n"
            f"Content: {content}\n"
            f"Current summary: {summary or '(none)'}\n"
            f"Current tags: {tags or '(none)'}"
        )
        raw = _llm_invoke(system_prompt, user_message)
        if raw:
            try:
                parsed = json.loads(_clean_json(raw))
                return {
                    "category": str(parsed.get("category") or "General"),
                    "summary": str(parsed.get("summary") or summary or _heuristic_summary(content, summary)),
                    "tags": list(parsed.get("tags") or tags or _heuristic_tags(content, tags)),
                }
            except Exception as e:
                print(f"[vata-mcp] ai_service: failed to parse LLM response, using heuristic: {e}")

    resolved_tags = _heuristic_tags(content, tags)
    resolved_summary = _heuristic_summary(content, summary)
    resolved_category = _heuristic_category(content, resolved_tags)
    return {"category": resolved_category, "summary": resolved_summary, "tags": resolved_tags}


async def fetch_suggestions(content: str, summary: str | None = None, tags: list[str] | None = None) -> dict:
    """Standalone suggestion tool (vata_suggest) — same decision, exposed
    directly without saving anything."""
    return await decide_category_and_metadata(content, summary, tags)
