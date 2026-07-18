# Vata MCP Server — Build Plan

Goal: turn Vata into a hosted MCP server usable from any MCP-capable chat
client (Claude Desktop, Claude Code, Gemini CLI). Single user. Free-tier
hosting. MongoDB Atlas as the database.

Primary UX is three slash prompts — `vata-save`, `vata-get`, `vata-find` —
but the underlying tool surface covers the **full CRUD set Vata already
supports** today via REST (create/edit/delete/rename/link/unlink, not just
save/get/find). See §1 for the full inventory and §3 for the tool list.

**Decision: categories are AI-managed, not user-managed.** The user never
names, picks, or creates a category. `vata_save` takes just `content` (+
optional `summary`/`tags` override); the server calls the AI internally
(`ai_service` + `decision_service`) to decide which existing category the
content belongs in, or to create a new one, before writing to Mongo.
Categories still exist in the data model (they're how `vata_find` narrows
search — see §4), they're just invisible to the user. See companion docs:
[`VATA_SCHEMA.md`](VATA_SCHEMA.md) for the full DB/tool schema and
[`VATA_DATAFLOW.md`](VATA_DATAFLOW.md) for sequence diagrams of each flow.

---

## 1. Current state (what already exists)

- `src/vata/services/storage.py` — flat-file JSON storage under
  `~/.vata/data` (`assets/`, `categories/`, `index.json`). This is the piece
  being replaced.
- `src/vata/services/category_service.py` — CRUD + many-to-many
  category↔asset membership. Logic stays, only its calls into `storage.py`
  change.
- `src/vata/services/decision_service.py` — two-pass search: BM25 pre-filter
  over categories, then BM25 pre-filter over assets within relevant
  categories, then an LLM re-rank/justify pass on each. This becomes the
  engine behind `vata-find`.
- `src/vata/services/ai_service.py` — LLM-based suggestion generation for a
  new asset (tags/summary). Reusable inside `vata-save`.
- `src/vata/main.py` — FastAPI REST app exposing all of the above. Keeps
  working after this change; MCP is an additional interface, not a
  replacement.

### Full operation inventory (everything the REST API exposes today)

Every one of these needs an MCP tool — the "3 verbs" are the slash-prompt
front door, not the full tool surface.

| # | Operation | REST route | Service function |
|---|---|---|---|
| 1 | Create category | `POST /categories` | `create_category_record` |
| 2 | List categories | `GET /categories` | `list_categories_record` |
| 3 | Get category (full content) | `GET /categories/{c}` | `get_category_record` |
| 4 | Get category summary (fast, index-backed) | `GET /categories/{c}/summary` | `get_category_summary` |
| 5 | Bulk-replace category contents | `PUT /categories/{c}` | `update_category_record` |
| 6 | Delete category | `DELETE /categories/{c}` | `delete_category_record` |
| 7 | Rename category | `PATCH /categories/{c}/rename` | `rename_category_record` |
| 8 | Add asset to category | `POST /categories/{c}/assets` | `add_asset_to_category_record` |
| 9 | Update/edit asset | `PUT /categories/{c}/assets/{a}` | `update_asset_in_record` |
| 10 | Delete asset (unlink; hard-delete if orphaned) | `DELETE /categories/{c}/assets/{a}` | `delete_asset_from_record` |
| 11 | Link existing asset to another category | `POST /categories/{c}/assets/{a}/link` | `link_asset_to_category` |
| 12 | Unlink asset from a category | `DELETE /categories/{c}/assets/{a}/link` | `unlink_asset_from_category` |
| 13 | AI tag/summary suggestions for new content | `POST /suggestions` | `fetch_ai_suggestions` |
| 14 | Search / decision query (BM25 + LLM re-rank) | `POST /query` | `evaluate_nodes_for_query` |

---

## 2. Target architecture

```
Chat client (Claude Desktop / Claude Code / Gemini CLI)
        │  MCP over Streamable HTTP  (Authorization: Bearer <token>)
        ▼
vata-mcp server  (hosted on Render, free web service)
   ├─ MCP layer: 11 tools + 3 slash prompts
   │     tools:   vata_save / vata_get / vata_find / vata_suggest /
   │              vata_edit_asset / vata_delete_asset / vata_delete_category /
   │              vata_rename_category / vata_link_asset / vata_unlink_asset /
   │              vata_replace_category
   │     prompts: "vata-save" / "vata-get" / "vata-find"  (edit/delete reachable
   │              via natural language → tool call, see §3b)
   ├─ service layer: category_service.py, decision_service.py, ai_service.py
   │     (kept, adapted to async Mongo calls)
   └─ storage.py  →  rewritten against MongoDB instead of local JSON files
                       │
                       ▼
              MongoDB Atlas free tier (M0, 512MB, free forever)
              collections: assets, categories, category_members
```

Why prompts *and* tools: a typed slash command in an MCP client (e.g.
`/mcp__vata__vata-save`) is rendered from an MCP **prompt**, not a tool.
Tools are what the model calls once it decides to act. So each verb needs:

- a **prompt** (`vata-save`, `vata-get`, `vata-find`) — the thing the user
  types/invokes, which expands into an instruction telling the model which
  tool to call and how.
- a **tool** (`vata_save`, `vata_get`, `vata_find`) — the actual function
  the server executes.

Exact slash-command rendering is client-dependent (Claude Code namespaces
it under the server name, Claude Desktop shows prompts in an attachment
picker), but the underlying tool call is identical everywhere.

---

## 3. Tool → service mapping

The MCP server exposes one tool per existing operation. Three of them are
promoted to top-level slash prompts (§3b); the rest are still fully callable
by the model mid-conversation ("delete that asset", "rename this category",
"link this to Work too") — an MCP client doesn't require a slash prompt to
invoke a tool, prompts are just a convenience shortcut for the common path.

| Tool | Args | Backed by (existing code) | Behavior |
|---|---|---|---|
| `vata_save` | `content`, `summary?`, `tags?` | `ai_service.fetch_ai_suggestions` (decides category + fills summary/tags) → `create_category_record` (if AI picked a new category) → `add_asset_to_category_record` | **No `category` arg** — AI decides which existing category fits, or creates one, then stores the asset. Returns `asset_id` (+ the category it landed in, for transparency, but never asks the user for one) |
| `vata_get` | `category?`, `asset_id?` | `list_categories_record` / `get_category_summary` / `get_category_record` | No args → list categories. `category` only → summary of its items. `asset_id` → full asset content |
| `vata_find` | `query` | `evaluate_nodes_for_query` | BM25 pre-filter + LLM re-rank across categories and assets, returns ranked matches with match reasons |
| `vata_edit_asset` | `asset_id`, `category_id`, `fields` | `update_asset_in_record` | Patches an existing asset's content/summary/tags |
| `vata_delete_asset` | `category_id`, `asset_id` | `delete_asset_from_record` | Unlinks asset from category; hard-deletes it if it's now in zero categories |
| `vata_delete_category` | `category_id` | `delete_category_record` | Deletes the category; orphaned assets (no other category) are hard-deleted too |
| `vata_rename_category` | `category_id`, `new_name` | `rename_category_record` | Renames a category (note: this changes its `category_id`, since IDs are name+timestamp derived) |
| `vata_link_asset` | `category_id`, `asset_id` | `link_asset_to_category` | Attaches an existing asset to an additional category (many-to-many) |
| `vata_unlink_asset` | `category_id`, `asset_id` | `unlink_asset_from_category` | Detaches an asset from one category without deleting it, unless that was its last category |
| `vata_replace_category` | `category_id`, `data` | `update_category_record` | Bulk-replace: unlinks all current members, creates new assets from `data` |
| `vata_suggest` | `content`, `summary?`, `tags?` | `fetch_ai_suggestions` | Returns AI-suggested category/summary/tags without saving anything — useful before `vata_save` |

### 3b. Slash prompts (typed entry points)

Only the three most common actions get a dedicated prompt; everything else
stays tool-only and is reached by the model deciding to call it from natural
language.

| Prompt | Expands to a call to |
|---|---|
| `/vata-save` | `vata_save` (optionally preceded by `vata_suggest` if summary/tags omitted) |
| `/vata-get` | `vata_get` |
| `/vata-find` | `vata_find` |

Open question: worth adding `/vata-edit` and `/vata-delete` as explicit
prompts too, since edit/delete are destructive and benefit from being an
intentional, typed action rather than something the model infers from
phrasing. Leaning yes — see §6.

---

## 4. MongoDB data model (replaces `~/.vata/data`)

- **`categories`**: `{ _id: category_id, category: name, created_at, updated_at }`
- **`assets`**: `{ _id: asset_id, main_content, summary, tags: [...], created_at, updated_at }`
- **`category_members`**: `{ category_id, asset_id }` — many-to-many join,
  indexed on both fields
- Drop the hand-rolled `index.json` cache — Mongo itself is the index. Add a
  text index on `assets.summary` / `assets.tags` / `assets.main_content` for
  future search optimization. Phase 1 keeps BM25 scoring in Python exactly
  as today (fetch candidate docs, score in-process); offloading pre-filtering
  to Mongo `$text` search is a later optimization, not required up front.

---

## 5. Build phases

### Phase 1 — Swap the storage backend
Rewrite `storage.py` against `pymongo` (or `motor` for async), keeping the
same function names/shapes (`read_json` → `get_asset`, etc.) so
`category_service.py` and `decision_service.py` need minimal edits. Verify
against the existing REST API + current frontend before touching MCP at
all — this is the riskiest step and should be validated in isolation.

### Phase 2 — Add the MCP server
New module, e.g. `src/vata/mcp_server.py`, using the official `mcp` Python
SDK's `FastMCP`. Register the 3 tools + 3 prompts, calling straight into the
same service functions used by the REST API. Can run as its own ASGI app —
either mounted alongside the FastAPI app or deployed as a separate Render
service (separate is simpler to reason about and restart independently).

### Phase 3 — Auth
Server is publicly reachable even though it's single-user, so add a static
bearer token (`VATA_MCP_TOKEN` env var) checked in middleware before any
tool/prompt executes. Not full multi-user auth — just a lock on the door.

### Phase 4 — Deploy
Render free web service. Env vars: `MONGODB_URI`, `VATA_MCP_TOKEN`, and
whatever LLM credentials `ai_service`/`decision_service` require. Free tier
sleeps when idle, so the first call after inactivity has cold-start latency
— acceptable for personal use.

### Phase 5 — Wire up clients
Add the deployed URL as a remote MCP server in Claude Desktop/Code config
with the bearer header set. Same connection works for Gemini CLI, since it
also speaks MCP natively.

### Phase 6 — Optional later: ChatGPT / Gemini-web support
ChatGPT and Gemini's web app don't speak MCP. The existing FastAPI routes in
`main.py` already provide a REST surface; if needed later, wrap that in an
OpenAPI-based GPT Action or a Gemini extension without touching the MCP
server or the Mongo layer at all.

---

## 6. Open decisions to revisit before/while building

- Same repo/process for MCP server vs. separate deployable — leaning
  separate Render service for independent restarts/logs.
- ~~Whether `vata_save` should call `ai_service` automatically~~ — **decided:
  yes**, category assignment is fully AI-driven, never user-supplied.
- Async migration: `motor` (async Mongo driver) vs. keeping `pymongo`
  sync calls inside FastAPI's threadpool — affects how much of
  `category_service.py`/`decision_service.py` needs `async def` changes.
- Whether `vata_delete_asset` / `vata_delete_category` should require a
  confirmation round-trip (e.g. tool returns a preview + requires a repeat
  call with `confirm: true`) since they're destructive and irreversible
  once Mongo writes land — MCP itself has no built-in "are you sure" step,
  so this has to be handled in the tool's own contract.
- Whether `/vata-edit` and `/vata-delete` should be added as explicit slash
  prompts (currently tool-only, reached via natural language) — makes
  destructive actions a deliberate typed command instead of inferred intent.
