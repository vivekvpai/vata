# Vata MCP — Backend Schema

Companion to [`VATA_MCP_PLAN.md`](VATA_MCP_PLAN.md). Defines the MongoDB
collections, the MCP tool I/O contracts, and validation rules. Categories
are AI-managed (see plan §"Decision") — no schema field here is ever
populated by direct user input; `category_id` is always written by the
server after an AI decision.

---

## 1. MongoDB collections

### 1.1 `assets`

One document per saved piece of content. Content-addressable by `_id`
(ULID, matches the existing `python-ulid` usage in `storage.new_asset_id`).

```jsonc
{
  "_id": "01J...ULID",              // string, ULID, primary key
  "main_content": "string",          // required, the raw saved text
  "summary": "string",               // AI- or user-provided, may be ""
  "tags": ["string", ...],           // AI- or user-provided, may be []
  "created_at": "ISO-8601 string",   // UTC, set once
  "updated_at": "ISO-8601 string"    // UTC, bumped on every edit
}
```

Indexes:
- `_id` — default primary key
- Text index on `main_content`, `summary`, `tags` — for future `$text`
  pre-filtering (phase 1 still scores BM25 in Python; index is prepared,
  not yet queried that way)

### 1.2 `categories`

AI-owned. Created automatically the first time the AI decides no existing
category fits.

```jsonc
{
  "_id": "string",                   // category_id, e.g. "notes_20260718142233"
  "category": "string",              // human-readable name, AI-generated
  "created_at": "ISO-8601 string",
  "updated_at": "ISO-8601 string"    // bumped whenever membership changes
}
```

Indexes:
- `_id` — default primary key
- Index on `category` (non-unique) — for AI category-matching lookups by name

### 1.3 `category_members`

Many-to-many join between `assets` and `categories`. Replaces the old
`members.json` file per category.

```jsonc
{
  "_id": "ObjectId",                 // auto
  "category_id": "string",           // FK -> categories._id
  "asset_id": "string"               // FK -> assets._id
}
```

Indexes:
- Compound unique index on `(category_id, asset_id)` — prevents duplicate
  links, makes unlink/delete idempotent
- Index on `asset_id` alone — needed for "which categories is this asset
  in" lookups (used by delete/unlink to detect orphaning)

No separate `index.json` cache — Mongo collections + indexes are the index.

---

## 2. Derived/computed shapes (not stored, returned by tools)

### 2.1 Category summary entry (from `vata_get` with no `asset_id`)

```jsonc
{
  "asset_id": "string",
  "summary": "string",
  "tags": ["string"],
  "content_snippet": "string",       // main_content truncated to 200 chars
  "updated_at": "ISO-8601 string",
  "categories": ["category_id", ...] // all categories this asset belongs to
}
```

### 2.2 Search/find result entry (from `vata_find`)

```jsonc
{
  "asset_id": "string",
  "category": "string",              // human name
  "category_id": "string",
  "summary": "string",
  "tags": ["string"],
  "match_reason": "string",          // LLM-generated justification
  "content_snippet": "string"
}
```

---

## 3. MCP tool contracts

Each tool is a JSON-Schema-validated function. Types below use TypeScript
notation for brevity; the actual server registers these as Pydantic models
(consistent with the existing FastAPI request models in `main.py`).

### `vata_save`
```ts
input:  { content: string; summary?: string; tags?: string[] }
output: { asset_id: string; category_id: string; category: string; message: string }
```
Never accepts a `category` field — see plan decision. Internally: calls
`fetch_ai_suggestions(content, summary, tags)` → gets back a suggested
category name (existing or new) + summary/tags fallback → resolves to a
`category_id` (create if it doesn't exist) → `add_asset_to_category_record`.

### `vata_get`
```ts
input:  { asset_id?: string; category_id?: string }
output:
  | { categories: string[] }                                    // no args
  | { category_id: string; count: number; items: SummaryEntry[] } // category_id only
  | { asset_id: string; main_content: string; summary: string;
      tags: string[]; categories: string[]; created_at: string;
      updated_at: string }                                       // asset_id given
```
Note: since categories are AI-named and not user-facing vocabulary, the
"no args" case is mostly a debug/admin path — normal usage is
`vata_find` for retrieval by meaning, not by browsing category names.

### `vata_find`
```ts
input:  { query: string }
output: { message: string; count: number; data: FindResultEntry[] }
```

### `vata_suggest`
```ts
input:  { content: string; summary?: string; tags?: string[] }
output: { category: string; summary: string; tags: string[] }
```
Used internally by `vata_save`; not usually invoked directly, but exposed
as a standalone tool for transparency/debugging ("what would this be filed
under?").

### `vata_edit_asset`
```ts
input:  { asset_id: string; category_id: string; fields: {
            main_content?: string; summary?: string; tags?: string[] } }
output: { message: string; category_id: string; asset_id: string }
```

### `vata_delete_asset`
```ts
input:  { category_id: string; asset_id: string; confirm: true }
output: { message: string; category_id: string; asset_id: string;
           hard_deleted: boolean }
```
`confirm: true` is required in the schema (literal type, not just a
boolean default) so the model cannot call this without an explicit
affirmative — see plan §6 open decision, resolved here as: yes, require it.

### `vata_delete_category`
```ts
input:  { category_id: string; confirm: true }
output: { message: string; category_id: string; orphaned_assets_deleted: string[] }
```

### `vata_rename_category`
```ts
input:  { category_id: string; new_name: string }
output: { message: string; old_id: string; new_id: string }
```
AI-only in practice (user never sees `category_id` to pass it), but kept as
a tool for admin/debug use and for the AI itself to consolidate/rename
categories over time (e.g. merging near-duplicate auto-created ones).

### `vata_link_asset` / `vata_unlink_asset`
```ts
input:  { category_id: string; asset_id: string }
output: { message: string; category_id: string; asset_id: string;
           categories: string[]; deleted?: boolean }  // deleted only on unlink
```

### `vata_replace_category`
```ts
input:  { category_id: string; data: Record<string, {
            main_content: string; summary?: string; tags?: string[] }> }
output: { message: string; category_id: string; content: {...} }
```
Rarely used directly; kept for parity with the existing REST bulk-replace
endpoint and potential future bulk-import flows.

---

## 4. Validation rules

- `content` / `main_content`: required, non-empty, no max length enforced
  at the schema level (Mongo doc size cap of 16MB is the real ceiling).
- `tags`: deduplicated on write, lowercased for consistency (matches
  existing tag handling implied by `ai_service` prompt design).
- `asset_id`, `category_id`: must reference existing documents — tools
  return a structured "not found" error (mirrors current `HTTPException`
  404s in `category_service.py`) rather than throwing raw exceptions to the
  MCP client.
- Destructive tools (`vata_delete_asset`, `vata_delete_category`) require
  `confirm: true` in the input schema itself, not just in prose — this
  makes the confirmation machine-checkable, not dependent on the calling
  model reading instructions correctly.

---

## 5. Auth & multi-tenancy note

Single-user for now (per plan). No `owner`/`user_id` field on any
collection. If this ever needs to support more than one person, every
collection would need a `user_id` field and every tool call would need to
carry an identity resolved from the bearer token — noted here so the
schema doesn't silently assume it "just works" for multi-user later.
