# ADR 001: Transcription approach

## Status

Accepted

## Context

Meeting input may be raw audio or already-transcribed text. Production systems need reliable transcription with speaker separation for attribution.

## Decision

- **Primary**: OpenAI Whisper (or compatible API) for audio → text; configurable via `TranscriptionService` and environment.
- **Text path**: Accept pre-transcribed strings and run the same parser for speaker heuristics (`Speaker N:` lines).
- **Mocks**: Default development uses a mock transcription client so CI and local runs need no API keys; latency and cost fields are still populated for observability.

## Consequences

- Swapping providers is an integration change behind `TranscriptionService`, not route handlers.
- Tests use mocks exclusively; production must set env vars and validate Whisper quotas.

## Alternatives considered

- **Cloud-only proprietary STT**: vendor lock-in; deferred.
- **Local Whisper**: lower latency cost but heavier ops; optional future path.
