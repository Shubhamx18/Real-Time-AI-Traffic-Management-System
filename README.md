<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:0f2027,50:203a43,100:2c5364&height=200&section=header&text=AI%20Traffic%20Management&fontSize=42&fontColor=ffffff&fontAlignY=38&desc=Real-Time%20Adaptive%20Signal%20Control%20%7C%20YOLOv8%20%2B%20React%20%2B%20Flask&descAlignY=58&descSize=16" width="100%"/>

<br/>

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![React](https://img.shields.io/badge/React-18.3-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://reactjs.org)
[![YOLOv8](https://img.shields.io/badge/YOLOv8s-Ultralytics-00FFFF?style=for-the-badge&logo=yolo&logoColor=black)](https://docs.ultralytics.com)
[![Flask](https://img.shields.io/badge/Flask-3.1-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge)](LICENSE)
[![Stars](https://img.shields.io/github/stars/Shubhamx18/Real-Time-AI-Traffic-Management-System?style=for-the-badge&color=fbbf24)](https://github.com/Shubhamx18/Real-Time-AI-Traffic-Management-System/stargazers)

<br/>

> **Replace fixed-timer intersections with an AI-driven adaptive system.**
> YOLOv8s detects vehicles across 4 live camera feeds, calculates queue lengths,
> and dynamically assigns green time — all visible on a real-time browser dashboard.

<br/>

[![Python](https://img.shields.io/badge/Python-47.1%25-3776AB?style=flat-square&logo=python&logoColor=white)]()
[![JavaScript](https://img.shields.io/badge/JavaScript-38.0%25-F7DF1E?style=flat-square&logo=javascript&logoColor=black)]()
[![CSS](https://img.shields.io/badge/CSS-12.5%25-1572B6?style=flat-square&logo=css3&logoColor=white)]()
[![Dockerfile](https://img.shields.io/badge/Dockerfile-1.4%25-2496ED?style=flat-square&logo=docker&logoColor=white)]()

</div>

<br/>

---

## Navigation

| | |
|---|---|
| [Overview](#-overview) | What the system does and why |
| [Features](#-features) | Detection, signals, dashboard, settings |
| [Architecture](#-architecture) | System diagram and data flow |
| [Tech Stack](#-tech-stack) | All libraries and frameworks |
| [Project Structure](#-project-structure) | File tree with annotations |
| [Installation](#-installation) | Step-by-step setup guide |
| [Usage](#-usage) | How to run an analysis session |
| [How It Works](#-how-it-works) | Algorithm and pipeline details |
| [Configuration](#-configuration) | All tunable parameters |
| [API Reference](#-api-reference) | All REST endpoints |
| [Performance](#-performance) | FPS, latency, model comparison |
| [Docker](#-docker-deployment) | Container deployment |
| [Contributing](#-contributing) | How to submit changes |

---

## Overview

Traditional traffic lights run on fixed timers — they cannot react to an empty road or a backed-up queue. This system changes that.

```
Upload 4 videos  →  YOLOv8s detects vehicles  →  Queue analysis per direction
      →  Adaptive green time assigned  →  Live dashboard updates in real time
```

The busiest approach always gets priority. Signal duration scales with congestion. Every decision is visible on the dashboard the moment it happens.

---

## Features

<table>
<tr>
<td width="50%" valign="top">

### AI Vehicle Detection
- YOLOv8s — fast, accurate, 22 MB
- 5 classes: car · truck · bus · motorcycle · bicycle
- All 4 directions processed simultaneously
- Centroid-based multi-object tracking

</td>
<td width="50%" valign="top">

### Adaptive Signal Control
- Queue-based priority per direction
- Green time: 10 s – 60 s, density-scaled
- Automatic cycle: Green → Yellow → All-Red
- Density bonus for heavily packed roads

</td>
</tr>
<tr>
<td width="50%" valign="top">

### Analytics Dashboard
- Live density charts via Recharts
- AI efficiency score per session
- Queue breakdown: waiting vs. moving
- Congestion alerts + recommendations
- Full detection history with metrics

</td>
<td width="50%" valign="top">

### Control Center
- 4-panel live feeds with overlays
- Signal timeline — current + upcoming phases
- Status bar: FPS · progress · elapsed time
- Dark UI designed for traffic operations
- 100% browser-based, no native dependencies

</td>
</tr>
</table>

---

## Architecture

```
╔══════════════════════════════════════════════════════════════════════╗
║                        FRONTEND  ·  React 18                        ║
║                                                                      ║
║   ┌─────────────┐  ┌──────────────┐  ┌────────────┐  ┌──────────┐  ║
║   │ Live Control│  │Upload Footage│  │ Analytics  │  │ Settings │  ║
║   └──────┬──────┘  └──────┬───────┘  └─────┬──────┘  └────┬─────┘  ║
║          └────────────────┴────────────────┴───────────────┘        ║
║                                    │  Axios  ·  HTTP/REST           ║
╠════════════════════════════════════╪═════════════════════════════════╣
║                        BACKEND  ·  Flask 3.1                        ║
║                                    │                                 ║
║          ┌─────────────────────────┴──────────────────────┐         ║
║          │                  REST API Layer                 │         ║
║          │  /upload  /progress  /frame/<dir>  /analytics  │         ║
║          │  /stop    /settings  /system/stats  /health    │         ║
║          └─────────────────────────┬──────────────────────┘         ║
║                                    │  subprocess                     ║
║          ┌─────────────────────────┴──────────────────────┐         ║
║          │              Detection Engine                   │         ║
║          │                                                 │         ║
║          │  vehicle_tracker_ultra.py                       │         ║
║          │    └─ YOLOv8s Inference                         │         ║
║          │         └─ CentroidTracker  (IoU + distance)    │         ║
║          │              └─ algo.py  (signal timing)        │         ║
║          └─────────────────────────────────────────────────┘         ║
║                                                                      ║
║  detection_progress.json   ·   frames/{N,S,E,W}.jpg                 ║
║  analytics_history.json    ·   settings.json                        ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## Tech Stack

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| Frontend | React | 18.3 | Single-page dashboard |
| Charts | Recharts | 3.8 | Live traffic density visualization |
| HTTP Client | Axios | latest | REST API communication |
| Backend | Flask | 3.1 | API server with CORS |
| AI Model | YOLOv8s (Ultralytics) | latest | Vehicle detection |
| Tracking | CentroidTracker (custom) | — | Multi-object tracking |
| Computer Vision | OpenCV | 4.9+ | Frame I/O and annotation |
| Computation | NumPy + SciPy | latest | Matrix ops and cost assignment |
| Containers | Docker + Compose | — | Optional deployment |

---

## Project Structure

```
Real-Time-AI-Traffic-Management-System/
│
├── docker-compose.yml                  # Two-service stack with health-check gating
├── README.md
│
├── backend/
│   ├── run_server.py                   # Flask entry point — starts API on :5000
│   ├── run_detection.py                # Spawns detection subprocess
│   ├── vehicle_tracker_ultra.py        # YOLOv8s inference + CentroidTracker
│   ├── algo.py                         # Queue analysis + green time calculation
│   ├── requirements.txt
│   ├── yolov8s.pt                      # ~22 MB — auto-downloaded on first run
│   │
│   ├── frames/                         # JPEG output — one file per direction
│   ├── uploads/                        # Uploaded videos (Docker volume mounted)
│   ├── detection_progress.json         # Written every frame — polled by /progress
│   ├── analytics_history.json          # Session history
│   └── settings.json                   # Persisted user config
│
└── frontend/
    ├── package.json
    ├── public/index.html
    └── src/
        ├── App.js                      # All tabs, state, and polling logic
        ├── Settings.js                 # Settings panel
        └── styles.css                  # Full dark-theme UI
```

---

## Installation

### Prerequisites

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![Node](https://img.shields.io/badge/Node.js-18%2B-339933?style=flat-square&logo=node.js&logoColor=white)
![Git](https://img.shields.io/badge/Git-required-F05032?style=flat-square&logo=git&logoColor=white)

---

**Step 1 — Clone**

```bash
git clone https://github.com/Shubhamx18/Real-Time-AI-Traffic-Management-System.git
cd Real-Time-AI-Traffic-Management-System
```

---

**Step 2 — Backend**

```bash
cd backend
python -m venv venv

# Activate
venv\Scripts\activate          # Windows
source venv/bin/activate       # macOS / Linux

pip install -r requirements.txt
```

> `yolov8s.pt` (~22 MB) downloads automatically on first run.

---

**Step 3 — Frontend**

```bash
cd ../frontend
npm install
```

---

**Step 4 — Run**

| Terminal | Command | URL |
|---|---|---|
| 1 — Backend | `python run_server.py` | `http://localhost:5000` |
| 2 — Frontend | `npm start` | `http://localhost:3000` |

```bash
# Terminal 1
cd backend && source venv/bin/activate && python run_server.py

# Terminal 2
cd frontend && npm start
```

---

## Usage

| Step | Action | Result |
|---|---|---|
| 1 | Open **Upload Footage** tab | Select 4 videos (N · S · E · W) |
| 2 | Click **Start AI Analysis** | Engine initializes, switches to Live Control |
| 3 | Watch **Live Control** | 4 annotated feeds + signal timeline update live |
| 4 | Open **Analytics** tab | Density charts, efficiency scores, history |
| 5 | Click **Stop Analytics** | Subprocess exits, session saved to `analytics_history.json` |

> Use single-approach traffic camera footage per video. MP4 works well.

---

## How It Works

### Detection Pipeline

```
Video Frame
  ├─ YOLOv8s Inference              ← vehicle_tracker_ultra.py
  ├─ Bounding Box Extraction
  ├─ Coordinate Scaling
  ├─ CentroidTracker Match           ← IoU + centroid distance
  ├─ Queue Zone Classification       ← 65% height threshold
  ├─ Green Time Calculation          ← algo.py
  ├─ Frame Annotation
  └─ JPEG → frames/<direction>.jpg  ← polled via /frame/<direction>
```

---

### Queue-Based Signal Timing

A stop line is drawn at **65% of frame height**.

| Zone | Status |
|---|---|
| Above stop line | Queued (waiting) |
| Crossing below | Passed (counted) |

The direction with the **highest queue count** gets green. Duration:

```
green_time = base_green + (queue_count × 2.5) + density_bonus
green_time = clamp(green_time, 10 s, 60 s)
```

---

### CentroidTracker

| Mechanism | Purpose |
|---|---|
| IoU matching | Pair overlapping boxes across frames |
| Centroid distance | Re-identify shifted vehicles |
| Greedy cost sort | Assign tracks by lowest combined cost |
| Age-based cleanup | Drop tracks missing for 8+ frames |

---

## Configuration

> All settings live in the **Settings** tab and persist to `settings.json`.

| Category | Parameter | Default | Range / Notes |
|---|---|---|---|
| **Detection** | Confidence | `0.25` | 0.0 – 1.0 |
| **Detection** | IoU | `0.45` | NMS overlap threshold |
| **Detection** | Image Size | `384` | px — higher = slower + more accurate |
| **Detection** | Model | `YOLOv8s` | n / s / m / x |
| **Signal** | Base Green | `10 s` | Minimum duration |
| **Signal** | Max Green | `60 s` | Maximum duration |
| **Signal** | Yellow Time | `3 s` | Fixed |
| **Signal** | All-Red Time | `2 s` | Safety clearance |
| **Display** | Refresh Rate | `500 ms` | Polling interval |
| **Display** | JPEG Quality | `70` | 1 – 100 |
| **Alerts** | Congestion Threshold | `15 vehicles` | Triggers alert |

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Server health check |
| `POST` | `/upload` | Upload 4 videos, start detection |
| `POST` | `/stop` | Terminate detection subprocess |
| `GET` | `/progress` | Live metrics — frame, FPS, queues, signals |
| `GET` | `/frame/<direction>` | Latest JPEG for north / south / east / west |
| `GET` | `/analytics/summary` | Aggregated session history |
| `GET` | `/system/stats` | CPU / memory usage |
| `GET` | `/settings` | Read current config |
| `POST` | `/settings` | Write config |
| `POST` | `/settings/reset` | Reset to defaults |
| `POST` | `/system/clear-frames` | Flush cached frames |

### Sample Response — `/progress`

```bash
curl http://localhost:5000/progress
```

```json
{
  "status": "detecting",
  "frame": 150,
  "total_frames": 3000,
  "progress": 5.0,
  "fps": 3.9,
  "directions": {
    "north": { "queue_count": 8,  "vehicles_on_road": 12, "green_time": 30 },
    "south": { "queue_count": 3,  "vehicles_on_road": 5,  "green_time": 18 },
    "east":  { "queue_count": 10, "vehicles_on_road": 15, "green_time": 35 },
    "west":  { "queue_count": 2,  "vehicles_on_road": 4,  "green_time": 15 }
  }
}
```

---

## Performance

| Metric | Value |
|---|---|
| Model size | 22 MB |
| Inference resolution | 384 × 384 px |
| CPU speed | 3 – 5 FPS |
| GPU speed | 15 – 25 FPS |
| Directions processed | 4 simultaneously |
| Tracker latency | < 1 ms per direction |
| Dashboard refresh | 500 ms (2 Hz) |
| Vehicle classes | 5 |

### Model Comparison

| Model | Size | CPU FPS | Accuracy | |
|---|---|---|---|---|
| YOLOv8n | 6 MB | ~15 | Good | Available |
| **YOLOv8s** | **22 MB** | **~5** | **Great** | **Default** |
| YOLOv8m | 52 MB | ~2 | Excellent | Available |
| YOLOv8x | 136 MB | ~0.5 | Maximum | Available |

> To switch: update `MODEL` in the `Cfg` class inside `vehicle_tracker_ultra.py`.

---

## Docker Deployment

`docker-compose.yml` defines two services. The frontend waits for the backend health check to pass before starting — no race conditions.

```bash
docker-compose up --build
# Dashboard → http://localhost:3000
```

| Service | Container | Port | Notes |
|---|---|---|---|
| Backend | `traffic-backend` | `5000` | Health-checked every 30 s |
| Frontend | `traffic-frontend` | `3000 → 80` | Starts only after backend is healthy |

Uploads persist via volume: `./backend/uploads:/app/uploads`

---

## Contributing

```bash
# 1. Fork and clone
git checkout -b feature/your-improvement

# 2. Make changes, then
git commit -m "feat: describe your change"
git push origin feature/your-improvement

# 3. Open a Pull Request
```

Please test changes against the detection pipeline before submitting.

---

## License

Distributed under the **MIT License** — see [`LICENSE`](LICENSE) for details.

---

<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:2c5364,50:203a43,100:0f2027&height=120&section=footer" width="100%"/>

**Built for Smart India Hackathon (SIH)**

*Reducing urban congestion through AI-powered adaptive traffic signals*

[![GitHub](https://img.shields.io/badge/View%20on-GitHub-181717?style=for-the-badge&logo=github)](https://github.com/Shubhamx18/Real-Time-AI-Traffic-Management-System)

</div>
