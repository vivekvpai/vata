# Vata MCP — Data Flow Diagrams

Companion to [`VATA_MCP_PLAN.md`](VATA_MCP_PLAN.md) and
[`VATA_SCHEMA.md`](VATA_SCHEMA.md). Sequence diagrams for each major flow,
plus one system-level context diagram. Rendered as Mermaid — view in any
Mermaid-capable Markdown viewer (GitHub, VS Code with the Mermaid
extension, etc.).

---

## 1. System context

```mermaid
flowchart LR
    U[User] -->|types /vata-save, /vata-get, /vata-find,\nor natural language| C[Chat Client\nClaude Desktop / Code / Gemini CLI]
    C -->|MCP over Streamable HTTP\nAuthorization: Bearer token| S[vata-mcp server\nRender free web service]
    S -->|reads/writes| M[(MongoDB Atlas\nfree M0 cluster)]
    S -->|LLM calls for category\ndecision + search re-rank| L[LLM Provider\nvia litellm/langchain]
```

---

## 2. `vata_save` flow (AI decides the category — no user input on it)

```mermaid
sequenceDiagram
    actor U as User
    participant C as Chat Client
    participant T as MCP Server (vata_save tool)
    participant AI as ai_service (LLM)
    participant CS as category_service
    participant DB as MongoDB

    U->>C: "/vata-save <content>"
    C->>T: call vata_save(content, summary?, tags?)
    T->>AI: fetch_ai_suggestions(content, summary, tags, existing_categories)
    AI->>DB: list_category_ids() (for context)
    DB-->>AI: [category names]
    AI-->>T: { category, summary, tags }
    alt category is new
        T->>CS: create_category_record(category)
        CS->>DB: insert into categories
    else category exists
        T->>CS: resolve category_id by name
    end
    T->>CS: add_asset_to_category_record(category_id, content, summary, tags)
    CS->>DB: insert into assets
    CS->>DB: insert into category_members (category_id, asset_id)
    CS->>DB: bump categories.updated_at
    T-->>C: { asset_id, category_id, category, message }
    C-->>U: "Saved. Filed under '<category>'."
```

---

## 3. `vata_get` flow (three shapes, one tool)

```mermaid
sequenceDiagram
    actor U as User
    participant C as Chat Client
    participant T as MCP Server (vata_get tool)
    participant CS as category_service
    participant DB as MongoDB

    U->>C: "/vata-get" or "show me that note about X"
    C->>T: call vata_get(asset_id?, category_id?)
    alt no args
        T->>CS: list_categories_record()
        CS->>DB: find categories
        DB-->>CS: [category docs]
        CS-->>T: { categories: [...] }
    else category_id only
        T->>CS: get_category_summary(category_id)
        CS->>DB: find category_members where category_id = ?
        CS->>DB: find assets where _id in [...]
        DB-->>CS: asset summaries
        CS-->>T: { count, items }
    else asset_id given
        T->>CS: get_category_record-equivalent lookup by asset_id
        CS->>DB: find asset by _id
        CS->>DB: find category_members where asset_id = ?
        DB-->>CS: full asset + categories
        CS-->>T: { asset_id, main_content, summary, tags, categories }
    end
    T-->>C: result
    C-->>U: rendered content
```

---

## 4. `vata_find` flow (BM25 pre-filter + LLM re-rank, two passes)

```mermaid
sequenceDiagram
    actor U as User
    participant C as Chat Client
    participant T as MCP Server (vata_find tool)
    participant DS as decision_service
    participant DB as MongoDB
    participant LLM as LLM Provider

    U->>C: "/vata-find <query>" or "what did I save about X?"
    C->>T: call vata_find(query)
    T->>DS: evaluate_nodes_for_query(query)
    DS->>DB: load all categories + aggregated member text
    Note over DS: Pass 1 — BM25 score categories against query
    DS->>LLM: confirm/expand top-K BM25 categories
    LLM-->>DS: relevant_category_ids
    loop for each relevant category
        DS->>DB: load member assets' index text
        Note over DS: Pass 2 — BM25 score assets within category
        DS->>LLM: re-rank top-K assets, ask for match reasons
        LLM-->>DS: [{asset_id, reason}, ...]
    end
    DS-->>T: { count, data: [ranked results] }
    T-->>C: results
    C-->>U: ranked list with reasons
```

---

## 5. Destructive flow — `vata_delete_asset` (confirm-gated)

```mermaid
sequenceDiagram
    actor U as User
    participant C as Chat Client
    participant T as MCP Server
    participant CS as category_service
    participant DB as MongoDB

    U->>C: "delete that asset"
    C->>T: call vata_delete_asset(category_id, asset_id, confirm: true)
    Note over T: schema requires confirm: true literal —\ncall fails validation without it
    T->>CS: delete_asset_from_record(category_id, asset_id)
    CS->>DB: remove category_members row
    CS->>DB: find remaining categories for asset_id
    alt asset now orphaned (zero categories)
        CS->>DB: delete asset document
    else asset still linked elsewhere
        CS->>DB: no-op on assets collection
    end
    CS->>DB: bump categories.updated_at
    CS-->>T: { message, hard_deleted }
    T-->>C: confirmation
    C-->>U: "Deleted."
```

---

## 6. Category lifecycle (why this stays invisible to the user)

```mermaid
stateDiagram-v2
    [*] --> NoCategory: asset content arrives via vata_save
    NoCategory --> AIMatching: ai_service scores content against existing categories
    AIMatching --> ExistingCategory: AI finds a fit
    AIMatching --> NewCategory: AI finds no fit
    NewCategory --> ExistingCategory: category created, asset linked
    ExistingCategory --> ExistingCategory: more assets added over time
    ExistingCategory --> Merged: vata_rename_category / future dedup pass\n(AI-only maintenance, not user-facing)
    Merged --> ExistingCategory
```

The user only ever sees asset-level results (`vata_find` results,
`vata_get` by `asset_id`). `category_id` values surface in tool
outputs for the *model's* bookkeeping (e.g. to call `vata_delete_asset`
correctly) — they aren't something the user should need to type or
remember.

---

## 7. Deployment/request path (hosting view)

```mermaid
flowchart TB
    subgraph Local["Your machine"]
        CD[Claude Desktop / Code config]
    end
    subgraph Render["Render (free web service)"]
        APP[vata-mcp ASGI app]
    end
    subgraph Atlas["MongoDB Atlas (free M0)"]
        COL[(assets / categories / category_members)]
    end
    CD -- "1. HTTPS + Bearer token" --> APP
    APP -- "2. driver connection\n(pymongo/motor, MONGODB_URI)" --> COL
    APP -- "3. LLM API call\n(litellm, API key from env)" --> LLM[LLM Provider]
    APP -- "4. JSON-RPC response\nover MCP" --> CD
```
