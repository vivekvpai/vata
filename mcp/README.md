# vata-mcp

Vata exposed as an MCP server: save/get/find plus full CRUD, with
categories decided entirely by AI (never a user-facing concept).

This lives inside the `vata` repo as an independent Python project (its own
`pyproject.toml` + venv, no import dependency on `../src/vata`), built per
[`../VATA_MCP_PLAN.md`](../VATA_MCP_PLAN.md), [`../VATA_SCHEMA.md`](../VATA_SCHEMA.md),
and [`../VATA_DATAFLOW.md`](../VATA_DATAFLOW.md).

## Current status: local dummy build

- **Database**: in-memory `mongomock` by default — no real MongoDB needed
  to run and test. Data does **not** persist across restarts. Set
  `VATA_MONGODB_URI` to point at a real MongoDB (e.g. Atlas) later — no
  code changes required, `storage.py` switches automatically.
- **AI**: category/summary/tag decisions use a local keyword-overlap
  heuristic by default — no LLM API key needed. Set `VATA_LLM_MODEL`
  (litellm-style model string, e.g. `gpt-4o-mini`) plus the provider's API
  key env var to switch to a real LLM — again no code changes required.
- **Hosting**: not deployed yet. Runs locally over stdio or streamable-http
  transport. Deploying to Render/Railway is a later step (per the plan).

## Setup

```bash
cd vata-mcp
python -m venv venv
./venv/Scripts/pip install -e .        # Windows
# source venv/bin/activate && pip install -e .   # macOS/Linux

# optional, for real LLM support:
./venv/Scripts/pip install -e ".[llm]"
```

## Running

**Stdio (for Claude Desktop/Code config):**

```bash
./venv/Scripts/python -m vata_mcp.server
```

**HTTP (for testing with curl / remote clients):**

```bash
VATA_MCP_TRANSPORT=http VATA_MCP_PORT=8765 ./venv/Scripts/python -m vata_mcp.server
```

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `VATA_MONGODB_URI` | unset (uses `mongomock`) | Real MongoDB connection string |
| `VATA_MONGODB_DB` | `vata` | Database name |
| `VATA_LLM_MODEL` | unset (uses heuristic) | litellm model string for real AI decisions |
| `VATA_MCP_TRANSPORT` | `stdio` | `stdio` or `http` |
| `VATA_MCP_HOST` | `0.0.0.0` | HTTP transport bind host |
| `VATA_MCP_PORT` | `8765` | HTTP transport bind port |

Auth (bearer token) and cloud deployment are **not yet implemented** — see
plan Phase 3/4. This build is local-only, meant to validate the tool
surface and logic before wiring up real infra.

## Tools

| Tool | Slash prompt | Notes |
|---|---|---|
| `vata_save` | `/vata-save` | No `category` arg — AI decides |
| `vata_get` | `/vata-get` | asset_id / category_id / neither |
| `vata_find` | `/vata-find` | BM25 + optional LLM re-rank |
| `vata_suggest` | — | Preview AI decision without saving |
| `vata_edit_asset` | — | Patch content/summary/tags |
| `vata_delete_asset` | — | Requires `confirm: true` |
| `vata_delete_category` | — | Requires `confirm: true` |
| `vata_rename_category` | — | Admin/AI maintenance use |
| `vata_link_asset` / `vata_unlink_asset` | — | Many-to-many membership |
| `vata_replace_category` | — | Bulk replace |

## Smoke test

```bash
./venv/Scripts/python scripts/smoke_test.py
```

Exercises save → find → get → edit → link/unlink → delete end to end
against the in-memory dummy DB, with no external services required.
