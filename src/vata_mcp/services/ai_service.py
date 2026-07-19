"""AI decision layer: category assignment + title/description/tag generation.

Tries a real LLM via `litellm` when `VATA_LLM_MODEL` (+ credentials) is
configured. Otherwise falls back to a deterministic local heuristic so the
whole server runs with zero API keys during local/dummy development.

Content saved via vata_save is usually a link, sometimes plain text — both
are supported. The AI always produces: a short title, the category it
belongs to (existing or new, with a description if new), a one-sentence
description of the content, and up to 5 tags.
"""

import json
import os
import re
from collections import Counter
from urllib.parse import urlparse

from . import storage

_LLM_MODEL = os.getenv("VATA_LLM_MODEL")
_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "for",
    "is", "are", "was", "were", "be", "been", "this", "that", "with", "as",
    "it", "its", "at", "by", "from", "i", "we", "you", "my", "our",
}
_WORD_RE = re.compile(r"[A-Za-z0-9']+")
_URL_RE = re.compile(r"^https?://", re.IGNORECASE)


def is_link(content: str) -> bool:
    return bool(_URL_RE.match((content or "").strip()))


def _use_llm() -> bool:
    return bool(_LLM_MODEL)


def backend_info() -> dict:
    return {
        "backend": _LLM_MODEL if _use_llm() else "local heuristic (keyword overlap, no LLM configured)",
        "llm_configured": _use_llm(),
    }


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


def _heuristic_tags(content: str, user_description: str, existing_tags: list[str] | None) -> list[str]:
    if existing_tags:
        return existing_tags
    return _keywords(f"{content} {user_description}", top_n=5)


def _heuristic_title(content: str, user_description: str) -> str:
    if is_link(content):
        parsed = urlparse(content.strip())
        path_hint = parsed.path.strip("/").split("/")[-1].replace("-", " ").replace("_", " ")
        if user_description:
            base = " ".join(user_description.split())[:60]
            return base
        if path_hint:
            return f"{parsed.netloc} — {path_hint}"[:80]
        return parsed.netloc or content[:60]
    snippet = " ".join(content.split())
    return snippet[:60] + ("..." if len(snippet) > 60 else "")


def _heuristic_description(content: str, user_description: str) -> str:
    if user_description:
        text = " ".join(user_description.split())
        return text[:200] + ("..." if len(text) > 200 else "")
    if is_link(content):
        return f"Link: {content.strip()}"
    text = " ".join(content.split())
    return text[:200] + ("..." if len(text) > 200 else "")


def _heuristic_category(content: str, user_description: str, tags: list[str]) -> str:
    """Score existing categories by token overlap with content+tags; fall
    back to a new category named after the strongest keyword."""
    existing = storage.list_categories()
    content_tokens = set(_keywords(f"{content} {user_description}", top_n=10)) | {t.lower() for t in tags}

    best_name = None
    best_score = 0
    for cat in existing:
        name_tokens = set(_WORD_RE.findall(cat["category"].lower()))
        score = len(content_tokens & name_tokens)
        for asset in storage.list_assets_in_category(cat["_id"])[:20]:
            asset_tokens = set(asset.get("tags", [])) | set(
                _keywords(f"{asset.get('title', '')} {asset.get('description', '')}", 10)
            )
            score += len(content_tokens & asset_tokens)
        if score > best_score:
            best_score = score
            best_name = cat["category"]

    if best_name and best_score > 0:
        return best_name

    top_keywords = _keywords(f"{content} {user_description}", top_n=1)
    return (top_keywords[0].capitalize() if top_keywords else "General")


def _heuristic_category_description(category_name: str, tags: list[str]) -> str:
    tag_hint = ", ".join(tags[:3]) if tags else category_name.lower()
    return f"Notes and links related to {tag_hint}."


async def decide_asset_metadata(
    content: str, description: str | None = None, tags: list[str] | None = None
) -> dict:
    """Returns {"title", "category", "category_description", "description",
    "tags", "is_link"}.

    `content` is a link or freeform text. `description` is an optional
    user-supplied hint about the content (e.g. why it's worth saving) —
    used to steer title/description/category generation, not stored
    verbatim unless the AI has nothing better.
    """
    content_is_link = is_link(content)
    existing_categories = [c["category"] for c in storage.list_categories()]

    if _use_llm():
        system_prompt = (
            "You are a filing assistant for a personal link/notes archive. Given "
            "new content (a URL or freeform text) and an optional user hint about "
            "why it's being saved, produce: a short title (<=80 chars), which "
            "single existing category it belongs to (reuse whenever it reasonably "
            "fits) or a new short category name if nothing fits (with a one-sentence "
            "category_description only when the category is new), a one-sentence "
            "description of the content itself, and up to 5 lowercase tags if not "
            "already provided. Respond strictly as JSON: "
            '{"title": "...", "category": "...", "category_description": "...", '
            '"description": "...", "tags": ["...", ...]}'
        )
        user_message = (
            f"Existing categories: {json.dumps(existing_categories)}\n\n"
            f"Content ({'URL' if content_is_link else 'text'}): {content}\n"
            f"User hint / description: {description or '(none)'}\n"
            f"Current tags: {tags or '(none)'}"
        )
        raw = _llm_invoke(system_prompt, user_message)
        if raw:
            try:
                parsed = json.loads(_clean_json(raw))
                resolved_tags = list(parsed.get("tags") or tags or _heuristic_tags(content, description or "", tags))
                resolved_category = str(parsed.get("category") or "General")
                return {
                    "title": str(parsed.get("title") or _heuristic_title(content, description or "")),
                    "category": resolved_category,
                    "category_description": str(
                        parsed.get("category_description")
                        or _heuristic_category_description(resolved_category, resolved_tags)
                    ),
                    "description": str(parsed.get("description") or _heuristic_description(content, description or "")),
                    "tags": resolved_tags,
                    "is_link": content_is_link,
                }
            except Exception as e:
                print(f"[vata-mcp] ai_service: failed to parse LLM response, using heuristic: {e}")

    user_description = description or ""
    resolved_tags = _heuristic_tags(content, user_description, tags)
    resolved_title = _heuristic_title(content, user_description)
    resolved_description = _heuristic_description(content, user_description)
    resolved_category = _heuristic_category(content, user_description, resolved_tags)
    resolved_category_description = _heuristic_category_description(resolved_category, resolved_tags)
    return {
        "title": resolved_title,
        "category": resolved_category,
        "category_description": resolved_category_description,
        "description": resolved_description,
        "tags": resolved_tags,
        "is_link": content_is_link,
    }


async def fetch_suggestions(content: str, description: str | None = None, tags: list[str] | None = None) -> dict:
    """Standalone suggestion tool (vata_suggest) — same decision, exposed
    directly without saving anything."""
    return await decide_asset_metadata(content, description, tags)
