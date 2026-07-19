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

Design docs: [VATA_MCP_PLAN.md](VATA_MCP_PLAN.md),
[VATA_SCHEMA.md](VATA_SCHEMA.md), [VATA_DATAFLOW.md](VATA_DATAFLOW.md).
Single-user per install — everyone who installs this runs their own
server against their own database; there's no shared/multi-tenant
service.

## Install

```bash
pipx install vata-mcp
vata-mcp setup
```

The setup wizard walks you through picking a MongoDB (local or Atlas,
validated live), an optional fallback LLM, an optional access token, and
an optional `/vata-clean` password — then prints a ready-to-paste MCP
client config block. Full walkthrough, including MongoDB installation, in
[SETUP.md](SETUP.md). Per-client config instructions (Claude Desktop/Code
confirmed working; ChatGPT/Windsurf/Gemini attempted, not confirmed) in
[CLIENT_SETUP.md](CLIENT_SETUP.md).

Settings are saved to a config file (env vars still override it if set —
see [Environment variables](#environment-variables)), so `vata-mcp setup`
only needs to run once.

## Deploying remotely (optional, free tier, ~15 min)

Only needed if you want Vata reachable from somewhere other than the
machine it's installed on (e.g. so a phone or a second computer can use
it too). Personal local use does not need this section at all.

1. **MongoDB Atlas** (free M0 cluster): see [SETUP.md §2 Option
   B](SETUP.md#option-b--mongodb-atlas-free-cloud-tier-needed-if-you-want-to-access-vata-from-more-than-one-device-or-host-it-remotely).
2. **Generate a token**: `vata-mcp setup` can do this for you, or manually
   via `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
3. **Push this repo to GitHub**, then in Render: New → Blueprint → point
   at the repo. `render.yaml` at the root defines the service. Render will
   prompt for the `sync: false` env vars (`VATA_MCP_TOKEN`,
   `VATA_MONGODB_URI`, optionally `VATA_LLM_MODEL` + its provider API key)
   — paste them in.
4. **Deploy.** Render builds with `pip install -e ".[llm]"` and runs
   `vata-mcp`, which binds to Render's injected `PORT`.
5. **Connect a client**: see [CLIENT_SETUP.md](CLIENT_SETUP.md)'s "Remote
   / hosted deployment" section.

Free-tier caveat: Render's free web services sleep after 15 min idle: the
first request after a while has cold-start latency (10-30s). Acceptable
for personal use; not for anything latency-sensitive.

## Running from source (contributing / modifying the code)

If you're changing Vata's own code rather than just using it:

```bash
git clone <this repo> && cd vata
python -m venv venv
./venv/Scripts/pip install -e .        # Windows
# source venv/bin/activate && pip install -e .   # macOS/Linux
```

The installed `vata-mcp` command works the same as the packaged version
(`vata-mcp setup`, then `vata-mcp` to run). Editable install means changes
to `src/vata_mcp/` take effect without reinstalling.

Claude Code also picks up a project-scoped `.mcp.json` automatically if
one exists at the repo root — useful during development to point directly
at your local venv without going through the installed command:

```json
{
  "mcpServers": {
    "vata": {
      "command": "c:/path/to/venv/Scripts/python.exe",
      "args": ["-m", "vata_mcp.server"],
      "env": { "VATA_MONGODB_URI": "mongodb://localhost:27017" }
    }
  }
}
```

**Stdio (default, for MCP clients):**

```bash
./venv/Scripts/python -m vata_mcp.server
```

**HTTP (for testing with curl / remote clients):**

```bash
VATA_MCP_TRANSPORT=http VATA_MCP_PORT=8765 ./venv/Scripts/python -m vata_mcp.server
```

## Environment variables

Every setting below can be set as an environment variable, or saved to the
config file via `vata-mcp setup` (env var always wins if both are set).
Config file location: `%APPDATA%\vata-mcp\config.json` (Windows),
`~/Library/Application Support/vata-mcp/config.json` (macOS),
`~/.config/vata-mcp/config.json` (Linux) — see `src/vata_mcp/config.py`.

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
  cli.py                 `vata-mcp` entry point: dispatches to server or setup
  setup_wizard.py        `vata-mcp setup` interactive wizard
  config.py              env var -> config file -> default settings loader
  server.py              MCP server: tool + prompt registration
  auth.py                Static bearer-token verifier for HTTP transport
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
at.** It refuses to run if `VATA_MONGODB_URI` is set — via environment
variable *or* the config file `vata-mcp setup` writes — to avoid
accidentally wiping a real database. Unset it (or don't run `vata-mcp
setup` first) to use the safe in-memory default, or pass `--allow-real-db`
if you genuinely want to test against a real Mongo instance (e.g. a
scratch/throwaway one).
