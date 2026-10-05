# AI Editorial Clipper

> An AI-assisted long-form → short-form content engine that discovers promising moments, creates editable first-draft vertical clips, and lets creators override every important decision before export.

## 1. Product Goal

The product is **not** a generic "paste a YouTube URL and get one viral clip" tool.

The system should behave like an **assistant editor**:

1. ingest long-form creator content,
2. understand the media across text, audio, and video,
3. discover several candidate moments,
4. resolve natural clip boundaries,
5. rank and diversify the candidates,
6. create an editable AI-generated edit plan,
7. render ready-to-post vertical clips,
8. let the creator modify the clip in an in-built editor,
9. learn from what the creator accepts, rejects, and changes.

The system must **estimate attention potential**, not claim that it can guarantee virality.

---

## 2. Core Product Loop

```text
YouTube / Upload
      │
      ▼
Ingest + normalize media
      │
      ▼
Build multimodal media index
      │
      ▼
Generate candidate moments
      │
      ▼
Resolve natural start/end boundaries
      │
      ▼
Rank + deduplicate + diversify
      │
      ▼
Top K clip proposals
      │
      ▼
Generate Edit Decision List (EDL)
      │
      ├──────────────► Auto preview / ready-to-post version
      │
      └──────────────► In-built editor
                             │
                             ▼
                        User changes EDL
                             │
                             ▼
                           Render
                             │
                             ▼
                           Export
                             │
                             ▼
                    Feedback / learning data
```

---

## 3. Fundamental Architecture

The application is organized around four logical planes.

### A. Perception Plane
Build a timestamp-aligned representation of the source video.

Signals may include:

- word-level transcript,
- speaker turns,
- silence / speech density,
- audio energy,
- laughter / reactions / music,
- scene boundaries,
- visual motion,
- faces / active speaker,
- OCR,
- lightweight visual embeddings,
- game / tutorial / screen-recording cues where available.

The output is a reusable **Media Intelligence Index**.

### B. Editorial Intelligence Plane
Use the media index to:

- propose interesting events,
- determine required context,
- find natural beginnings and endings,
- reject incomplete clips,
- score interpretable qualities,
- rank candidates relative to each other,
- remove near-duplicates,
- select a diverse final set.

### C. Editing Plane
Convert each selected raw clip into an **Edit Decision List (EDL)**.

The EDL, not the final MP4, is the source of truth for:

- trims,
- cuts,
- crop/reframe,
- zoom events,
- caption style,
- highlighted words,
- layout,
- effects,
- optional B-roll/music hooks.

### D. Learning Plane
Capture creator decisions:

- clip accepted/rejected,
- boundary changes,
- cut changes,
- crop/zoom changes,
- caption changes,
- exported vs discarded,
- optional post-publication analytics later.

This data will eventually drive creator-specific ranking and editing preferences.

---

## 4. Important Product Principles

### 4.1 Analysis once, reuse many times
Do not re-run transcription, vision analysis, or candidate generation because the user changed a subtitle style.

All expensive intermediate artifacts must be cacheable and versioned.

### 4.2 Candidate generation and editing are separate problems
A good moment can have a bad edit.
A mediocre moment can have a flashy edit.

Do not collapse both into one `virality_score`.

### 4.3 Ranking, not absolute virality regression
The system should become good at:

> "Candidate A is more useful than Candidate B for this creator/video."

before trying to predict a universal 0–100 virality number.

### 4.4 Natural boundaries are a dedicated stage
Never use a fixed `event ± N seconds` rule as the final clip.

The system should separately resolve:

- minimum required setup,
- core event,
- payoff/reaction,
- complete ending.

### 4.5 Human control is part of the architecture
The editor is not a fallback.

It is the control surface for the AI-generated EDL and a future source of preference data.

### 4.6 No premature fine-tuning
Start with strong baselines, existing models, heuristics, and explicit evaluation.

Fine-tune only after reliable labels exist.

---

## 5. MVP Target

The first commercial-quality MVP is aimed at **individual creators**.

### Supported in first MVP

- YouTube URL input
- optional local upload
- English-first
- long-form input up to ~2–3 hours
- podcasts / interviews / talking-head / creator streams with speech
- word-level transcription
- multimodal candidate discovery
- 5 recommended clip candidates
- boundary refinement
- vertical 9:16 output
- automatic captions
- basic speaker-aware reframing
- basic AI editing presets
- in-built editor
- final H.264/AAC export
- creator accept/reject/edit telemetry

### Explicitly postponed

- autonomous internet-wide YouTube crawling
- Twitch live clipping
- movie/copyright-oriented clipping workflows
- full generative B-roll
- autonomous publishing to every platform
- multilingual dubbing
- complex multi-camera cinematic editing
- model fine-tuning before baseline validation

---

## 6. Versioned Build Plan

The build is intentionally split into versions. **Do not skip version gates.**

### Version 0 — Project Skeleton + Contracts

Goal: establish clean interfaces before implementing AI.

Build:

- FastAPI service
- PostgreSQL schema
- Redis-backed job queue
- object/artifact storage abstraction
- job state model
- source / project / artifact / candidate / EDL models
- structured logging
- deterministic artifact paths
- config + environment handling
- Docker setup
- basic health endpoints

Required output:

```text
POST /projects
POST /sources
POST /jobs/analyze
GET  /jobs/{id}
GET  /projects/{id}
```

Exit criteria:

- job can be created,
- job state survives restart,
- artifacts are addressable,
- pipeline stages can be executed independently.

---

### Version 0.1 — Ingestion + Canonical Media

Goal: reliably turn a source URL/upload into normalized media assets.

Build:

- YouTube ingestion through `yt-dlp`,
- upload path,
- FFprobe metadata extraction,
- audio extraction,
- normalized proxy generation,
- source checksum,
- resumable/cached artifacts.

Artifacts:

```text
source.json
source.mp4
audio.wav
proxy.mp4
```

Exit criteria:

- 30 min, 1 hour, and 2 hour videos ingest successfully,
- rerunning ingestion does not redownload/reprocess identical assets.

---

### Version 0.2 — Transcript + Media Intelligence Index v1

Goal: create the first timestamp-aligned source representation.

Build:

- faster-whisper transcription,
- word-level timestamps,
- silence regions,
- speech rate,
- audio energy,
- basic scene boundaries,
- face detections on sampled frames,
- lightweight motion score.

Primary artifact:

```text
media_index.json
```

Suggested event shape:

```json
{
  "start": 120.4,
  "end": 124.8,
  "transcript": "...",
  "speaker": null,
  "audio_energy": 0.72,
  "speech_rate": 168,
  "scene_id": 14,
  "motion_score": 0.31,
  "faces": []
}
```

Exit criteria:

- all signals use the same source timebase,
- index can be queried by time range,
- index is cached and versioned.

---

### Version 0.3 — Candidate Discovery Baseline

Goal: find potentially useful moments without trying to edit them.

Build multiple proposal strategies:

- semantic surprise / strong statement,
- question → answer,
- story / confession,
- high information density,
- emotional change,
- laughter / reaction spike,
- audio-energy spike.

Merge proposals into a candidate pool.

Candidate output:

```json
{
  "candidate_id": "cand_...",
  "event_start": 812.2,
  "event_end": 824.7,
  "source": ["semantic", "audio"],
  "reason_codes": ["contrarian_claim", "energy_spike"]
}
```

Exit criteria:

- system can produce ~15–40 candidates from a typical long video,
- candidates have interpretable reasons,
- no final "virality score" required.

---

### Version 0.4 — Context Expander + Boundary Resolver + Quality Gates

Goal: turn raw events into coherent clip ranges.

Build:

- backward context search,
- forward payoff search,
- sentence boundary alignment,
- silence-aware trim,
- natural-ending resolver,
- clip completeness validator.

Hard reject conditions:

- ends mid-sentence,
- unresolved setup,
- missing obvious payoff,
- duplicated/irrelevant context,
- duration exceeds configured bounds without justification.

Exit criteria:

- candidate clips feel self-contained in blind review,
- boundary resolver is separately testable.

---

### Version 0.5 — Ranking + Diversity

Goal: return the best **set** of clips, not five copies of the same moment.

Represent each candidate with interpretable dimensions:

- hook strength,
- completeness,
- payoff,
- novelty,
- emotional intensity,
- information/value density,
- creator fit placeholder,
- context dependency / retention risk.

Then:

1. rank candidates relative to one another,
2. detect semantic overlap,
3. suppress duplicates,
4. return a diverse Top K (default 5).

Exit criteria:

- Top 5 does not contain overlapping timestamp variants,
- creator reviewers consider at least 3/5 suggestions worth inspecting.

---

### Version 0.6 — Edit Decision List + Auto Editing v1

Goal: convert a selected clip into a structured, editable first draft.

Create EDL schema for:

- source range,
- trim/cut events,
- layout,
- crop path,
- zoom events,
- caption blocks,
- highlighted words,
- style preset,
- effects.

Example:

```json
{
  "source_start": 812.2,
  "source_end": 854.0,
  "layout": "single_speaker_vertical",
  "cuts": [
    {"start": 14.8, "end": 15.7, "reason": "dead_air"}
  ],
  "zoom_events": [
    {"at": 8.3, "scale": 1.12}
  ],
  "captions": {
    "preset": "clean",
    "highlight_words": ["impossible", "three days"]
  }
}
```

Exit criteria:

- renderer consumes EDL without AI dependencies,
- edit changes do not require re-analysis,
- generated clip is watchable without manual intervention.

---

### Version 0.7 — Built-in Editor

Goal: make every important AI decision directly editable.

Minimum controls:

- clip start/end,
- remove/restore cut,
- caption text,
- caption style,
- crop position,
- zoom intensity,
- layout preset,
- reset individual AI change,
- export preview/final.

Store:

```text
original_edl
current_edl
diff / edit events
```

Exit criteria:

- creator can fix a bad AI decision without rerunning the pipeline,
- every user change is logged as structured feedback.

---

### Version 1 — Creator MVP

Goal: test real creator utility.

Flow:

```text
Paste URL
→ analyze
→ receive 5 clips
→ preview
→ edit if required
→ export
```

Primary product metrics:

```text
Top5UsableRate
ExportRate
MajorEditRate
TimeToFirstUsableClip
ManualTimeSaved
```

Target validation gates:

- >= 60% of Top 5 recommendations judged usable/worth clipping,
- meaningful reduction in creator editing time,
- repeat usage from beta creators.

Do not proceed to heavy model fine-tuning before these gates are met.

---

### Version 2 — Creator Personalization

Goal: learn creator-specific preferences.

Use feedback including:

- accepted vs rejected candidates,
- final duration,
- boundary corrections,
- editing intensity,
- caption choice,
- zoom/crop changes,
- exported clip type.

Introduce:

```text
creator_profile
creator_preference_features
pairwise_candidate_preferences
pairwise_edit_preferences
```

Ranking becomes creator-aware.

---

### Version 3 — Twitch / Stream Intelligence

Goal: support long VODs and event-heavy content.

Add:

- Twitch VOD ingestion,
- chat timeline when available,
- game/category metadata,
- stronger visual event detectors,
- gameplay/reaction experts,
- game-aware layouts,
- multi-signal candidate generation.

Do not reuse podcast heuristics unchanged.

---

### Version 4 — Large-Scale Discovery / B2B

Goal: optionally evolve from "creator uploads their content" to a broader discovery engine.

Potential capabilities:

- channel-level monitoring,
- bulk agency workflows,
- scheduled analysis,
- candidate discovery across a creator library,
- APIs/webhooks,
- review queues.

Any public-web discovery/republication workflow must be designed around platform terms, rights, and creator permissions.

---

## 7. Suggested Repository Structure

```text
ai-editorial-clipper/
├── apps/
│   ├── api/
│   └── web/
├── services/
│   ├── ingestion/
│   ├── transcription/
│   ├── media_index/
│   ├── candidates/
│   ├── boundaries/
│   ├── ranking/
│   ├── edit_policy/
│   └── rendering/
├── workers/
│   ├── cpu/
│   └── gpu/
├── domain/
│   ├── models/
│   ├── schemas/
│   └── events/
├── storage/
├── migrations/
├── tests/
│   ├── fixtures/
│   ├── unit/
│   └── integration/
├── docs/
│   └── ANTIGRAVITY_BUILD_CONTEXT.md
├── docker/
├── .env.example
├── docker-compose.yml
└── README.md
```

A modular monolith with workers is preferred initially. Do not split each module into a network microservice until scale or ownership requires it.

---

## 8. Suggested Starting Stack

| Concern | Initial choice |
|---|---|
| API | FastAPI |
| DB | PostgreSQL |
| Queue | Celery + Redis initially |
| Durable artifacts | S3-compatible storage / local adapter for development |
| Video/audio | FFmpeg / FFprobe |
| ASR | faster-whisper |
| Basic CV | OpenCV + replaceable detectors |
| AI reasoning | provider/model adapter; no hard coupling |
| Rendering | FFmpeg |
| Web editor | React |
| Canonical edit representation | JSON EDL |
| Containerization | Docker / Docker Compose |

All model/provider calls must sit behind interfaces so they can be replaced.

---

## 9. Evaluation Before Optimization

Build a fixed benchmark set early.

For each source video store:

- human-selected useful moments,
- acceptable boundary ranges,
- rejected moments,
- preferred candidate ordering,
- optional preferred edit.

Minimum offline metrics:

```text
CandidateRecall
Precision@5
BoundaryStartError
BoundaryEndError
DuplicateRate@5
ClipCompletenessRate
```

Product metrics:

```text
Top5UsableRate
ExportRate
ManualAdjustmentRate
TimeSaved
RepeatUsage
```

Never optimize infrastructure cost before validating clip quality.

---

## 10. Hard Rules for Contributors / Coding Agents

1. Do not introduce a universal `virality_score` as the core abstraction.
2. Do not combine candidate discovery, boundary resolution, ranking, and editing in one model call.
3. Do not make MP4 output the only representation of an edit.
4. Do not rerun expensive perception stages after simple edit changes.
5. Do not add Twitch/live/global crawling before creator MVP quality is validated.
6. Do not fine-tune a custom model before a strong labeled evaluation set exists.
7. Every pipeline stage must accept and produce explicit typed artifacts.
8. Every expensive artifact must have a cache/version key.
9. Every AI decision that affects the final video should be editable or regenerable independently.
10. Keep the pipeline observable: stage timings, failures, artifact versions, model versions, and reasons for candidate selection must be logged.

---

## 11. Immediate Next Step

Start **Version 0 only**.

Do not implement candidate AI yet.

The first engineering milestone is:

```text
create project
→ ingest source
→ persist job state
→ persist normalized artifact metadata
→ rerun safely
```

Once Version 0 passes its acceptance criteria, proceed to Version 0.1.
