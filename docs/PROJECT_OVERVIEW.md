# PROJECT OVERVIEW — Hand-Gesture AR Punching Game (Real-time Inference)

> Context file for coding agents. Read fully before writing code.
> This file records **decisions only**. Items marked **[TBD]** are NOT decided. Do not choose them yourself — ask the user.
> Last updated: 2026-10-26.

---

## 1. Project context

| Item | Value |
|---|---|
| Course | ED4140 — Đồ án VR/AR (HUST) |
| Research topic | Techniques supporting AI models for real-time response in image-sequence processing |
| Product | A "Move Fast"-style punching game: shapes fly toward the player, who hits them with the matching hand and gesture. Controlled by hand gestures from a webcam. |
| Demo platform | PC + single webcam. **No VR headset.** |
| Deadline | January 2027 (end of semester) |
| Validation | Unit tests + technical tests (latency, FPS, accuracy, stability). No user studies. |
| Out of scope | Rehabilitation / medical use cases |

### Scope balance
Both parts matter equally: **real-time AI inference** (the research topic) and the **VR/AR game** (the course is a VR/AR project).
Do not sacrifice one for the other. The game also serves as the measurement vehicle: latency/accuracy improvements should show up in hit rate and play feel.

### External model
- An existing closed-source hand-gesture model will be integrated later ("the external model"). Format, inputs/outputs and gesture set are **unknown**.
- Until then the baseline is **MediaPipe** (Hand Landmarker / Gesture Recognizer).
- The recognizer MUST be swappable without changing game code.

---

## 2. Goals

1. Recognize hands (left/right) and gestures from a webcam stream in real time, including **dynamic gestures** (punches) over frame sequences.
2. Convert per-frame results into stable, discrete strike events (temporal decision logic).
3. Run a playable game (Level 1 at minimum) driven by those events.
4. Optimize and **measure** the full pipeline (webcam → recognition → logic → game), not only model latency.

Success criteria (numbers): **[TBD]**. Current draft: gesture accuracy ≥ 90%, end-to-end latency < 100 ms, pipeline ≥ 25 FPS on the dev machine.

---

## 3. Hardware

- Dev laptop: Acer Aspire 7 A715-76G — i5-12450H — GTX 1650 4 GB — 8 GB RAM
- Primary inference target: **CPU**. GPU for experiments only.
- 8 GB RAM is shared by Unity + Python + IDE: keep memory usage low.

### MediaPipe baseline (measured 2026-10, model time only, CPU)
| Config | Mean | p95 |
|---|---|---|
| Video mode, `num_hands=1` | ~9 ms | 12 ms |
| Video mode, `num_hands=2`, 1 hand in frame | ~28 ms | 42 ms |
| Image mode (no tracking) | ~21 ms | — |

- Built-in static gestures: `Closed_Fist, Open_Palm, Pointing_Up, Thumb_Down, Thumb_Up, Victory, ILoveYou` (+ `None`).
- **No dynamic gestures** (punches must be derived from landmarks over time).
- Accuracy is **not yet validated** (only 4 sample images tested).
- Existing tools in repo: `python/tools/live_test.py` (webcam, flicker/accuracy), `python/tools/eval_dataset.py` (folder of images), `python/punchar/` (pipeline skeleton, see README).

---

## 4. Tech stack — DECIDED

| Part | Choice |
|---|---|
| Capture, recognition, decision logic, metrics | **Python** (OpenCV + MediaPipe) |
| Game + rendering | **Unity** (C#) |
| Link | **UDP on localhost** (`127.0.0.1`), JSON messages, Python → Unity |
| AR background | Phase 1: none (3D scene + 3D hands only). Later: Python sends JPEG frames to Unity as background. |

Team has no prior Unity/VR experience: keep Unity usage basic (primitives, free assets, simple physics/colliders). Fallback engine if Unity blocks progress: Ursina (Python). Only switch with user approval.

---

## 5. System architecture

```
┌────────────────────── Python ──────────────────────┐        ┌────────────── Unity ──────────────┐
│ [1] Capture ─► [2] Recognizer ─► [3] Decision Logic │  UDP   │ [4] Receiver ─► Game logic ─► Render│
│  (thread,       (swappable,        (per-hand state   │ ─────► │  (thread → queue,  (hit check,       │
│   latest frame)  adapters)          machine)         │  JSON  │   read in Update)  score, combo)     │
│                         [5] Metrics (timestamps at every stage, both sides)                       │
└───────────────────────────────────────────────────────────────────────────────────────────────────┘
```

| # | Module | Responsibility |
|---|---|---|
| 1 | Capture | Separate thread. Keep only the latest frame. Record capture timestamp. |
| 2 | Recognizer | Per-frame raw results behind a common interface. One adapter per model. |
| 3 | Decision Logic | All temporal rules (thresholds, velocity, cooldown). Emits strike events. |
| 4 | Unity game | Consumes messages only. Never calls or knows about the model. |
| 5 | Metrics | Timestamps per stage; end-to-end latency via `t` carried in every message. |

### Recognizer output (Python, per frame)

```
FrameResult {
  frame_id: int
  timestamp_ms: int              # capture time
  hands: list[HandResult]        # 0..2
}
HandResult {
  handedness: "Left" | "Right"   # from the PLAYER's point of view (mirroring resolved in Python)
  shape: string                  # "Closed_Fist", "Open_Palm", "None", ...
  score: float                   # 0..1
  landmarks: list[21 x (x, y, z)]       # normalized 0..1 image coords
  world_landmarks: list[21 x (x, y, z)] # meters
}
Recognizer (interface) { load(); predict(frame) -> FrameResult; close() }
```

Implementations: `MediaPipeRecognizer` (baseline), `ExternalModelRecognizer` (later), `ReplayRecognizer` (plays back recorded `FrameResult` files for tests and for game dev without a webcam).

### UDP messages (Python → Unity)

```json
{"type": "pose", "t": 1234567, "hands": [
  {"hand": "Left", "x": 0.32, "y": 0.55, "shape": "Closed_Fist"}
]}
{"type": "strike", "t": 1234600, "hand": "Left", "kind": "PUNCH_STRAIGHT", "x": 0.30, "y": 0.52}
{"type": "hand_lost", "t": 1234700, "hand": "Right"}
```

- `pose`: every processed frame; Unity moves the 3D hands.
- `strike`: only when decision logic confirms a strike. `kind` ∈ `PUNCH_STRAIGHT`, `BLOCK`, `OPEN_PALM`, `HOOK` (optional).
- `t`: capture timestamp of the source frame (ms, same clock both sides) → end-to-end latency.
- Coordinates: normalized 0..1, already mirrored so the player's left hand appears on the left of the screen.
- The message format is a contract: change it only with user approval.

---

## 6. Gestures and decision logic

Rule: **the side the shape comes from = the hand that must hit it.**

| Gesture | Status | Detection approach (initial) |
|---|---|---|
| Straight punch | Decided | Fist shape + fast increase of hand size in image (and/or landmark `z`) within a short window |
| Block ("đấm thủ") | Decided | Exact pose **[TBD]** |
| Open palm | Decided | `Open_Palm` shape; game meaning **[TBD]** |
| Hook | Optional | Fist + strong horizontal velocity toward center |

Decision logic (in Python, module [3]):
- Per-hand **state machine**: `IDLE → WINDUP → STRIKE (emit event) → COOLDOWN → IDLE`.
- Gesture acceptance thresholds: shape confidence, velocity/displacement normalized by hand size, per-hand cooldown.
- All time parameters in **ms** (not frame counts). All parameters in a config file.
- Must handle motion blur / brief tracking loss during a punch.
- Report two latency types separately: **system latency** (machines) and **design latency** (intentional waiting to confirm a gesture).

---

## 7. Game design — DECIDED

Reference: Move Fast (https://youtu.be/p1DniSBv85E?t=173).

- A **launcher** fires **shapes** toward the player along a lane, on the level's own schedule.
- Each shape is on the **left or right** and shows (by shape/color) the **gesture required**.
- Correct hand + correct gesture while the shape is in the **hit zone** → hit: score, combo, multiplier, break effect.
- Wrong hand, wrong gesture, or shape passes the hit zone → miss, combo reset.
- The **hit zone width** must compensate end-to-end latency; it is a config value and a key link between inference results and game feel.
- **Levels:** Level 1 first and complete. Later levels: faster/denser shapes, more gesture types.
- **Scoring:** score, combo, multiplier; local top score / leaderboard; unlock next level by score.
- **Audio:** background music only, **not** synced to the beat (not a rhythm game) + hit/miss sounds.
- **Visuals:** vivid, harmonious colors, clear layout (lane in center, score/combo panel, progress bar).
- **3D content list:** hands, launcher, flying shapes, "reflection" (meaning **[TBD]**), surroundings, animations, effects. Use primitives / free assets first.
- **Debug mode** (one key): show skeleton, gesture labels, per-stage latency, FPS. Used to demo the inference work.
- Game must also accept **keyboard input** that emits fake `strike` events, for development without the recognizer.

Build order inside the game: Level 1 playable with primitives → hit/miss + score → debug mode → 3D art, effects, leaderboard/unlock → extra levels.

---

## 8. Inference & performance

MediaPipe model time is already small (~9 ms). Optimization work targets the **whole pipeline**:

1. **Two-hand tracking cost** (~9 → ~28 ms when `num_hands=2`): the game requires both hands.
2. **Dynamic gesture detection on sequences**: detect punches as **early** as possible without false triggers; handle blur and tracking loss.
3. **Latency outside the model**: webcam (exposure, buffering, MJPG, FPS), decision waiting, UDP, Unity render. Measure each stage, then reduce the biggest.
4. **Latency compensation**: hand trajectory prediction (One Euro / Kalman) between recognitions.
5. **Running alongside the game under limited resources**: inference never blocks rendering; adaptive quality (resolution, frame skip, hand count) under load.
6. **External model**: ONNX Runtime / OpenVINO / FP16 / INT8 when it arrives.

Required metrics: end-to-end latency, per-stage latency, p50/p95/p99 + jitter, FPS, CPU %/RAM, accuracy (frame level and strike level), false triggers per minute, in-game hit rate.

Every technique: measure **before / after** with the same recorded videos (`benchmark.py`, not live webcam).
Weak-device simulation: limit cores (`taskset`), power-saver mode, lower camera resolution.

---

## 9. Rules for coding agents

1. Game code never depends on a specific model. Unity consumes UDP messages only.
2. All thresholds, durations, cooldowns, resolutions, ports → config files, not hard-coded.
3. Every stage logs timestamps; every message carries `t`.
4. Keep CPU and memory usage low; ask before adding heavy dependencies.
5. Unit-test decision logic with recorded / synthetic `FrameResult` sequences.
6. Do not decide **[TBD]** items. Ask the user.
7. Keep code simple and modular, short docstrings. Unity code must stay beginner-readable.

---

## 10. Open decisions

- [ ] Exact pose for "block"; game meaning of "open palm"
- [ ] Meaning of "reflection" in the 3D content list
- [ ] Success-criteria numbers and how to measure them
- [ ] Benchmark machine and shared evaluation dataset
- [ ] External model format, gesture set, delivery date
- [ ] Names for Person 2 and Person 3 (task split approved 2026-10-26, see `PHAN_CONG.vi.md`; Person 1 = the user)
- [ ] How the game is delivered (build .exe vs. run from editor)
