# Vata MCP — Backend Schema

Companion to [VATA_MCP_PLAN.md](VATA_MCP_PLAN.md). MongoDB collections,
MCP tool I/O contracts, validation rules — matches `src/vata_mcp/` as of
the current `mcp` branch. One category per asset (no many-to-many join);
metadata (`title`/`category`/`description`/`tags`) is normally supplied by
the calling LLM, not generated server-side — see plan §2.

---

## 1. MongoDB collections

Two collections only. No `category_members` join (removed — assets carry
`category_id` directly).

### 1.1 `categories`

```jsonc
{
  "_id": "string",            // category_id, e.g. "web_frameworks_20260719170220"
                               // slug(name) + "_" + UTC timestamp, from storage.new_category_id
  "category": "string",       // human-readable name
  "description": "string",    // one-sentence description, may be ""
  "created_at": "ISO-8601 string",
  "updated_at": "ISO-8601 string"  // bumped on rename, description edit, or any asset add/edit/delete inside it
}
```

Indexes: `_id` (default), `category` (non-unique, for exact-name lookup
via `find_category_by_name`).

### 1.2 `assets`

```jsonc
{
  "_id": "string",             // ULID, from storage.new_asset_id
  "category_id": "string",     // FK -> categories._id. Every asset has exactly one.
  "title": "string",           // may be "" but insert_asset always writes something
  "content": "string",         // the raw link or text saved — required
  "description": "string",     // one-sentence description, may be ""
  "tags": ["string", ...],     // lowercased, deduplicated, sorted on every write
  "created_at": "ISO-8601 string",
  "updated_at": "ISO-8601 string"
}
```

Indexes: `_id` (default), `category_id` (list-by-category lookups),
`title` (case-insensitive regex lookup via `find_asset_by_title`).

No `index.json` or other derived cache — Mongo collections are the source
of truth; BM25 scoring in `decision_service.py` reads asset documents
directly at query time.

---

## 2. MCP tool contracts

TypeScript-style signatures for brevity; actual server uses FastMCP +
Pydantic `Field` annotations (see `src/vata_mcp/server.py` for exact
`Annotated[...]` types and per-field descriptions shown to the calling
model).

### `vata_save`
```ts
input: {
  content: string;                    // required — link or freeform text
  title?: string;                     // caller should supply; else falls back
  category?: string;                  // caller should supply; else falls back
  category_description?: string;      // only meaningful if category is new
  description?: string;               // caller should supply; else falls back
  tags?: string[];                    // caller should supply; else falls back
}
output: {
  message: string; asset_id: string; title: string; category_id: string;
  category: string; description: string; tags: string[]; is_link: boolean;
}
```
Delegates to `ai_service.decide_asset_metadata(...)` to fill any blank
field (order: caller value → `VATA_LLM_MODEL` → local heuristic — see
plan §2), then `category_service.resolve_or_create_category` +
`add_asset_to_category_record`. If all four of title/category/description/
tags are supplied, `decide_asset_metadata` short-circuits and returns them
untouched — no Mongo read of existing categories, no LLM call.

### `vata_list_categories`
```ts
input: {}
output: { count: number; categories: Array<{
  category_id: string; category: string; description: string; asset_count: number;
}> }
```

### `vata_list_assets`
```ts
input: { category_id?: string; category_name?: string }  // at least one required
output: { category: string; category_id: string; count: number; assets: Array<{
  asset_id: string; title: string; content: string; description: string; tags: string[];
}> }
```
Raises not-found (returned as `{error, error_type}`, not a thrown
exception across the MCP boundary) if neither resolves to an existing
category.

### `vata_find`
```ts
input: { query: string }
output: {
  message: string; count: number;
  assets: Array<{
    asset_id: string; category: string; category_id: string; title: string;
    description: string; tags: string[]; content: string; match_reason: string;
  }>;
  categories: Array<{ category_id: string; category: string; description: string; match_count: number; }>;
}
```
Two-pass BM25 (categories, then assets within top categories), with an
optional LLM re-rank pass on each stage if `VATA_LLM_MODEL` is set —
falls back to "keyword match" as the reason when no LLM is configured.
Returns matched **categories** alongside matched **assets** (added after
the original 3-verb design — was missing from the first version of this
doc).

### `vata_stats`
```ts
input: {}
output: { categories: number; assets: number; version: string }
```

### `vata_describe`
```ts
input: {}
output: {
  name: string; description: string; version: string;
  tools: string[]; prompts: string[];
  storage_backend: { backend: string; database: string; persistent: boolean };
  ai_backend: { backend: string; llm_configured: boolean };
  auth_enabled: boolean;
}
```
`tools`/`prompts` are introspected live from the running `FastMCP`
instance (`mcp.list_tools()`/`mcp.list_prompts()`), so this never drifts
from what's actually registered.

### `vata_suggest`
```ts
input: { content: string; description?: string; tags?: string[]; title?: string; category?: string }
output: { title: string; category: string; category_description: string; description: string; tags: string[]; is_link: boolean }
```
Same `decide_asset_metadata` call as `vata_save`, but never writes
anything. Intended for previewing/debugging the *fallback* path — not
part of the normal caller-decides flow.

### `vata_edit_category`
```ts
input: { category_id?: string; current_name?: string; new_name?: string; description?: string }
// at least one of category_id/current_name to locate it, at least one of new_name/description to change
output: { message: string; category_id: string; category: string; description: string }
```
Renaming assigns a new `category_id` (name+timestamp derived) and moves
every asset in the category to it — this is a real document rewrite in
`categories`, not a soft alias.

### `vata_edit_asset`
```ts
input: {
  asset_id?: string; current_title?: string;      // at least one to locate the asset
  new_content?: string;                            // if given, triggers a full metadata refresh
  new_title?: string; new_description?: string; new_tags?: string[];  // caller should supply when new_content given
  hint?: string;                                   // fallback-only steering, ignored if new_description given
}
output: { asset_id: string; title: string; content: string; description: string; tags: string[]; category_id: string; created_at: string; updated_at: string }
```
If `new_content` is omitted, this is currently a no-op (no other fields
are editable independently of content in the present implementation —
flagged as a possible gap, not a documented feature: there's no path to
edit *only* the title without also touching content).

### `vata_delete_category`
```ts
input: { confirm: true; category_id?: string; category_name?: string }
output: { message: string; category_id: string; deleted_asset_ids: string[]; deleted_asset_count: number }
```
`confirm` is a required positional-first parameter typed as the literal
`true` — omitting it or passing `false` fails MCP-level schema validation
before the tool body ever runs.

### `vata_delete_asset`
```ts
input: { confirm: true; asset_id?: string; title?: string }
output: { message: string; asset_id: string; title: string }
```

### `vata_clean`
```ts
input: { password: string }
output:
  | { message: "All categories and assets deleted"; deleted_categories: number; deleted_assets: number }
  | { error: string; error_type: "RuntimeError" }    // VATA_CLEAN_PASSWORD unset on server
  | { error: string; error_type: "PermissionError" } // password mismatch — uses hmac.compare_digest, timing-safe
```
Deletes all documents in both collections via `delete_many({})` — does
**not** attempt `dropDatabase`, since some Mongo roles (e.g. scoped Atlas
users) aren't granted that privilege; `delete_many` works under any
read/write role.

### `vata_replace_category`
```ts
input: { category_id: string; data: Record<string, { title?: string; content: string; description?: string; tags?: string[] }> }
output: { message: string; category_id: string; data: Record<string, AssetDoc> }
```
Deletes every existing asset in the category first, then inserts new ones
from `data`. Rarely used; kept for bulk-import parity.

---

## 3. Validation rules

- `content`: required, non-empty. No app-level max length; Mongo's 16MB
  document cap is the real ceiling.
- `tags`: lowercased and deduplicated on every write (`storage.insert_asset`
  / `storage.update_asset`), regardless of whether they came from the
  caller or a fallback.
- Not-found lookups (`asset_id`/`title`/`category_id`/`category_name` that
  don't resolve) raise `VataNotFoundError` inside the service layer, which
  every tool wrapper catches and converts to `{error, error_type}` — never
  a raw exception surfacing across the MCP boundary.
- Destructive tools (`vata_delete_category`, `vata_delete_asset`) require
  `confirm: true` as a literal-typed field, machine-checkable at the
  schema level, not just documented in the tool description.
- `vata_clean` uses `hmac.compare_digest` for the password check
  specifically to avoid timing side-channels — same pattern as the bearer
  token check in `auth.py`.

---

## 4. Auth & multi-tenancy

Single-user per deployment — confirmed design, not a placeholder. No
`owner`/`user_id` field on any document. `VATA_MCP_TOKEN` is one shared
secret for the whole deployment's HTTP transport; there is no per-user
identity anywhere in the schema. If multi-tenant support is ever wanted,
every collection needs a `user_id` field and every tool call needs an
identity resolved from the token — not currently planned (see
[VATA_DISTRIBUTION_PLAN.md §7](VATA_DISTRIBUTION_PLAN.md) — the packaging
plan explicitly keeps "one person, one deployment, one DB" as the model
rather than building shared infrastructure).
