# Vata MCP — Distribution Plan

Goal: let a stranger install `vata-mcp`, point it at their own MongoDB
(local or Atlas) and optionally their own LLM key, and start using it from
any MCP client — without ever touching this repo's source or knowing
anything about FastMCP/Mongo internals.

Current state: already a proper installable package (`pyproject.toml`,
`src/` layout, console entry point `vata-mcp`). What's missing is
everything *around* the code — packaging polish, a guided first-run setup,
and docs a non-author can follow.

---

## 1. What "package it" actually means here

Three distinct audiences, three different bars:

| Audience | What they need |
|---|---|
| You (today) | Already working — local venv, local Mongo, `.mcp.json` |
| A technical friend | `pip install vata-mcp`, answer a few setup prompts, get a working MCP config snippet |
| A totally new user | Same as above, but every step must be self-explanatory — no assumed knowledge of MongoDB, MCP, or Python venvs |

Design for the middle tier (technical friend) as the primary target — a
truly non-technical user installing and running a local Python MCP server
by hand is out of scope without a GUI installer, which is a much bigger
project. Flag this explicitly in the docs rather than pretending otherwise.

---

## 2. Distribution mechanism

**Publish to PyPI** as `vata-mcp` (or whatever name is available —
`pip install vata-mcp` needs to not collide with an existing package;
check availability first). This gives:

- `pip install vata-mcp` from anywhere, no repo clone needed
- `pipx install vata-mcp` as the recommended method (isolates it from
  other Python environments — better default advice than raw `pip
  install` for a CLI tool)
- Automatic dependency resolution (fastmcp, pymongo, etc.) — already
  declared correctly in `pyproject.toml`

Versioning: bump `version` in `pyproject.toml` per release; tag matching
git tags (`v0.1.0`, etc.) so PyPI history and git history line up.

Not in scope for v1: Docker image, Homebrew formula, Windows installer/EXE.
These are reasonable v2 additions if demand shows up, not needed for "a
stranger can `pip install` and run this."

---

## 3. First-run setup experience (the actual hard part)

The current design assumes env vars are already set correctly
(`VATA_MONGODB_URI`, `VATA_MCP_TOKEN`, etc.) before the server starts. A
new user has no idea what to set or why. Add a **guided setup command**:

```
vata-mcp setup
```

An interactive CLI wizard (using `typer` or plain `input()` prompts — no
new heavy dependency needed) that:

1. Asks: "Use a local MongoDB, or a MongoDB Atlas connection string?"
   - **Local**: checks if `mongod` is reachable at `localhost:27017`; if
     not, prints the one-line install command for their OS (`winget
     install MongoDB.Server` / `brew install mongodb-community` / apt
     instructions) and waits for confirmation before continuing.
   - **Atlas**: prompts for the connection string directly, validates it
     by attempting a real `ping` command against it on the spot (fail
     fast with a clear message, not a stack trace, if auth/network is
     wrong).
2. Asks: "Do you want AI-powered categorization (needs an LLM API key), or
   the free local heuristic (no key needed, works out of the box but less
   smart)?" — if LLM, prompts for `VATA_LLM_MODEL` + reminds them to set
   their provider's own API key env var (we don't store/proxy that key).
3. Asks: "Generate a random access token for this server?" → generates one
   with `secrets.token_urlsafe(32)` (exact snippet already proven working
   in this project) and displays it once, clearly labeled as
   save-this-now.
4. Asks: "Enable the /vata-clean full-wipe command? If yes, set a
   password for it now." (optional, skippable — most users may not want
   this exposed at all).
5. Writes a local **`.env` file** (or platform-appropriate config dir —
   see §4) with everything collected, so future runs of `vata-mcp` just
   pick it up automatically — no re-asking every time.
6. Prints a ready-to-paste MCP client config block (stdio-style, pointing
   at the installed `vata-mcp` command) for Claude Desktop/Code, so the
   user's very next step is "paste this into your client," not "figure out
   the JSON shape yourself."

This wizard is the single highest-leverage thing to build — it's the
difference between "technically installable" and "actually usable by
someone who isn't you."

---

## 4. Config file location (replacing ad-hoc env vars)

Right now everything is read via `os.getenv(...)` scattered across
`storage.py`, `ai_service.py`, `auth.py`, `server.py`. For a distributed
package, env vars alone are a bad UX (nobody wants to export 5 vars every
terminal session). Add:

- A config file at the OS-appropriate user config dir
  (`~/.config/vata-mcp/config.toml` on Linux/Mac,
  `%APPDATA%\vata-mcp\config.toml` on Windows — `platformdirs` is the
  standard tiny dependency for this lookup, or hand-roll it, it's a
  one-liner).
- Load order: env var (if set) → config file → built-in default. This
  keeps env vars working for power users / CI / Docker while giving
  everyone else a persistent file the setup wizard writes to.
- One small helper module, e.g. `src/vata_mcp/config.py`, centralizing
  this lookup so `storage.py`/`ai_service.py`/`auth.py`/`server.py` all
  call `config.get("VATA_MONGODB_URI")` instead of `os.getenv(...)`
  directly. This is a mechanical refactor, low risk, but touches every
  existing module — do it once, carefully, with the smoke test as the
  regression check.

---

## 5. Docs to write

- **`README.md`** (rewrite the "Setup" section): lead with `pipx install
  vata-mcp && vata-mcp setup`, not with cloning this repo and building a
  venv. Keep the current local-dev instructions (clone + editable install)
  as a separate "Contributing / running from source" section further down,
  since that's a different audience (people modifying the code, not just
  using it).
- **`SETUP.md`** (new): a from-scratch guide for someone who has never
  touched MongoDB or MCP. Screenshots or exact command blocks for:
  Atlas free-tier signup → cluster → connection string, vs. local Mongo
  install per OS. This is the doc that makes the wizard's Atlas/local
  choice make sense to someone unfamiliar with either option.
- **`CLIENT_SETUP.md`** (new, or fold into README): copy-paste config
  blocks for each MCP client we know works — Claude Desktop, Claude Code
  (project `.mcp.json` and global config, both shown in this repo's
  history), plus whatever we've verified for others. Be explicit about
  what's confirmed-working vs. untested (e.g. Windsurf's exact header
  requirements weren't fully nailed down this session — don't claim
  certainty we don't have).
- **`CHANGELOG.md`** (new): even a minimal one — "what changed between
  versions" matters once other people depend on this instead of just you.

---

## 6. Scripts needed

- **`scripts/release.sh`** (or `.py`): bump version in `pyproject.toml`,
  build (`python -m build`), upload (`twine upload`), tag the commit. One
  command instead of remembering the PyPI publish steps each time.
- **`scripts/smoke_test.py`**: already exists and already has the
  real-DB safety guard from earlier — keep as the pre-release regression
  check, run it before every `scripts/release.sh`.
- **`scripts/setup_wizard.py`** (or make it a subcommand inside
  `server.py`'s CLI, i.e. `vata-mcp setup` per §3) — this is the main new
  script. Whether it's a separate file or a Typer subcommand of the
  existing entry point is a small implementation choice, not a design
  fork — subcommand is cleaner (one installed command, `vata-mcp` vs.
  `vata-mcp-setup`).

---

## 7. Multi-user reality check (important, don't skip)

Right now, `VATA_MCP_TOKEN` is a **single shared secret** — fine for "one
person, one deployment." Once this is a package other people install
independently, each person runs their **own separate server + own
database** (their own Atlas cluster or local Mongo) — this is NOT a
multi-tenant SaaS where many users share one deployment. That's the
correct and simplest model for this plan: package = "software you run
yourself," not "a service we host for everyone."

Make this explicit in the README so nobody mistakenly assumes signing up
somewhere or sharing infrastructure with other users — everyone who
installs this package gets a fully independent, isolated instance pointed
at their own database.

---

## 8. Build order (phases)

1. **Config file + loader refactor** (§4) — foundational, everything else
   builds on this. Verify with the existing smoke test after every module
   touched.
2. **Setup wizard** (§3) — the actual UX payoff. Test it manually end to
   end: fresh empty config dir, walk through every prompt path (local
   Mongo / Atlas / LLM yes-no / clean-password yes-no).
3. **PyPI packaging polish** — check name availability, add
   classifiers/keywords/license metadata to `pyproject.toml` if not
   already complete, build locally with `python -m build` and inspect the
   wheel contents before ever publishing.
4. **Docs** (§5) — write once the wizard and config behavior are final, so
   docs describe what actually exists rather than the plan.
5. **First real publish** to PyPI (start with a `0.1.0` or `0.2.0`,
   whichever is next after current work), smoke-test the *installed*
   package (not just the dev checkout) in a clean venv on a clean machine
   if possible.
6. **Release script** (§6) — write once step 5 has been done manually at
   least once successfully, so the script encodes a proven-working
   sequence rather than a guessed one.

---

## 9. Open decisions to confirm before building

- Exact PyPI package name (check `pypi.org/project/vata-mcp` availability
  before committing to it anywhere in docs).
- Whether the setup wizard is a `vata-mcp setup` subcommand (recommended)
  or a standalone script — affects `pyproject.toml`'s `[project.scripts]`
  entry.
- Whether to keep supporting the current "just set env vars, no config
  file" mode indefinitely for power users/CI, or eventually deprecate it
  in favor of the config file — recommend keeping both, env vars always
  win when set, since that's zero extra work and doesn't break anything
  existing.
