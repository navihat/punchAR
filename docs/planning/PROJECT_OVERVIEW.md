# PROJECT OVERVIEW — Hand-Gesture AR Punching Game (Real-time Inference)

> Context file for coding agents. Read fully before writing code, together with [`AGENTS.md`](../../AGENTS.md).
> This file records **decisions only**. Items marked **[TBD]** are NOT decided. Do not choose them yourself — ask the user.
> Synced with [`PROJECT_OVERVIEW.vi.md`](PROJECT_OVERVIEW.vi.md) on 2026-11-27. If either conflicts with [`DECISIONS.md`](../decisions/DECISIONS.md), `DECISIONS.md` wins.

---

## 1. Project context

| Item | Value |
|---|---|
| Course | ED4140 — Đồ án VR/AR (HUST) |
| Research topic | Techniques supporting AI models for real-time response in image-sequence processing |
| Product | A "Move Fast"-style punching game: shapes fly toward the player, who hits them with the matching hand and gesture. Controlled by hand gestures from a webcam, 3D objects overlaid on the webcam image (AR). |
| Demo platform | PC + single webcam. **No VR headset.** |
| Deadline | Demo mid-January 2027 (milestone M4: 2027-01-10) |
| Team | Thái (pipeline + AR), Duy (hand gestures), Thảo (gameplay) — see [`PHAN_CONG.vi.md`](../team/PHAN_CONG.vi.md) |
| Validation | Unit tests + technical tests (latency, FPS, accuracy, stability). No user studies. |
| Out of scope | Rehabilitation / medical use; the closed-source external model (dropped 2026-11-16, together with ONNX / quantization; if revived, only after M3 on 2026-12-27) |

### Grading focus
The focus is **real-time techniques**: latency, FPS, recognition accuracy and stability. The game is the vehicle that proves them: improvements should show up in hit rate and play feel.

### Model
- **MediaPipe Gesture Recognizer** on CPU (`models/gesture_recognizer.task`).
- Built-in static shapes: `Closed_Fist, Open_Palm, Pointing_Up, Thumb_Down, Thumb_Up, Victory, ILoveYou` (+ `None`), 21 landmarks per hand, handedness.
- **No dynamic gestures**: strikes are derived from landmarks over time in Decision Logic (§6).
- The recognizer stays swappable via `python/punchar/recognizer/base.py` without changing game code.

---

## 2. Goals

1. Recognize hands (left/right) and gestures from a webcam stream in real time, including **dynamic gestures** (punches) over frame sequences.
2. Convert per-frame results into stable, discrete strike events (temporal decision logic).
3. Run a playable game (Level 1 at minimum) driven by those events, on an AR webcam background.
4. Optimize and **measure** the full pipeline (webcam → recognition → logic → game), not only model latency.

Targets used by the sprint plan: accuracy ≥ 90% on the team's strike dataset, end-to-end latency < 100 ms, pipeline ≥ 25 FPS on the benchmark machine. **[TBD]**: whether accuracy is per frame or per strike, and the recording conditions.

---

## 3. Hardware and measurements

- **Benchmark machine:** Acer Aspire 7 A715-76G — i5-12450H — GTX 1650 4 GB — 8 GB RAM. All reported numbers come from this machine.
- Inference on **CPU**. GPU for experiments only. 8 GB RAM is shared by Unity + Python + IDE: keep memory usage low.

**Model-only, 2026-10:** video mode `num_hands=1` ~9 ms (p95 12); `num_hands=2` with 1 hand in frame ~28 ms (p95 42); image mode ~21 ms.

**Pipeline baseline, 2026-11-22** (`python -m punchar.main`, live webcam 1280×720 MJPG, 2 hands; details in [sprint-01.md](../sprints/sprint-01.md) "Review"):

| `recognize` p50 / p95 / p99 | `since_capture` p50 / p95 / p99 | FPS |
|---|---|---|
| 20.4 / 30.7 / 39.6 ms | 22.1 / 33.1 / 43.4 ms | ≈ 30 (webcam limit; model allows ~45) |

Before MJPG the webcam delivered only 10 FPS at 720p. Not yet measured: `benchmark.py` on recorded video, real end-to-end latency, strike accuracy.

---

## 4. Tech stack — DECIDED (2026-11-16)

| Part | Choice |
|---|---|
| Capture, recognition, decision logic, metrics | **Python 3.12**: OpenCV, MediaPipe (CPU), numpy, pytest; env via `uv` |
| Game, rendering, AR | **Unity 6000.6.4f1**, URP, C#, Input System |
| Link | **UDP** `127.0.0.1:5005`, one JSON object per packet, Python → Unity only |
| Parameters | `python/config/default.toml`, all times in **ms** |
| AR background | Webcam image as background in Unity (Sprint 3). Transport **[TBD]**: Python owns the camera, so Unity cannot open it directly |

Keep Unity usage beginner-readable (primitives, free assets, simple physics).

---

## 5. System architecture

```
Webcam → [1] Capture → [2] Recognizer → [3] Decision Logic → (UDP) → [4] Unity: game + AR
          own thread      swappable        thresholds, timing
                     [5] Metrics: timestamps at every stage
```

| # | Module | Responsibility | Code |
|---|---|---|---|
| 1 | Capture | Own thread, keep only the latest frame, MJPG, mirror the image | `python/punchar/capture/camera.py` |
| 2 | Recognizer | Per-frame raw results behind a common interface; adapters `mediapipe`, `replay` | `python/punchar/recognizer/` |
| 3 | Decision Logic | Smoothing, thresholds, cooldown, per-hand state machine → `strike`, `hand_lost` | `python/punchar/decision/` |
| 4 | Unity game | Consumes UDP messages only. Never calls or knows about the model | `Assets/_Project/` |
| 5 | Metrics | Per-stage timestamps; Ctrl+C prints a timing table | `python/punchar/metrics/`, `python/tools/benchmark.py` |

Folder ownership: [`code-structure.md`](../team/code-structure.md).

### Recognizer output (`recognizer/base.py`)

```
FrameResult {
  frame_id: int
  timestamp_ms: int              # capture time, Unix epoch ms
  hands: list[HandResult]        # 0..2
}
HandResult {
  handedness: "Left" | "Right"   # the PLAYER's real hand
  shape: string                  # "Closed_Fist", "Open_Palm", "None", ...
  score: float                   # 0..1
  landmarks: list[21 x (x, y, z)]       # normalized 0..1 image coords
  world_landmarks: list[21 x (x, y, z)] # meters
}
Recognizer { load(); predict(image, frame_id, timestamp_ms) -> FrameResult; close() }
```

### UDP messages — DECIDED (2026-11-19)

The full contract is in [`PHAN_CONG.vi.md`](../team/PHAN_CONG.vi.md), section "Hợp đồng dữ liệu Python → Unity". Code: `python/punchar/transport/udp_sender.py` ↔ `Assets/_Project/Network/Messages.cs`. **Change both in the same PR, with team approval.** Unity ignores unknown `type`s.

```json
{"type":"pose","t":1795072926644,"frame":1532,
 "hands":[{"hand":"Right","x":0.7312,"y":0.5979,"size":0.1830,
           "shape":"Closed_Fist","score":0.9312,"lm":[0.7101,0.4520,0.0, ...63 floats]}]}
{"type":"strike","t":1795072926711,"hand":"Left","kind":"PUNCH_STRAIGHT","x":0.3120,"y":0.5521}
{"type":"hand_lost","t":1795072927010,"hand":"Right"}
```

- `pose`: every processed frame, even with no hands. `x, y` = palm center (landmark 9). `size` = wrist→landmark 9 distance. `lm` = 21 landmarks flattened (`JsonUtility` cannot read nested arrays).
- `strike`: once per confirmed strike. `kind` ∈ `PUNCH_STRAIGHT`, `BLOCK`, `OPEN_PALM`, `HOOK` (optional, not implemented).
- `hand_lost`: once, when a hand is absent longer than `lost_grace_ms`.
- `t`: capture time of the source frame (Unix epoch ms, same clock both sides) → **end-to-end latency = Unity time at render − `t`**.
- **Mirroring happens once**: the image is flipped in `capture/camera.py`; handedness is corrected for the flipped image in `recognizer/mediapipe_recognizer.py`. Unity never flips again.
- `x, y` use Unity viewport convention (0..1, y up). Conversion from MediaPipe's y-down happens **only in `udp_sender.py`**. `z` is MediaPipe's relative depth (negative = closer to camera), for 3D hand shape only.
- Floats rounded to 4 decimals.

---

## 6. Gestures and decision logic

Rule: **the side the shape comes from = the hand that must hit it.**

Implemented in `python/punchar/decision/` (owner: Duy), tests in `python/tests/test_decision.py`. Strikes combine **hand shape** (MediaPipe `shape` plus finger-openness ratio `r_open` from landmarks) with **motion** over several frames (planar velocity, growth rate of `hand_size`).

| Gesture | `kind` | Detection (current) | Status |
|---|---|---|---|
| Straight punch | `PUNCH_STRAIGHT` | Fist + `hand_size` grows ≥ `punch_size_growth` (15%) within `punch_window_ms` (150 ms) | Decided |
| Block | `BLOCK` | Fist held still (velocity below thresholds) for ≥ `block_hold_ms` (120 ms) | Gesture decided; detection is Duy's proposal, not in `DECISIONS.md`; game meaning **[TBD]** |
| Open palm | `OPEN_PALM` | Open palm + push toward camera | Gesture decided; game meaning **[TBD]** |
| Hook | `HOOK` | Not implemented | Optional; first item cut if late |

- Per-hand state machine: `IDLE → WINDUP → STRIKE → COOLDOWN → IDLE`, plus `BLOCK_READY` for block.
- Per-hand cooldown `cooldown_ms` (250). Brief loss from motion blur bridged by `blur_grace_ms` (60). Absent > `lost_grace_ms` (300) → `hand_lost`.
- One Euro filter for hand position (`decision/filter.py`).
- **All parameters in `config/default.toml`, times in ms, never frame counts.**
- Report **system latency** (machines) and **design latency** (intentional waiting to confirm a gesture) separately.

---

## 7. Game design — DECIDED (2026-10-26)

Reference: Move Fast (https://youtu.be/p1DniSBv85E?t=173).

- A **launcher** fires **shapes** toward the player along a lane, on the level's schedule (read from level data).
- Each shape is on the **left or right** and shows (by shape/color) the **gesture required**.
- Correct hand + correct gesture while the shape is in the **hit zone** → hit: score, combo, multiplier, break effect.
- Wrong hand, wrong gesture, or shape passes the hit zone → miss, combo reset.
- The **hit window** must compensate end-to-end latency; it is a config value and a key link between inference and game feel. Width **[TBD]**.
- **Levels:** Level 1 complete first (1–2 min, menu, end screen; M2). Level 2 + unlock by score later, cuttable.
- **Scoring:** score, combo, multiplier; local top score / leaderboard.
- **Audio:** background music only, **not** beat-synced (not a rhythm game) + hit/miss sounds.
- **Visuals:** vivid, harmonious colors, clear layout (lane in center, score/combo panel, progress bar).
- **3D content:** hands (FBX rig, 15 finger joints, driven by `lm`), launcher, flying shapes, surroundings, animations, effects, AR webcam background. "Reflection" object: meaning **[TBD]**.
- **Debug mode** (one key): skeleton, gesture labels, per-stage latency, FPS.
- **Keyboard fallback** (`F` = left, `J` = right) emits the same hit path as UDP `strike`, for development without the recognizer.

---

## 8. Inference & performance

Required metrics: end-to-end latency, per-stage latency, **p50/p95/p99** + jitter (never only the mean), FPS, CPU %/RAM, accuracy (frame level and strike level), false triggers per minute, in-game hit rate.

Every technique: measure **before / after** with `tools/benchmark.py` on the same **recorded videos** (not live webcam), on the benchmark machine. Weak-device simulation: limit cores (`taskset`), lower camera resolution.

| Sprint | Techniques |
|---|---|
| 1 (done) | Capture thread keeping the latest frame; webcam MJPG (10 → 30 FPS) |
| 4 | Lower resolution, hand-region crop |
| 5 | Frame skipping, adaptive quality under load (cuttable); weak-device simulation |
| 6 | End-to-end measurement with a 240 FPS external camera; tune to < 100 ms |

Not planned now: ONNX Runtime, OpenVINO, FP16/INT8 (tied to the dropped external model).

---

## 9. Schedule — DECIDED (2026-11-16)

8 one-week sprints, details in [`../sprints/`](../sprints/README.md); current sprint in [`../README.md`](../README.md).

| Milestone | Date | Content |
|---|---|---|
| M1 | 2026-11-29 | Real punch in front of webcam → block breaks in Unity |
| M2 | 2026-12-13 | Full Level 1 with real hands, 3 gestures, AR background |
| M3 | 2026-12-27 | Feature freeze, bug fixes only afterwards |
| M4 | 2027-01-10 | Demo ready: build, report, slides |

Cut order if late: hook → Level 2 and level unlock → launcher animation, surroundings → adaptive quality. Never cut: M1, M2, before/after benchmark table, accuracy table.

---

## 10. Rules for coding agents

1. Follow the mandatory rules in [`AGENTS.md`](../../AGENTS.md) (read-only `.unity`/`.prefab`/`.meta`/`ProjectSettings`, `.meta` handling, UDP contract, ms timing, single mirroring point, benchmark p50/p95/p99).
2. Game code never depends on a specific model. Unity consumes UDP messages only.
3. All thresholds, durations, cooldowns, resolutions, ports → `config/default.toml`, not hard-coded.
4. Every stage logs timestamps; every message carries `t`.
5. Keep CPU and memory usage low; ask before adding heavy dependencies.
6. Unit-test decision logic with recorded / synthetic `FrameResult` sequences.
7. Put new code in the folder given by [`code-structure.md`](../team/code-structure.md).
8. Do not decide **[TBD]** items. Ask the user.

---

## 11. Open decisions

- [ ] Game meaning of "block" and "open palm" (which shape needs which gesture, what a hit does)
- [ ] Meaning of "reflection" in the 3D content list
- [ ] Success criteria: per-frame vs per-strike accuracy, minimum vs target levels, recording conditions
- [ ] Shared evaluation dataset: people, strikes, conditions (Sprint 4)
- [ ] How the webcam image reaches Unity (Sprint 2)
- [ ] Hit window width (ms)
- [ ] How the game is delivered: build vs. Unity Editor (Sprint 6)
