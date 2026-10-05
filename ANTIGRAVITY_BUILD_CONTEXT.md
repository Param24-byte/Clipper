# Antigravity Build Context — AI Editorial Clipper

## Purpose of This File

This file is the **initial understanding / source-of-truth context** for an AI coding agent (Antigravity or equivalent) before implementation begins.

Read this file before making architectural decisions.

If implementation code conflicts with this document, prefer the intent in this document unless the user explicitly changes the requirement.

---

# 1. Problem Definition

We are building an AI-assisted system that converts long-form creator content into multiple editable short-form clips.

The core problem is **not**:

> "Predict whether a clip will go viral."

The core problem is:

> Given a long-form audiovisual source, identify a small set of moments with strong attention potential, convert them into coherent short-form stories, create high-quality first-draft edits, and let a human creator modify every important decision efficiently.

The product should reduce the work of a creator/editor from:

```text
watch entire video
→ manually find moments
→ trim
→ reframe
→ caption
→ edit
→ render
```

to:

```text
submit source
→ review suggested clips
→ optionally adjust
→ export
```

---

# 2. Initial Target User

Primary initial target:

- individual creators,
- podcasters,
- interview channels,
- long-form YouTubers,
- streamers with speech-heavy VODs.

Secondary later targets:

- editing agencies,
- creator teams,
- high-volume content operations.

Large-scale public-content discovery is **not** the first build target.

---

# 3. Product Boundary for the First Build

## In scope

- YouTube URL ingestion,
- optional file upload,
- long-form video,
- English-first,
- transcript generation,
- cheap multimodal media analysis,
- candidate moment generation,
- boundary refinement,
- ranking,
- duplicate suppression,
- Top K recommendations,
- vertical auto-editing,
- captions,
- basic reframing,
- structured edit plan,
- in-built editor,
- export.

## Not in scope initially

- guaranteed virality prediction,
- automatic public-web crawling,
- movies/copyright clipping,
- Twitch live processing,
- autonomous social publishing,
- complex generative video/B-roll,
- model training from scratch,
- early custom LLM fine-tuning,
- dozens of microservices.

---

# 4. Architectural Mental Model

The system has four planes:

```text
PERCEPTION
    ↓
EDITORIAL INTELLIGENCE
    ↓
EDITING / COMPOSITION
    ↓
LEARNING
```

The system should not be architected around "the LLM".

Models are replaceable workers inside the architecture.

---

# 5. Canonical Data Flow

```text
SOURCE
  │
  ▼
INGESTION
  │
  ├── source metadata
  ├── canonical media
  ├── audio
  └── proxy
  │
  ▼
MEDIA INTELLIGENCE INDEX
  │
  ├── transcript
  ├── audio signals
  ├── scene boundaries
  ├── motion
  ├── faces
  └── other time-aligned observations
  │
  ▼
CANDIDATE GENERATORS
  │
  ▼
CANDIDATE POOL
  │
  ▼
CONTEXT EXPANDER
  │
  ▼
BOUNDARY RESOLVER
  │
  ▼
QUALITY GATES
  │
  ▼
RANKING
  │
  ▼
DEDUPLICATION / DIVERSITY
  │
  ▼
TOP K CLIPS
  │
  ▼
EDIT POLICY
  │
  ▼
EDL
  │
  ├── automatic preview
  └── user editor
          │
          ▼
      final EDL
          │
          ▼
       renderer
          │
          ▼
        export
          │
          ▼
feedback events
```

---

# 6. Core Domain Objects

Do not start with database tables. Start with domain meaning.

## Project

One creator workflow/session.

```text
Project
- id
- owner_id
- name
- created_at
- status
```

## Source

Original long-form media input.

```text
Source
- id
- project_id
- type: youtube | upload | twitch_vod_later
- uri
- checksum
- duration
- width
- height
- fps
- metadata
```

## Artifact

Any derived, cacheable output.

```text
Artifact
- id
- source_id
- stage
- version
- content_hash
- storage_uri
- metadata
- created_at
```

Examples:

```text
canonical_video
audio_track
proxy_video
transcript
media_index
candidate_set
edl
preview_render
final_render
```

## Observation

A timestamp-aligned perception result.

```text
Observation
- start
- end
- type
- value
- confidence
- producer/version
```

## Candidate

An interesting event proposal before final boundaries.

```text
Candidate
- id
- source_id
- event_start
- event_end
- generator
- reason_codes[]
- evidence[]
```

## ClipProposal

A coherent candidate after context/boundary resolution.

```text
ClipProposal
- id
- candidate_ids[]
- source_start
- source_end
- feature_scores
- rank
- cluster_id
- quality_gate_results
```

## EDL

Canonical representation of the actual edit.

```text
EditDecisionList
- id
- clip_proposal_id
- schema_version
- source_range
- cuts[]
- reframing[]
- zooms[]
- captions
- effects[]
- layout
- audio
```

## FeedbackEvent

Structured human correction / product signal.

```text
FeedbackEvent
- id
- project_id
- clip_proposal_id
- type
- before
- after
- created_at
```

Example types:

```text
candidate_accepted
candidate_rejected
boundary_changed
cut_deleted
crop_changed
caption_changed
zoom_changed
exported
```

---

# 7. Job Model

All long-running operations are jobs.

Recommended initial states:

```text
queued
running
succeeded
failed
cancelled
```

A project pipeline should not be one giant non-resumable task.

Think in stages:

```text
ingest
normalize
transcribe
index
discover_candidates
resolve_boundaries
rank
generate_edl
render_preview
render_final
```

Each stage must:

- be idempotent where possible,
- expose progress,
- record input artifact versions,
- record output artifact versions,
- record model/tool version,
- support retry,
- not silently overwrite unrelated artifacts.

---

# 8. Artifact Versioning

Use explicit semantic stage versions from day one.

Example:

```text
transcript:v1
media_index:v1
candidates:v1
boundaries:v1
ranking:v1
edl:v1
render:v1
```

Cache identity should depend on:

```text
source checksum
+
stage version
+
relevant configuration
+
model/tool version
```

Changing caption font must invalidate render/EDL-related output only, not transcription.

---

# 9. Media Intelligence Index

The media index is the most important foundational artifact.

Initial V1 of the index does **not** need every possible feature.

Minimum:

```text
timeline chunks
word timestamps
sentence timestamps
silence regions
speech-rate estimate
audio energy
scene IDs
motion estimate
sampled face detections
```

Example conceptual shape:

```json
{
  "schema_version": "1",
  "source_id": "src_123",
  "duration": 3782.4,
  "intervals": [
    {
      "start": 10.0,
      "end": 15.0,
      "text": "example",
      "audio_energy": 0.54,
      "speech_rate": 152,
      "scene_id": 2,
      "motion_score": 0.14,
      "face_count": 1
    }
  ]
}
```

Later the index may add:

- speaker diarization,
- OCR,
- active speaker,
- objects,
- semantic embeddings,
- sound events,
- game telemetry,
- chat activity.

Do not make these mandatory for Version 0.x.

---

# 10. Candidate Discovery Philosophy

Avoid one prompt:

> "Find the 5 viral moments."

Instead, allow several weak proposal generators.

Initial examples:

```text
semantic_strong_statement
semantic_question_answer
semantic_story_payoff
audio_energy_spike
laughter_reaction
speech_rate_change
emotion_shift
high_information_density
```

Generators produce **events**, not final clips.

Multiple generators can propose the same region.

Merge overlapping proposals while retaining evidence.

---

# 11. Boundary Resolution Philosophy

Boundary resolution is a dedicated problem.

Given an event:

```text
event_start
event_end
```

find:

```text
source_start
source_end
```

using:

- sentence boundaries,
- setup dependencies,
- silence,
- discourse completion,
- payoff,
- visual continuity.

Reject if coherence cannot be achieved.

A "best clip" must not simply be:

```text
event ± 30s
```

---

# 12. Ranking Philosophy

Do not assume universal virality.

Rank candidates using interpretable features.

Initial candidate feature vector:

```text
hook_strength
completeness
payoff_strength
novelty
emotional_intensity
information_density
context_dependency
visual_interest
audio_interest
```

Later:

```text
creator_fit
platform_fit
historical_performance_fit
```

The long-term problem is closer to pairwise/listwise preference ranking than absolute regression.

---

# 13. Diversity Requirement

Top K must be a useful set.

Near-duplicate timestamp variants are a failure.

After ranking:

1. compute semantic/timestamp overlap,
2. cluster similar candidates,
3. select strongest representative,
4. intentionally preserve variety.

---

# 14. Edit Decision List Is Mandatory

Do not generate the final MP4 as the only editable state.

All AI editing choices must be represented as EDL data.

Minimum EDL v1:

```text
source range
cuts
layout
crop/reframe track
zoom events
captions
highlight words
style preset
```

Renderer input must be:

```text
source artifacts + EDL
```

The editor should edit the EDL, not destructively manipulate an already rendered final file.

---

# 15. User Editor Requirements

The initial editor is intentionally small.

Must support:

```text
change start/end
delete/restore AI cut
edit caption text
change caption preset
adjust crop
adjust zoom
change layout preset
preview
export
```

Do not attempt to build a complete Premiere Pro competitor.

---

# 16. Learning Strategy

## Before creator feedback exists

Use:

- heuristics,
- existing pretrained models,
- prompts/model APIs behind adapters,
- human benchmark evaluation.

## After feedback exists

Train/learn in this order:

1. candidate ranking,
2. boundary preferences,
3. editing preferences,
4. creator personalization.

Do not prioritize a custom 8B fine-tune as the first ML milestone.

---

# 17. Evaluation Set

Create a small benchmark dataset as soon as the first pipeline exists.

For each benchmark source:

```text
source
human useful moments
acceptable start ranges
acceptable end ranges
rejected examples
preferred ordering
```

Do not rely only on screenshots or intuition.

Initial metrics:

```text
CandidateRecall
Precision@5
ClipCompletenessRate
BoundaryStartError
BoundaryEndError
DuplicateRate@5
```

Product metrics later:

```text
Top5UsableRate
ExportRate
MajorEditRate
TimeSaved
RepeatUsage
```

---

# 18. Reliability Requirements

Antigravity should design for:

- retryable jobs,
- partial failure,
- large files,
- corrupt sources,
- missing audio,
- videos with no faces,
- videos with multiple scene layouts,
- model/API timeout,
- FFmpeg failure,
- user cancellation,
- duplicated request,
- worker restart.

No stage should assume "happy path only".

---

# 19. Security / Abuse Basics

At minimum:

- validate input URLs,
- do not shell-concatenate raw user input,
- isolate FFmpeg/yt-dlp command construction,
- enforce file size/duration limits,
- use temp working directories,
- clean temporary files,
- never trust client-provided storage paths,
- rate-limit expensive endpoints,
- do not expose internal artifact paths.

---

# 20. Initial Tech Decisions

Prefer:

```text
Python 3.11+
FastAPI
Pydantic
PostgreSQL
SQLAlchemy / SQLModel
Alembic
Redis
Celery initially
FFmpeg / FFprobe
yt-dlp
faster-whisper
OpenCV
Docker Compose
pytest
```

Frontend can be introduced when Version 0.6/0.7 requires editor work.

Do not hard-code any LLM provider.

Create interfaces such as:

```text
CandidateReasoner
BoundaryReasoner
Ranker
EditPolicy
```

with provider-backed implementations.

---

# 21. Suggested Initial Package Boundaries

```text
src/
├── api/
├── config/
├── domain/
├── db/
├── jobs/
├── storage/
├── media/
│   ├── ingest/
│   ├── ffmpeg/
│   ├── audio/
│   └── video/
├── intelligence/
│   ├── transcript/
│   ├── index/
│   ├── candidates/
│   ├── boundaries/
│   ├── ranking/
│   └── editing/
├── rendering/
└── telemetry/
```

Imports should generally point inward toward domain contracts.

Avoid circular coupling between pipeline stages.

---

# 22. First Implementation Sprint

Implement **only Version 0**.

## Task 1 — repository and runtime

Create:

```text
pyproject.toml
README.md
.env.example
docker-compose.yml
src/
tests/
```

Set up:

- API container,
- PostgreSQL,
- Redis,
- worker container.

## Task 2 — domain models

Implement typed contracts for:

```text
Project
Source
Artifact
Job
```

Do not implement Candidate/EDL behavior beyond schemas yet unless needed for migrations.

## Task 3 — database

Create migrations.

## Task 4 — storage abstraction

Interface:

```python
class ArtifactStore:
    def put(...)
    def get(...)
    def exists(...)
    def delete(...)
```

Development implementation may use local filesystem.
Keep an S3 implementation possible later.

## Task 5 — job execution

Create one test job such as:

```text
probe_source
```

that moves:

```text
queued → running → succeeded
```

and records an artifact/result.

## Task 6 — API

Minimum endpoints:

```text
POST /projects
GET  /projects/{id}

POST /sources
GET  /sources/{id}

POST /jobs/probe
GET  /jobs/{id}

GET /health
```

## Task 7 — tests

Test:

- DB model creation,
- job transitions,
- retry safety,
- artifact store,
- duplicate request behavior.

---

# 23. Version 0 Exit Gate

Do not start AI work until all statements below are true:

```text
[ ] API starts from clean Docker Compose
[ ] PostgreSQL migrations apply cleanly
[ ] Redis/worker is healthy
[ ] project/source records persist
[ ] job state survives API restart
[ ] artifacts have deterministic metadata
[ ] duplicate job invocation is safe
[ ] stage failure is visible and retryable
[ ] unit/integration tests pass
```

Only after that, proceed to **Version 0.1: ingestion**.

---

# 24. Anti-Patterns to Avoid

Do not:

- place all logic in `main.py`,
- let endpoints run FFmpeg synchronously,
- store giant transcript blobs in random columns with no versioning strategy,
- use untyped dictionaries everywhere,
- create a "god service" called `AIService`,
- tightly couple candidate logic to one model vendor,
- write temporary paths into persistent domain objects,
- recompute everything after a tiny edit,
- add Kubernetes before product validation,
- create microservices because the architecture diagram looks cleaner,
- promise "viral" outcomes in code/product copy as a measurable guarantee.

---

# 25. Product Truths to Preserve

When trade-offs arise, preserve these truths:

1. **The system proposes; the creator controls.**
2. **The final clip must be coherent before it is flashy.**
3. **Candidate quality matters more than quantity.**
4. **Top-K diversity matters.**
5. **Editing decisions must be structured and editable.**
6. **Human corrections are future training data.**
7. **The product must save time, not merely demonstrate AI.**
8. **No expensive model is sacred.**
9. **Cacheable media intelligence is more foundational than any single model.**
10. **Build and validate one version at a time.**

---

# 26. Instruction to Antigravity

Begin with Version 0 only.

Before coding:

1. summarize the architecture you intend to implement,
2. list the exact files/directories you will create,
3. identify any deviation from this document,
4. state Version 0 acceptance tests,
5. then implement incrementally.

Do not silently expand scope.

When a decision is ambiguous, prefer the option that:

- keeps stages independently replaceable,
- preserves artifact reuse,
- makes failure observable,
- delays expensive/complex ML,
- preserves future creator-feedback learning.
