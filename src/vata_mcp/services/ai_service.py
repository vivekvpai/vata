"""Metadata decision layer: category assignment + title/description/tag
generation for saved assets.

The intended caller is the LLM already driving the MCP session (Claude,
ChatGPT, etc.) — it reasons about the content itself and passes explicit
title/category/description/tags into vata_save. This module's job is then
just to fill in whatever the caller left blank, so nothing is ever
required to be empty. Fill-in order:

  1. Explicit value passed by the caller — used as-is, no computation.
  2. VATA_LLM_MODEL, if configured — the server makes its own LLM call.
     Only useful for callers that can't reason themselves (scripts, cron).
  3. Local keyword-overlap heuristic — always available, zero cost,
     zero API key, works with nothing configured.

Content saved via vata_save is usually a link, sometimes plain text.
"""

import json
import re
from collections import Counter
from urllib.parse import urlparse

from .. import config
from . import storage

_LLM_MODEL = config.get("VATA_LLM_MODEL")
_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "for",
    "is", "are", "was", "were", "be", "been", "this", "that", "with", "as",
    "it", "its", "at", "by", "from", "i", "we", "you", "my", "our",
}
_WORD_RE = re.compile(r"[A-Za-z0-9']+")
_URL_RE = re.compile(r"^https?://", re.IGNORECASE)
_URL_NOISE_WORDS = {"http", "https", "www", "com", "org", "net", "io", "co"}


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
    words = [
        w.lower() for w in _WORD_RE.findall(text)
        if w.lower() not in _STOPWORDS and w.lower() not in _URL_NOISE_WORDS and len(w) > 2
    ]
    counts = Counter(words)
    return [w for w, _ in counts.most_common(top_n)]


def _truncate_words(text: str, max_chars: int) -> str:
    """Truncate at a word boundary (never mid-word) and add an ellipsis only
    when something was actually cut."""
    text = " ".join(text.split())
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars].rsplit(" ", 1)[0]
    return (cut or text[:max_chars]) + "..."


def _heuristic_tags(content: str, user_description: str, existing_tags: list[str] | None) -> list[str]:
    if existing_tags:
        return existing_tags
    return _keywords(f"{content} {user_description}", top_n=5)


def _heuristic_title(content: str, user_description: str) -> str:
    """A short, standalone label — distinct from the description, never a
    duplicate of the raw hint or the full URL."""
    if user_description:
        title = _truncate_words(user_description, 60)
        return title[0].upper() + title[1:] if title else title

    if is_link(content):
        parsed = urlparse(content.strip())
        path_hint = parsed.path.strip("/").split("/")[-1].replace("-", " ").replace("_", " ")
        if path_hint:
            return _truncate_words(f"{parsed.netloc} — {path_hint}", 80)
        return parsed.netloc or _truncate_words(content, 60)

    return _truncate_words(content, 60)


def _heuristic_description(content: str, user_description: str) -> str:
    """A fuller one-liner distinct from the title. Never quotes the user's
    hint verbatim — synthesizes a new sentence from keywords extracted out
    of the content + hint together, so the stored description is always
    Vata's own wording, not a copy-paste of what was given."""
    keywords = _keywords(f"{content} {user_description}", top_n=6)
    topic = ", ".join(keywords[:4]) if keywords else "this item"

    if is_link(content):
        link = content.strip()
        return _truncate_words(f"A saved link about {topic}. ({link})", 200)
    return _truncate_words(f"A note about {topic}.", 200)


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


def list_existing_categories() -> list[dict]:
    """Categories with enough context (name + description + a few asset
    titles/tags) for a calling LLM to judge fit without a second round trip."""
    result = []
    for cat in storage.list_categories():
        sample = storage.list_assets_in_category(cat["_id"])[:5]
        result.append({
            "category": cat["category"],
            "category_id": cat["_id"],
            "description": cat.get("description", ""),
            "sample_titles": [a.get("title", "") for a in sample],
            "sample_tags": sorted({t for a in sample for t in a.get("tags", [])})[:10],
        })
    return result


async def decide_asset_metadata(
    content: str,
    description: str | None = None,
    tags: list[str] | None = None,
    title: str | None = None,
    category: str | None = None,
    category_description: str | None = None,
) -> dict:
    """Fills in only whatever the caller left blank. Returns {"title",
    "category", "category_description", "description", "tags", "is_link"}.

    Preferred usage: the calling LLM already reasoned about the content —
    it calls vata_list_categories itself, decides fit-or-new, and passes
    title/category/description/tags explicitly. In that case this function
    does nothing but pass them through untouched.

    Any field left None falls back to VATA_LLM_MODEL (if configured) or the
    local heuristic — for callers that can't reason for themselves (direct
    script/API use).
    """
    content_is_link = is_link(content)

    # Caller supplied everything — no computation needed at all.
    if title and category and description and tags:
        return {
            "title": title,
            "category": category,
            "category_description": category_description or "",
            "description": description,
            "tags": tags,
            "is_link": content_is_link,
        }

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
                resolved_tags = tags or list(parsed.get("tags") or _heuristic_tags(content, description or "", None))
                resolved_category = category or str(parsed.get("category") or "General")
                return {
                    "title": title or str(parsed.get("title") or _heuristic_title(content, description or "")),
                    "category": resolved_category,
                    "category_description": category_description or str(
                        parsed.get("category_description")
                        or _heuristic_category_description(resolved_category, resolved_tags)
                    ),
                    "description": description or str(parsed.get("description") or _heuristic_description(content, description or "")),
                    "tags": resolved_tags,
                    "is_link": content_is_link,
                }
            except Exception as e:
                print(f"[vata-mcp] ai_service: failed to parse LLM response, using heuristic: {e}")

    user_description = description or ""
    resolved_tags = tags or _heuristic_tags(content, user_description, None)
    resolved_title = title or _heuristic_title(content, user_description)
    resolved_description = description or _heuristic_description(content, user_description)
    resolved_category = category or _heuristic_category(content, user_description, resolved_tags)
    resolved_category_description = category_description or _heuristic_category_description(resolved_category, resolved_tags)
    return {
        "title": resolved_title,
        "category": resolved_category,
        "category_description": resolved_category_description,
        "description": resolved_description,
        "tags": resolved_tags,
        "is_link": content_is_link,
    }


async def fetch_suggestions(
    content: str,
    description: str | None = None,
    tags: list[str] | None = None,
    title: str | None = None,
    category: str | None = None,
) -> dict:
    """Standalone suggestion tool (vata_suggest) — same decision, exposed
    directly without saving anything."""
    return await decide_asset_metadata(content, description, tags, title, category)
