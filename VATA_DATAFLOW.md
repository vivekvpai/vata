# Vata MCP — Data Flow Diagrams

Companion to [VATA_MCP_PLAN.md](VATA_MCP_PLAN.md) and
[VATA_SCHEMA.md](VATA_SCHEMA.md). Rendered as Mermaid. Reflects the
current implementation — the calling LLM decides categorization (plan
§2), one category per asset (plan §3).

---

## 1. System context

```mermaid
flowchart LR
    U[User] -->|"/vata-save, /vata-find,\nor natural language"| C[Chat Client\nClaude Desktop / Code / any MCP client]
    C -->|"MCP over stdio (local)\nor Streamable HTTP + Bearer token (remote)"| S[vata-mcp server]
    S -->|reads/writes| M[(MongoDB\nlocal, Atlas, or in-memory mongomock)]
    S -.->|"only for fallback path\n(VATA_LLM_MODEL, non-reasoning callers)"| L[LLM Provider via litellm]
```

The chat client's own model (Claude, etc.) does the categorization
reasoning as part of normal tool use — it is not a separate box in this
diagram, it *is* the client. The dotted line to "LLM Provider" is a
second, independent LLM call the **server itself** can optionally make,
used only when a caller doesn't supply title/category/description/tags
(e.g. a bare script) and no reasoning model is in the loop.

---

## 2. `vata_save` — the calling LLM decides, the server just stores

```mermaid
sequenceDiagram
    actor U as User
    participant Model as Chat model (e.g. Claude)
    participant T as vata-mcp server
    participant AI as ai_service
    participant CS as category_service
    participant DB as MongoDB

    U->>Model: "/vata-save <link/text>" or "save this: ..."
    Model->>T: call vata_list_categories()
    T->>CS: list_categories_record()
    CS->>DB: find categories, count assets per category
    DB-->>CS: category docs + counts
    CS-->>T: {count, categories: [{category, description, asset_count}, ...]}
    T-->>Model: category table
    Note over Model: Model reasons: reuse a fitting category,\nor invent a short new one.\nWrites its own title, description, tags.
    Model->>T: call vata_save(content, title, category,\ncategory_description?, description, tags)
    T->>AI: decide_asset_metadata(...) — all fields present, no computation
    AI-->>T: {title, category, category_description, description, tags, is_link} (verbatim passthrough)
    T->>CS: resolve_or_create_category(category, category_description)
    alt category name matches an existing one
        CS->>DB: find_category_by_name → return existing doc
    else no match
        CS->>DB: insert_category(new_id, name, description)
    end
    T->>CS: add_asset_to_category_record(category_id, title, content, description, tags)
    CS->>DB: insert_asset(...)
    CS->>DB: touch_category(category_id) — bump updated_at
    T-->>Model: {asset_id, title, category_id, category, description, tags, is_link}
    Model-->>U: "Saved as '<title>' under '<category>'."
```

### 2b. Fallback path — caller leaves fields blank (non-reasoning caller)

```mermaid
sequenceDiagram
    participant Caller as Script / non-reasoning caller
    participant T as vata-mcp server
    participant AI as ai_service
    participant DB as MongoDB
    participant LLM as LLM Provider

    Caller->>T: vata_save(content) — title/category/description/tags all omitted
    T->>AI: decide_asset_metadata(content, None, None, None, None, None)
    AI->>DB: list_categories() — for context
    alt VATA_LLM_MODEL configured
        AI->>LLM: filing-assistant prompt (existing categories + content)
        LLM-->>AI: {title, category, category_description, description, tags} JSON
    else no LLM configured, or LLM call/parse failed
        Note over AI: local heuristic: keyword-overlap category scoring,\nkeyword-based title/description synthesis
    end
    AI-->>T: resolved metadata
    T->>T: (same resolve_or_create_category + add_asset_to_category_record as §2)
```

---

## 3. `vata_list_assets` / `vata_list_categories` — browsing

```mermaid
sequenceDiagram
    actor U as User
    participant Model as Chat model
    participant T as vata-mcp server
    participant CS as category_service
    participant DB as MongoDB

    U->>Model: "/vata-list-categories" or "what categories do I have?"
    Model->>T: vata_list_categories()
    T->>CS: list_categories_record()
    CS->>DB: find all categories
    loop each category
        CS->>DB: count_assets_in_category(category_id)
    end
    CS-->>T: {count, categories: [{category_id, category, description, asset_count}]}
    T-->>Model: table data
    Model-->>U: rendered table: Category | Description | Assets

    U->>Model: "/vata-list-assets <category>"
    Model->>T: vata_list_assets(category_id? or category_name?)
    T->>CS: list_assets_in_category_record(...)
    CS->>DB: resolve_category(id or name)
    CS->>DB: list_assets_in_category(category_id)
    CS-->>T: {category, category_id, count, assets: [{asset_id, title, content, description, tags}]}
    T-->>Model: table data
    Model-->>U: rendered table: Title | Content | Description | Tags
```

---

## 4. `vata_find` — BM25 two-pass search, assets AND categories returned

```mermaid
sequenceDiagram
    actor U as User
    participant Model as Chat model
    participant T as vata-mcp server
    participant DS as decision_service
    participant DB as MongoDB
    participant LLM as LLM Provider

    U->>Model: "/vata-find <query>" or "what did I save about X?"
    Model->>T: vata_find(query)
    T->>DS: evaluate_nodes_for_query(query)
    DS->>DB: list_categories() + list_assets_in_category() per category
    Note over DS: Pass 1 — BM25 score each category's\naggregated asset text against the query
    opt VATA_LLM_MODEL configured
        DS->>LLM: classify which BM25-top categories are truly relevant
        LLM-->>DS: relevant_category_ids
    end
    Note over DS: falls back to trusting BM25 ranking\nas-is if no LLM or LLM call fails
    loop each relevant category
        DS->>DB: list_assets_in_category(category_id)
        Note over DS: Pass 2 — BM25 score assets within category
        opt VATA_LLM_MODEL configured
            DS->>LLM: rank candidates, produce match_reason per asset
            LLM-->>DS: [{asset_id, reason}, ...]
        end
        Note over DS: falls back to "keyword match" as the\nreason for every BM25-surfaced asset
    end
    DS->>DS: build categories[] summary from which categories\nthe surfaced assets actually came from
    DS-->>T: {count, assets: [...], categories: [...]}
    T-->>Model: both tables
    Model-->>U: rendered: assets table + categories table
```

---

## 5. Destructive flows — confirm-gated, category delete cascades

```mermaid
sequenceDiagram
    actor U as User
    participant Model as Chat model
    participant T as vata-mcp server
    participant CS as category_service
    participant DB as MongoDB

    U->>Model: "delete that asset" / "delete this category"
    Model->>T: vata_delete_asset(confirm: true, asset_id? or title?)
    Note over T: schema requires confirm literal true —\nvalidation fails before the tool body runs if omitted
    T->>CS: delete_asset_record(asset_id, title)
    CS->>DB: resolve_asset(...)
    CS->>DB: delete_asset(asset_id)
    CS->>DB: touch_category(category_id) — category itself is untouched
    T-->>Model: {message, asset_id, title}

    Model->>T: vata_delete_category(confirm: true, category_id? or category_name?)
    T->>CS: delete_category_record(...)
    CS->>DB: resolve_category(...)
    CS->>DB: delete_assets_in_category(category_id) — ALL assets inside, no orphan check needed
    CS->>DB: delete_category(category_id)
    T-->>Model: {message, deleted_asset_ids, deleted_asset_count}
    Model-->>U: "Deleted '<category>' and its N assets."
```

No orphan-detection logic exists anymore (removed with the many-to-many
model) — deleting a category is an unconditional cascade, since an asset
can no longer belong to any other category that would keep it alive.

---

## 6. `vata_clean` — password-gated full wipe

```mermaid
sequenceDiagram
    actor U as User
    participant Model as Chat model
    participant T as vata-mcp server (vata_clean)
    participant CS as category_service
    participant DB as MongoDB

    U->>Model: "/vata-clean" or "wipe everything"
    Model->>U: "What's the clean password?"
    U->>Model: <password>
    Model->>T: vata_clean(password)
    alt VATA_CLEAN_PASSWORD not set on server
        T-->>Model: {error: "vata_clean is disabled...", error_type: "RuntimeError"}
    else password mismatch (hmac.compare_digest)
        T-->>Model: {error: "Incorrect password...", error_type: "PermissionError"}
    else password matches
        T->>CS: wipe_all_data()
        CS->>DB: delete_many({}) on assets
        CS->>DB: delete_many({}) on categories
        CS-->>T: {deleted_categories, deleted_assets}
        T-->>Model: {message: "All categories and assets deleted", ...}
    end
    Model-->>U: report outcome — do not retry silently on error
```

---

## 7. Category lifecycle

```mermaid
stateDiagram-v2
    [*] --> Deciding: vata_save called with content
    Deciding --> ExistingCategory: caller (or fallback) matches an\nalready-existing category by name
    Deciding --> NewCategory: no match — caller invents a name,\nor fallback picks a keyword-derived one
    NewCategory --> ExistingCategory: category document inserted,\nfirst asset linked via category_id
    ExistingCategory --> ExistingCategory: more assets added (category_id\nset on each new asset directly)
    ExistingCategory --> Renamed: vata_edit_category(new_name=...) —\nnew category_id assigned, all assets\nmoved to it in one update_many
    Renamed --> ExistingCategory
    ExistingCategory --> [*]: vata_delete_category — category AND\nevery asset inside it deleted together
```

Categories are addressable by name in tool calls, but the underlying
`category_id` is what actually links assets — the model doesn't need to
remember or expose raw ids to the user, but does need to pass them (or the
exact name) into edit/delete/list-assets calls.

---

## 8. Deployment topology (as currently live)

```mermaid
flowchart TB
    subgraph LocalDev["This machine"]
        CC[Claude Code\n.mcp.json + ~/.claude.json]
        LocalMongo[(MongoDB Community Server\nlocalhost:27017)]
        CC -- "stdio, no auth" --> LocalServer[vata-mcp process\nvenv/Scripts/python.exe]
        LocalServer --> LocalMongo
    end
    subgraph RenderCloud["Render (free web service)"]
        RemoteServer[vata-mcp\nbranch: mcp, auto-deploy on push]
    end
    subgraph AtlasCloud["MongoDB Atlas (free M0)"]
        AtlasDB[(cluster0 — categories, assets)]
    end
    AnyClient[Any MCP client\ne.g. Claude, attempted: ChatGPT, Windsurf] -- "HTTPS + Bearer VATA_MCP_TOKEN" --> RemoteServer
    RemoteServer --> AtlasDB
```

Two independent, unrelated databases exist right now: the local Mongo
instance (used by local Claude Code sessions) and the Atlas cluster (used
by the deployed Render service). They do not sync — saving locally does
not appear in the remote deployment and vice versa. This is expected
given the current single-database-per-process design, but worth
remembering if data seems "missing" when switching between local and
remote MCP configs.
