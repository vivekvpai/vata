# vata-mcp

Vata exposed as an MCP server: a personal link/notes archive. Save a link
or note; the LLM already driving your chat session decides its title,
category, description, and tags and calls `vata_save` with them — you
just save and search, categories are never something you manage by hand.

**Design note:** the categorization "AI" here is not a separate service —
it's whichever model is already in your MCP client (Claude, etc.). The
`/vata-save` prompt instructs it to call `vata_list_categories`, decide
fit-or-new itself, and pass explicit values into `vata_save`. No
`VATA_LLM_MODEL` or API key is needed for this to work well. That setting
only matters for callers that *can't* reason (a bare script calling the
tool directly) — see [Tools](#tools) below.

This branch is MCP-only — the original FastAPI + React app lives on
`master`. Design docs: [VATA_MCP_PLAN.md](VATA_MCP_PLAN.md),
[VATA_SCHEMA.md](VATA_SCHEMA.md), [VATA_DATAFLOW.md](VATA_DATAFLOW.md).

## Current status

Running locally for personal use, on this machine, right now:

- **Database**: real, persistent MongoDB Community Server, installed
  locally via `winget install MongoDB.Server`, running as a Windows
  service on `mongodb://localhost:27017`. No account, no internet
  dependency, no cost. (Falls back to in-memory `mongomock` automatically
  if `VATA_MONGODB_URI` isn't set — useful for quick throwaway testing.)
- **AI**: the calling assistant (Claude, etc.) decides title/category/
  description/tags itself and passes them into `vata_save` — no separate
  LLM call, no API key needed for normal chat use. `VATA_LLM_MODEL` is
  only a fallback for non-reasoning callers; unset by default, falls back
  further to a local keyword-overlap heuristic if also unset.
- **Client wiring**: `.mcp.json` at the repo root configures Claude
  Code to launch this server via stdio automatically when you're working
  in this folder — nothing to run manually.
- **Auth**: not needed for this setup. Bearer-token auth
  (`VATA_MCP_TOKEN`, see `src/vata_mcp/auth.py`) only matters if this ever
  gets exposed over HTTP to something other than your own local client —
  stdio-to-local-process has no network exposure to protect against.

Remote hosting (Render + MongoDB Atlas) is documented below for later, if
you ever want this reachable from somewhere other than this machine — it's
not required for personal local use and isn't currently deployed.

## Deploying remotely (optional, free tier, ~15 min)

1. **MongoDB Atlas** (free M0 cluster): create one at
   [mongodb.com/atlas](https://www.mongodb.com/atlas), create a database
   user, allow network access from anywhere (`0.0.0.0/0` — Render's egress
   IPs aren't static on the free plan), and copy the `mongodb+srv://...`
   connection string.
2. **Generate a token**: anything long and random, e.g.
   `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
3. **Push this repo to GitHub**, then in Render: New → Blueprint → point
   at the repo. `render.yaml` at the root defines the service. Render will
   prompt for the `sync: false` env vars (`VATA_MCP_TOKEN`,
   `VATA_MONGODB_URI`, optionally `VATA_LLM_MODEL` + its provider API key)
   — paste them in.
4. **Deploy.** Render builds with `pip install -e ".[llm]"` and runs
   `python -m vata_mcp.server`, which binds to Render's injected `PORT`.
5. **Connect a client**: point Claude Desktop/Code or Gemini CLI at
   `https://<your-service>.onrender.com/mcp/` as a remote MCP server, with
   header `Authorization: Bearer <your token>`.

Free-tier caveat: Render's free web services sleep after 15 min idle: the
first request after a while has cold-start latency (10-30s). Acceptable
for personal use; not for anything latency-sensitive.

## Local setup (personal use)

```bash
# 1. Local MongoDB (one-time, Windows):
winget install MongoDB.Server
# runs as a Windows service automatically, listens on localhost:27017

# 2. This project:
python -m venv venv
./venv/Scripts/pip install -e .        # Windows
# source venv/bin/activate && pip install -e .   # macOS/Linux
```

Claude Code picks up `.mcp.json` in this repo automatically — no manual
server launch needed. It points at `venv/Scripts/python.exe` and sets
`VATA_MONGODB_URI=mongodb://localhost:27017`.

To run it by hand instead (e.g. for other MCP clients):

**Stdio:**

```bash
VATA_MONGODB_URI=mongodb://localhost:27017 ./venv/Scripts/python -m vata_mcp.server
```

**HTTP (for testing with curl / remote clients):**

```bash
VATA_MCP_TRANSPORT=http VATA_MCP_PORT=8765 VATA_MONGODB_URI=mongodb://localhost:27017 ./venv/Scripts/python -m vata_mcp.server
```

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `VATA_MONGODB_URI` | unset (uses `mongomock`) | Real MongoDB connection string |
| `VATA_MONGODB_DB` | `vata` | Database name |
| `VATA_LLM_MODEL` | unset (uses heuristic) | litellm model string for real AI decisions |
| `VATA_MCP_TRANSPORT` | `stdio` | `stdio` or `http` |
| `VATA_MCP_HOST` | `0.0.0.0` | HTTP transport bind host |
| `VATA_MCP_PORT` | `8765` | HTTP transport bind port (local only — Render's `PORT` takes priority) |
| `VATA_MCP_TOKEN` | unset (auth disabled) | Shared bearer token required on every HTTP request |
| `VATA_CLEAN_PASSWORD` | unset (`vata_clean` disabled) | Password required by `vata_clean` to wipe the entire database |

## Data model

Each asset (a saved link or note) belongs to **exactly one** category —
there's no many-to-many linking. Deleting a category deletes every asset
inside it. Assets have: `title`, `content` (the link or raw text saved),
`description`, `tags` — normally all decided by the calling assistant, see
the design note above. You can always address a specific asset by
`asset_id` or by its exact `title`.

## Tools

| Tool | Slash prompt | Notes |
|---|---|---|
| `vata_save` | `/vata-save` | `content` (link/text) + `title`/`category`/`category_description`/`description`/`tags` — the calling assistant should fill these in itself after checking `vata_list_categories`. Anything left blank falls back to `VATA_LLM_MODEL` or a local heuristic |
| `vata_list_categories` | `/vata-list-categories` | Table: category, description, asset count. Call this before deciding a category for a new save |
| `vata_list_assets` | `/vata-list-assets` | Table for one category: title, content, description, tags |
| `vata_find` | `/vata-find` | Search by meaning; returns matching assets **and** the categories they came from, both table-ready |
| `vata_stats` | `/vata-stats` | Total categories, total assets, server version |
| `vata_describe` | `/vata-describe` | What Vata is, every tool/prompt, storage/AI/auth config |
| `vata_suggest` | — | Preview what the fallback (LLM/heuristic) would decide, without saving — for debugging the fallback path specifically |
| `vata_edit_category` | — | Rename and/or edit description; assets move with a rename |
| `vata_edit_asset` | — | Give `new_content` + `new_title`/`new_description`/`new_tags` (caller decides these), or edit by id/current_title directly |
| `vata_delete_category` | — | Requires `confirm: true`. Deletes the category **and every asset inside it** |
| `vata_delete_asset` | — | Requires `confirm: true`. Deletes only that one asset |
| `vata_clean` | `/vata-clean` | Wipes **everything** (all categories + assets). Requires a password matching `VATA_CLEAN_PASSWORD`; disabled entirely if that env var isn't set |
| `vata_replace_category` | — | Bulk replace all assets in a category |

## Project structure

```
src/vata_mcp/
  server.py              MCP server: tool + prompt registration
  services/
    storage.py           Mongo/mongomock data access (one category per asset)
    category_service.py  Category/asset CRUD, id-or-name/title resolution
    decision_service.py  BM25 + optional LLM re-rank search
    ai_service.py         AI title/category/description/tag decisions
scripts/
  smoke_test.py          End-to-end test against the dummy DB
```

## Smoke test

```bash
./venv/Scripts/python scripts/smoke_test.py
```

Exercises save → list-categories → list-assets → edit-category → find →
edit-asset → delete-asset → delete-category (cascading) → describe → clean,
end to end, against the in-memory dummy DB with no external services
required.

**This test calls `vata_clean` and will wipe whatever database it's pointed
at.** It refuses to run if `VATA_MONGODB_URI` is set in your environment,
to avoid accidentally wiping a real database — unset it first, or pass
`--allow-real-db` if you genuinely want to test against a real Mongo
instance (e.g. a scratch/throwaway one).
