# Vata MCP Server — Plan

Status: **implemented and deployed** (branch `mcp`, live on Render + MongoDB
Atlas). This doc is the up-to-date reference for the current design — kept
so the next round of changes has an accurate starting point instead of
re-deriving intent from the diff. Companion docs:
[VATA_SCHEMA.md](VATA_SCHEMA.md) (DB + tool I/O contracts),
[VATA_DATAFLOW.md](VATA_DATAFLOW.md) (sequence diagrams),
[VATA_DISTRIBUTION_PLAN.md](VATA_DISTRIBUTION_PLAN.md) (packaging for other
users — not yet built).

---

## 1. What Vata is

A personal link/notes archive exposed as an MCP server: `vata_save` files
a link or note away, `vata_find` retrieves by meaning, plus browsing/edit/
delete/admin tools. Single user per deployment — everyone who runs this
gets their own database, there is no shared multi-tenant service.

## 2. Core design decision: the calling LLM does the thinking

**This changed once already and is the current, correct model — don't
regress to the earlier version.**

Earlier iteration (superseded): `vata_save` took only `content` +
optional `summary`/`tags`, and decided the category itself — either via a
local heuristic or, if `VATA_LLM_MODEL` was set, its own separate LLM API
call. The chat model driving the MCP session was never involved in that
decision; it just called a black-box tool.

Current model: `vata_save` accepts explicit `title`, `category`,
`category_description`, `description`, `tags`. The `/vata-save` prompt
instructs the calling assistant (Claude, etc.) to:

1. Call `vata_list_categories` to see what already exists.
2. Decide itself: reuse a fitting category, or invent a short new one.
3. Write its own title, one-sentence description, and up to 5 tags.
4. Call `vata_save` passing all of that explicitly.

The server stores whatever it's given **verbatim** — no computation, no
second LLM call. Fields left blank still get filled (in order: caller
value → `VATA_LLM_MODEL` if configured → local keyword-overlap heuristic),
which matters only for non-reasoning callers (a bare script hitting the
tool directly). Normal chat use needs no API key at all — the model
already in the conversation does the categorization as ordinary tool use.

`ai_service.decide_asset_metadata()` is the single function implementing
this fill-in-the-gaps logic; see its docstring for the exact precedence
order.

## 3. Data model: one category per asset

**This also changed from the original many-to-many design — don't
reintroduce a join collection.**

Each asset belongs to exactly one category (`category_id` field directly
on the asset document). No `category_members` join table, no
`vata_link_asset`/`vata_unlink_asset`. Deleting a category cascades:
every asset inside it is deleted too — this is intentional, not a bug,
because there's no other category for an orphaned asset to remain in.

Renaming a category changes its `category_id` (IDs are `slug_timestamp`
derived from the name) — assets move to the new id automatically as part
of the rename.

Assets are addressable by `asset_id` or by exact `title` (case-insensitive
match) throughout the tool surface — see `category_service.resolve_asset`.
Categories are addressable by `category_id` or exact name — see
`resolve_category`.

## 4. Tool surface (13 tools, 7 prompts)

| Tool | Prompt | Purpose |
|---|---|---|
| `vata_save` | `/vata-save` | Save a link/note. Caller decides title/category/description/tags |
| `vata_list_categories` | `/vata-list-categories` | Table: category, description, asset count |
| `vata_list_assets` | `/vata-list-assets` | Table for one category: title, content, description, tags |
| `vata_find` | `/vata-find` | BM25 search (+ optional LLM re-rank); returns matching assets AND matched categories |
| `vata_stats` | `/vata-stats` | Category count, asset count, version |
| `vata_describe` | `/vata-describe` | Self-introspection: name, tools, prompts, storage/AI/auth backend status |
| `vata_clean` | `/vata-clean` | Wipes everything. Password-gated via `VATA_CLEAN_PASSWORD` |
| `vata_edit_category` | — | Rename and/or edit description |
| `vata_edit_asset` | — | Edit content/title/description/tags; caller decides new values |
| `vata_delete_category` | — | Deletes category + all assets inside. `confirm: true` required |
| `vata_delete_asset` | — | Deletes one asset. `confirm: true` required |
| `vata_suggest` | — | Preview what the *fallback* (LLM/heuristic) would decide — debug tool for that path specifically, not for normal use |
| `vata_replace_category` | — | Bulk-replace all assets in a category |

Full I/O contracts: [VATA_SCHEMA.md §3](VATA_SCHEMA.md#3-mcp-tool-contracts).

Destructive tools (`vata_delete_category`, `vata_delete_asset`) require a
literal `confirm: true` in the schema itself — not just prose — so the
calling model can't skip confirmation by misreading instructions.
`vata_clean` additionally requires a password matching `VATA_CLEAN_PASSWORD`
on the server; if that env var isn't set, the tool refuses to run at all.

## 5. Architecture

```
Chat client (Claude Desktop / Claude Code / any MCP client)
        │  MCP over stdio (local) or Streamable HTTP + Bearer token (remote)
        ▼
vata-mcp server  (src/vata_mcp/, FastMCP)
   ├─ server.py           13 tools + 7 prompts, thin — delegates to services
   ├─ auth.py             static bearer-token TokenVerifier for HTTP transport
   └─ services/
        ai_service.py       fill-in-the-gaps metadata resolution (§2)
        category_service.py category/asset CRUD, id-or-name/title resolution
        decision_service.py BM25 + optional LLM re-rank search
        storage.py          Mongo/mongomock data access
                       │
                       ▼
        MongoDB (Atlas free M0, or local Community Server, or in-memory
        mongomock if VATA_MONGODB_URI is unset)
```

Two deployment modes coexist:
- **Local**: stdio transport, local Mongo (`mongodb://localhost:27017`),
  no auth needed (no network exposure). Wired via `.mcp.json` /
  `~/.claude.json`.
- **Remote**: HTTP transport, MongoDB Atlas, `VATA_MCP_TOKEN` required.
  Currently deployed to Render free tier at `vata-mcp.onrender.com`.

## 6. Environment variables

| Variable | Default | Effect |
|---|---|---|
| `VATA_MONGODB_URI` | unset → `mongomock` in-memory | Real MongoDB connection string |
| `VATA_MONGODB_DB` | `vata` | Database name |
| `VATA_LLM_MODEL` | unset → heuristic only | litellm model string; fallback-path LLM, not used when the caller supplies fields explicitly |
| `VATA_MCP_TRANSPORT` | `stdio` | `stdio` or `http` |
| `VATA_MCP_TOKEN` | unset → auth disabled | Bearer token required on HTTP transport |
| `VATA_CLEAN_PASSWORD` | unset → `vata_clean` disabled | Password `vata_clean` checks against |
| `PORT` | — | Render/Railway-injected; takes priority over `VATA_MCP_PORT` for HTTP bind |

## 7. What's deployed right now

- Render free web service `vata-mcp`, branch `mcp`, auto-deploys on push.
- MongoDB Atlas free M0 cluster, user `vatauser`.
- `VATA_MCP_TOKEN` set; `VATA_CLEAN_PASSWORD` — confirm it's set on Render
  before relying on `/vata-clean` remotely (it was added after the last
  manual env var pass in the dashboard).
- Local dev: MongoDB Community Server via `winget`, wired through both a
  project-scoped `.mcp.json` and the global `~/.claude.json`.

## 8. Known gaps / not yet done

- **Distribution for other users**: see
  [VATA_DISTRIBUTION_PLAN.md](VATA_DISTRIBUTION_PLAN.md) — setup wizard,
  config file loader, PyPI publish. Not started.
- **ChatGPT connector**: attempted, failed before reaching the server at
  all (confirmed via Render logs — zero incoming requests). Looked like an
  account/plan-side restriction on OpenAI's end, not fixable from our
  side. Not retried since.
- **Windsurf IDE connector**: attempted, not resolved this session — last
  known state was testing header variants (`Content-Type` alongside
  `Authorization`). No confirmed working config yet.
- **Gemini web app**: no known custom-MCP-connector support in the
  consumer web UI as of last check; not verified against current Gemini
  UI, could have changed.
- **`decision_service.py`'s LLM re-rank pass** still makes its own
  separate LLM call (via `VATA_LLM_MODEL`) for search re-ranking — this
  was *not* part of the §2 redesign, which only covered `vata_save`/
  `vata_edit_asset`. Worth revisiting with the same "let the calling model
  do it" lens if `vata_find`'s match-reason quality becomes a concern.
- **Category consolidation**: nothing automatically merges near-duplicate
  categories the calling model might create over time (e.g. "Docs" vs
  "Documentation"). `vata_edit_category` supports manual rename/merge-by-
  rename, but nothing proactive exists.
