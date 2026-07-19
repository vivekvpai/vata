# Vata MCP — Client Setup

Config snippets for connecting `vata-mcp` to specific MCP clients. Run
`vata-mcp setup` first (see [SETUP.md](SETUP.md)) — it prints a config
block already filled in for you; this doc explains *where* to put it per
client, and calls out what's actually confirmed working versus untested.

---

## Confirmed working

### Claude Code (project-scoped)

Create `.mcp.json` in your project's root directory:

```json
{
  "mcpServers": {
    "vata": {
      "command": "vata-mcp"
    }
  }
}
```

Claude Code picks this up automatically for sessions opened in that
directory. Requires restarting Claude Code (or opening a fresh session)
after adding it — an already-running session won't pick up a newly added
`.mcp.json`.

### Claude Code / Claude Desktop (global)

Edit your global MCP config (`~/.claude.json` on most setups — check
Claude's own docs if that path doesn't exist for your install) and add
under the existing `"mcpServers"` key:

```json
"vata": {
  "type": "stdio",
  "command": "vata-mcp"
}
```

This makes `vata` available in every session regardless of directory.
Requires a full restart of the client (not just a new session) to be
picked up, since global config is read once at startup.

### Remote / hosted deployment (any MCP client that supports HTTP transport)

If you deployed `vata-mcp` somewhere reachable over the network (see the
"Deploying remotely" section in [README.md](README.md)), use the HTTP
form instead of `command`:

```json
"vata": {
  "type": "http",
  "url": "https://your-deployment.example.com/mcp",
  "headers": {
    "Authorization": "Bearer YOUR_TOKEN_HERE"
  }
}
```

The token is whatever `vata-mcp setup` generated (or whatever you set
`VATA_MCP_TOKEN` to on the deployment). Confirmed working against Render's
free tier with this exact shape — note the URL must include the `/mcp`
path, and some clients redirect `/mcp` → `/mcp/` or vice versa
transparently; if a connection silently fails, try adding or removing the
trailing slash.

---

## Attempted, not confirmed working

Flagging these honestly rather than guessing — if you get one working,
consider sending a fix for this doc.

### ChatGPT (desktop/web, custom connector)

Attempted via the "New Plugin" developer connector flow. The connection
failed before any request reached the server at all (confirmed via server
logs showing zero incoming requests) — this points to an account/plan-side
restriction on OpenAI's end (custom MCP connectors may require a paid
tier), not something fixable from Vata's side. Not retried since.

### Windsurf IDE

Attempted with a `serverUrl` + `headers` config shape similar to examples
seen for other MCP servers (e.g. GitHub's remote MCP connector). Not
confirmed working by the end of the session that tried it — last state was
testing whether an explicit `Content-Type: application/json` header
alongside `Authorization` was required. If you're trying this, start from:

```json
"vata": {
  "serverUrl": "https://your-deployment.example.com/mcp",
  "headers": {
    "Authorization": "Bearer YOUR_TOKEN_HERE",
    "Content-Type": "application/json"
  }
}
```

...and check Windsurf's Output/Logs panel (View → Output) if it doesn't
show up in the server list — it likely logs why a config entry was
rejected.

### Gemini (web app, gemini.google.com)

No confirmed custom-MCP-connector support in the consumer web UI as of
last check. Google's MCP support has mostly shipped through Gemini CLI
(a terminal tool, out of scope for "chat app" use) rather than the web
chat interface. This may have changed since — worth checking Gemini's own
Settings for a "Connectors"/"Extensions"/"Tools" section before assuming
it's unsupported.

---

## General troubleshooting

- **Tools don't show up after adding config**: restart the client
  entirely, not just start a new chat/session — MCP server configs are
  typically read once at startup.
- **"Connection failed" with no other detail**: run `vata-mcp` by hand in
  a terminal first (just the bare command, no client involved) — if it
  crashes or prints an error immediately, fix that before troubleshooting
  the client integration.
- **Works locally but not for remote/HTTP clients**: double-check
  `VATA_MCP_TOKEN` is set on the deployment and the exact same token is in
  the client's `Authorization: Bearer ...` header — a mismatch here fails
  silently in some clients rather than showing a clear auth error.
