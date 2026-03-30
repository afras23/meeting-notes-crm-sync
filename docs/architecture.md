# Architecture

## System context

The service exposes a versioned HTTP API (`/api/v1`) that accepts meeting audio or text, runs an async processing pipeline, persists structured results, and optionally updates a CRM and sends notifications.

## Component diagram

```mermaid
flowchart TB
  subgraph clients [Clients]
    U[Uploader / integrator]
  end

  subgraph api [FastAPI]
    R1[POST /process]
    R2[GET /meetings]
    R3[GET /actions]
    R4[GET /health]
  end

  subgraph services [Services]
    TS[TranscriptionService]
    ES[ExtractionService]
    CS[CRMService]
    NS[NotificationService]
    PS[MeetingProcessService]
  end

  subgraph integrations [Integrations]
    W[Whisper / mock]
    LLM[AIClient LLM mock]
    HS[HubSpot mock]
    SL[Slack mock]
    CAL[Calendar mock]
  end

  subgraph data [Data]
    DB[(PostgreSQL / SQLite)]
    AR[AuditRepository]
    MR[MeetingRepository]
    AIR[ActionItemRepository]
  end

  U --> R1
  R1 --> PS
  PS --> TS
  TS --> W
  PS --> ES
  ES --> LLM
  ES --> AR
  PS --> CS
  CS --> HS
  PS --> NS
  NS --> SL
  PS --> MR
  PS --> AIR
  R2 --> MR
  R3 --> AIR
  PS --> DB
  MR --> DB
  AIR --> DB
  R4 --> DB
  R4 --> LLM
```

## Request flow (process)

```mermaid
sequenceDiagram
  participant C as Client
  participant P as Process route
  participant T as TranscriptionService
  participant E as ExtractionService
  participant CRM as CRMService
  participant N as NotificationService
  participant DB as Database

  C->>P: audio or JSON text
  P->>T: transcribe / parse
  T-->>P: transcript + ParsedTranscript
  P->>E: extract_meeting
  E->>E: validate transcript, audit dedupe by hash
  E-->>P: Meeting + extraction
  P->>CRM: apply_updates (diff vs HubSpot snapshot)
  CRM-->>P: changed_properties, skipped
  P->>N: notify_meeting_events
  P->>DB: upsert meeting, actions, audit
  P-->>C: 202 + meeting_id
```

## Diff detection (CRM)

1. Load `config/crm_mapping.yaml` for the configured CRM key (e.g. `hubspot`).
2. Build **desired** deal fields from meeting JSON via each field’s `source` path.
3. Load **current** deal from `HubSpotClientMock.get_deal(deal_id)`.
4. `_diff_properties`: emit `changed` only where `current[key] != desired[key]`; skip `None` desired values.
5. If `changed` non-empty: `update_deal` with **only** `changed`, then attach a note. Retries use exponential backoff + jitter.

## Meeting series

`compute_meeting_series_id(deal_id, project_id)` derives a stable series id so related meetings can be listed and filtered by `deal_id` on `/meetings`.

## Non-functional

- **Correlation ID**: middleware attaches `X-Correlation-ID` for tracing.
- **Rate limiting**: configurable RPM on HTTP layer.
- **AI**: daily cost cap, timeout, retries with jitter on `TimeoutError`, circuit breaker on consecutive failures.
- **Lifespan**: DB engine disposed on shutdown.
