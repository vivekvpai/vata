# Changelog

All notable changes to `vata-mcp`. Format loosely follows [Keep a
Changelog](https://keepachangelog.com/).

## [0.2.0] — Unreleased

### Added
- `vata-mcp setup` interactive wizard: guides local/Atlas MongoDB choice
  (with live connection validation), optional fallback LLM, optional
  access token generation, optional `/vata-clean` password — writes
  everything to a persistent per-user config file.
- Layered configuration (`config.py`): environment variable → config file
  → default. Every module (`storage`, `ai_service`, `decision_service`,
  `auth`, `server`) now reads settings through this instead of scattered
  `os.getenv()` calls.
- `SETUP.md` and `CLIENT_SETUP.md`: from-scratch setup guide and per-MCP-
  client config instructions, distinguishing confirmed-working clients
  from attempted-but-unconfirmed ones (ChatGPT, Windsurf, Gemini web).
- Packaging metadata for PyPI distribution (classifiers, keywords,
  license, project URLs).

### Changed
- `vata-mcp` console script now dispatches through `cli.py`: bare
  `vata-mcp` still runs the server, `vata-mcp setup` runs the wizard.

## [0.1.x] — Prior work on the `mcp` branch

Squashed history of the branch's evolution, for context:

- **Categorization redesign**: `vata_save`/`vata_edit_asset` now accept
  explicit `title`/`category`/`category_description`/`description`/`tags`
  — the calling LLM (Claude, etc.) is instructed via the `/vata-save`
  prompt to check `vata_list_categories` and decide these itself. Fields
  left blank still fall back to `VATA_LLM_MODEL` or a local heuristic, but
  that path is now the exception, not the default. (Previously, `vata_save`
  took only `content` and decided the category itself via a heuristic or
  a separate LLM call — the chat model was never involved.)
- **`vata_clean`**: password-gated full database wipe, disabled entirely
  unless `VATA_CLEAN_PASSWORD` is configured.
- **Heuristic quality fix**: the no-LLM fallback no longer echoes a user's
  hint verbatim into the stored description, and truncation always cuts
  at a word boundary.
- **`vata_stats` / `vata_list_categories` / `vata_describe`**: metrics,
  table-view category listing, and full self-introspection (tools,
  prompts, storage/AI/auth backend status).
- **Data model redesign**: categories gained AI-written descriptions;
  later, the whole asset model changed from freeform `main_content`/
  `summary` with many-to-many category membership to `title`/`content`/
  `description`/`tags` with exactly one category per asset (deleting a
  category now cascades to its assets, replacing the old orphan-unlink
  logic).
- **MCP-only branch restructure**: removed the original FastAPI + React
  app from this branch (still on `master`), flattened the MCP server from
  a nested `mcp/` subdirectory to repo root.
- **Deployment**: bearer-token auth (`auth.py`), `render.yaml` blueprint,
  deployed to Render free tier against a MongoDB Atlas free cluster.
- **Local dev**: MongoDB Community Server via `winget`, wired through both
  a project-scoped `.mcp.json` and the global Claude Code config.
- Initial implementation: `vata_save`/`vata_get`/`vata_find` ported from
  the original FastAPI app's `category_service.py`/`decision_service.py`/
  `ai_service.py`, storage rewritten from flat JSON files to MongoDB
  (`mongomock` in-memory fallback when no `VATA_MONGODB_URI` is set).
