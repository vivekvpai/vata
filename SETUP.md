# Vata MCP — Setup Guide

For anyone installing `vata-mcp` for the first time, with no prior MongoDB
or MCP experience. If you're comfortable with both already, `vata-mcp
setup` alone (see below) is probably all you need — this doc is the
from-scratch version.

---

## 1. Install

```bash
pipx install vata-mcp
```

`pipx` is recommended over plain `pip install` because it isolates this
tool's dependencies from any other Python project on your machine. If you
don't have `pipx`:

```bash
python -m pip install --user pipx
python -m pipx ensurepath
```

(then restart your terminal, and retry the `pipx install vata-mcp` command)

Don't have `pipx` and don't want it? `pip install vata-mcp` works too,
just without the isolation.

## 2. Get a database

Vata stores everything you save in a MongoDB database. You need exactly
one of these — pick whichever is easier for you:

### Option A — Local MongoDB (simplest, free, no account)

Runs on your own machine, no internet dependency once installed:

- **Windows**: `winget install MongoDB.Server`
- **macOS**: `brew install mongodb-community`
- **Linux**: follow [MongoDB's official install
  guide](https://www.mongodb.com/docs/manual/administration/install-on-linux/)
  for your distribution

Once installed, it runs as a background service automatically — you
don't need to start it manually, and don't need to remember any
connection details. `vata-mcp setup` (next step) will find it on its own
at the default address.

### Option B — MongoDB Atlas (free cloud tier, needed if you want to
access Vata from more than one device, or host it remotely)

1. Go to [mongodb.com/atlas](https://www.mongodb.com/atlas) and sign up
   (free, no credit card required for the free tier).
2. Click **Build a Database** → choose **M0 Free**.
3. Once it's created, go to **Database Access** (left sidebar) → **Add
   New Database User** → pick a username, and **type your own password
   directly** rather than using "Autogenerate" (copy/paste errors with
   generated passwords are a common source of connection failures).
4. Go to **Network Access** (left sidebar) → **Add IP Address** → **Allow
   Access from Anywhere** (`0.0.0.0/0`). This is necessary for cloud
   hosting providers (Render, Railway, etc.) that don't have a fixed IP.
5. Go back to your cluster → **Connect** → **Drivers** → copy the
   connection string. It looks like:
   ```
   mongodb+srv://<username>:<password>@cluster0.xxxxx.mongodb.net/?appName=Cluster0
   ```
6. Replace `<username>` and `<password>` with what you set in step 3.

Keep this connection string handy for the next step.

## 3. Run the setup wizard

```bash
vata-mcp setup
```

This asks a few questions:
- **Local or Atlas?** — if local, it checks that MongoDB is actually
  reachable before continuing; if Atlas, paste the connection string from
  step 2 and it verifies the connection live, on the spot.
- **Fallback LLM?** — almost always **no** for normal use. The chat model
  you're already talking to (Claude, etc.) handles categorization for
  free as part of normal tool use. This setting only matters if you plan
  to call Vata's tools directly from a script that has no LLM of its own
  reasoning about the content.
- **Access token?** — only needed if you'll run Vata reachable from
  outside your own machine (e.g. deployed to a cloud host). For local use
  with Claude Desktop/Code on the same machine, say no.
- **Enable /vata-clean?** — a full-database-wipe command, gated by a
  password you set here. Optional; most people can say no.

Everything you answer gets saved to a config file (path varies by OS,
printed at the top of the wizard's output) so you never have to answer
these again — `vata-mcp` picks it up automatically on every future run.

At the end, it prints a ready-to-paste MCP client config block.

## 4. Connect a client

Paste the config block the wizard printed into your MCP client. See
[CLIENT_SETUP.md](CLIENT_SETUP.md) for exact instructions per client
(Claude Desktop, Claude Code, etc.).

## 5. Try it

In your chat client, say something like: "save this link:
https://example.com — it's a good example". The assistant should look at
your existing categories, decide on one (or create a new one), and store
it — you never need to name or manage categories yourself.

---

## Troubleshooting

**"Could not connect" during the Atlas step** — almost always one of:
network access not set to allow your IP (§2 step 4), or a typo in the
password inside the connection string. Re-copy the string fresh from
Atlas's Connect dialog rather than hand-editing a previous one.

**`vata-mcp` command not found after install** — `pipx`/`pip install
--user` put scripts in a directory that may not be on your `PATH` yet.
Restart your terminal, or run `python -m pipx ensurepath` again.

**Local MongoDB not found during setup** — the wizard checks
`mongodb://localhost:27017` specifically. If you installed MongoDB to a
non-default port or it's not running as a service, start it manually and
re-run `vata-mcp setup`.
