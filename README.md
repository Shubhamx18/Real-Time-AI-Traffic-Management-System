<div align="center">

# Real-Time AI Traffic Management System

### Adaptive Signal Control using Computer Vision and Deep Learning

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![React](https://img.shields.io/badge/React-18.3-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://reactjs.org)
[![YOLOv8](https://img.shields.io/badge/YOLOv8s-Ultralytics-00FFFF?style=for-the-badge&logo=yolo&logoColor=black)](https://docs.ultralytics.com)
[![Flask](https://img.shields.io/badge/Flask-3.1-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge)](LICENSE)

**An intelligent, real-time traffic signal management system that uses AI-powered vehicle detection to dynamically optimize intersection signal timing — reducing congestion and improving urban traffic flow.**

[Overview](#overview) · [Features](#features) · [Architecture](#architecture) · [Installation](#installation) · [Usage](#usage) · [API Reference](#api-reference) · [Performance](#performance)

---

</div>

## Overview

Traditional traffic signals operate on fixed timers, completely blind to real-time road conditions. This system replaces that outdated model with an AI-powered adaptive approach that responds dynamically to live traffic data.

**How it works:**

1. Upload 4 intersection videos (North, South, East, West directions)
2. YOLOv8s detects and tracks every vehicle in real time
3. Queue analysis determines which direction has the most congestion
4. Signal timing is dynamically optimized — busier roads get longer green windows
5. A professional dashboard displays live feeds, analytics, and AI-generated insights

The result: reduced wait times, lower congestion, and smarter intersections.

---

## Features

### AI Vehicle Detection

- **YOLOv8s** deep learning model for fast, accurate detection
- Recognizes cars, trucks, buses, motorcycles, and bicycles
- Processes all 4 directions simultaneously every frame
- Real-time bounding box tracking with centroid-based association

### Adaptive Signal Control

- **Queue-based priority** — the direction with the most vehicles gets green first
- **Dynamic green time** — ranges from 10s to 60s based on vehicle density and queue length
- **Density-aware timing** — congested roads receive proportionally longer green signals
- Automatic signal cycle sequencing: Green → Yellow → Red

### AI Analytics Dashboard

- Live traffic density charts with real-time Recharts visualization
- AI efficiency score calculated per intersection in real time
- Queue analysis showing waiting vs. moving vehicles per direction
- Direction comparison with side-by-side traffic load visualization
- Smart AI recommendations for congestion alerts and optimization
- Detection history tracking past sessions with detailed metrics

### Professional Control Center

- 4-panel live intersection feeds with detection overlays
- Signal timeline visualization showing current and upcoming phases
- System status monitoring: FPS, progress, and elapsed time
- Dark-themed, high-density UI designed for traffic control operations
- Fully browser-based — no external windows or dependencies

### Configurable Settings

- Detection parameters: confidence, IoU threshold, image size
- Signal timing: base green, max green, yellow and red clearance durations
- Display settings: refresh rate, output quality, themes
- Alert thresholds: congestion, low traffic, emergency triggers

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      FRONTEND (React 18)                     │
│                                                              │
│   Live Control    Upload Footage    Analytics    Settings    │
│        │                │               │            │       │
│        └────────────────┴───────────────┴────────────┘       │
│                              │ HTTP / REST                   │
├──────────────────────────────┼───────────────────────────────┤
│                      BACKEND (Flask)                         │
│                              │                               │
│         ┌────────────────────┴────────────────────┐          │
│         │            API Layer (REST)              │          │
│         │  /upload  /progress  /frame/<direction>  │          │
│         │  /stop    /settings  /system/stats       │          │
│         └────────────────────┬────────────────────┘          │
│                              │                               │
│         ┌────────────────────┴────────────────────┐          │
│         │          Detection Subprocess            │          │
│         │                                          │          │
│         │   YOLOv8s Engine                         │          │
│         │        └─> Centroid Tracker              │          │
│         │                 └─> Queue Signal Timing  │          │
│         └──────────────────────────────────────────┘          │
│                                                              │
│   detection_progress.json    (live metrics)                  │
│   frames/{north,south,east,west}.jpg   (live feeds)          │
│   analytics_history.json     (session history)               │
└──────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Frontend | React 18.3 | Single-page dashboard application |
| Charts | Recharts 3.8 | Real-time traffic density visualization |
| HTTP Client | Axios | API communication with the backend |
| Backend | Flask 3.1 | REST API server with CORS support |
| AI Model | YOLOv8s (Ultralytics) | Real-time vehicle detection |
| Tracking | Custom CentroidTracker | Multi-object tracking with IoU matching |
| Computer Vision | OpenCV 4.9+ | Frame processing, drawing, and I/O |
| Computation | NumPy, SciPy | Matrix operations and cost assignment |
| Containerization | Docker + Docker Compose | Optional deployment |

---

## Project Structure

```
AI-Based-Traffic-Management-SIH/
├── README.md
├── docker-compose.yml
│
├── backend/
│   ├── run_server.py              # Flask API server (main entry point)
│   ├── run_detection.py           # Detection subprocess launcher
│   ├── vehicle_tracker_ultra.py   # YOLOv8 + CentroidTracker engine
│   ├── algo.py                    # Traffic signal optimization algorithm
│   ├── requirements.txt           # Python dependencies
│   ├── yolov8s.pt                 # YOLOv8s model weights (~22 MB)
│   ├── frames/                    # Live detection frame output
│   ├── uploads/                   # Uploaded video storage
│   ├── detection_progress.json    # Real-time detection metrics
│   ├── analytics_history.json     # Historical detection records
│   └── settings.json              # User-configured settings
│
└── frontend/
    ├── package.json
    ├── public/
    │   └── index.html
    └── src/
        ├── App.js                 # Main dashboard application
        ├── Settings.js            # Settings panel component
        └── styles.css             # Complete UI styling
```

---

## Installation

### Prerequisites

- Python 3.10+ with pip
- Node.js 18+ with npm
- Git

### Step 1 — Clone the Repository

```bash
git clone https://github.com/Shubhamx18/Real-Time-AI-Traffic-Management-System.git
cd Real-Time-AI-Traffic-Management-System
```

### Step 2 — Set Up the Backend

```bash
cd backend

# Create a virtual environment
python -m venv venv

# Activate the environment
# Windows:
venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

> The YOLOv8s model weights (~22 MB) will auto-download on first run.

### Step 3 — Set Up the Frontend

```bash
cd ../frontend
npm install
```

### Step 4 — Start the System

**Terminal 1 — Backend**

```bash
cd backend
source venv/bin/activate   # Windows: venv\Scripts\activate
python run_server.py
```

> API server starts at `http://localhost:5000`

**Terminal 2 — Frontend**

```bash
cd frontend
npm start
```

> Dashboard opens at `http://localhost:3000`

---

## Usage

### 1. Upload Traffic Footage

Go to **Upload Footage** and select 4 video files — one per intersection direction: North, South, East, and West.

> Use traffic surveillance footage where each video captures a single approach lane of the intersection.

### 2. Start AI Analysis

Click **Start AI Analysis**. The system will:

- Switch automatically to the Live Control page
- Display a loading indicator while the AI engine initializes
- Begin showing live detection feeds with bounding boxes overlaid
- Update the signal timing panel in real time

### 3. Monitor Live Detection

The Live Control dashboard shows:

- 4 live feeds with real-time vehicle detection overlays
- Green signal indicator — which direction currently has right-of-way
- Queue counts — vehicles waiting at each approach
- Signal cycle timeline — current and upcoming phases

### 4. Review Analytics

Switch to the **Analytics** tab to access:

- Traffic density trends over time
- AI efficiency scores and congestion indices
- Queue analysis breakdowns per direction
- Smart recommendations for signal optimization
- Full detection history with per-session metrics

### 5. Stop Analysis

Click **Stop Analytics** at any time to gracefully terminate the detection process and save the session.

---

## How It Works

### Detection Pipeline

```
Video Frame
  → YOLOv8s Inference
  → Bounding Box Extraction
  → Coordinate Scaling
  → CentroidTracker Matching
  → Queue Zone Classification
  → Signal Time Calculation
  → Frame Annotation
  → Dashboard Display
```

### Queue-Based Signal Timing

The system uses a zone-based queue detection approach:

1. A stop line is drawn at 65% of the frame height
2. Vehicles above the line are counted as queued (waiting)
3. Vehicles crossing below the line are counted as passed
4. The direction with the highest queue count receives green priority
5. Green time is calculated dynamically using the following formula:

```
green_time = base_green + (queue_count × 2.5) + density_bonus
green_time = clamp(green_time, 10s, 60s)
```

### Tracker Algorithm

The custom CentroidTracker uses:

- **IoU matching** (Intersection over Union) for overlapping bounding boxes
- **Centroid distance** for non-overlapping re-identification
- **Greedy cost assignment** sorted by combined IoU and distance cost
- **Age-based cleanup** — tracks are removed after 8 frames without a detection

---

## Configuration

All parameters are configurable from the Settings page in the dashboard.

| Category | Parameter | Default | Description |
|---|---|---|---|
| Detection | Confidence | 0.25 | Minimum detection confidence threshold |
| Detection | IoU | 0.45 | Non-maximum suppression threshold |
| Detection | Image Size | 384 | YOLO inference resolution |
| Detection | Model | YOLOv8s | Detection model variant |
| Signal | Base Green | 10 s | Minimum green signal duration |
| Signal | Max Green | 60 s | Maximum green signal duration |
| Signal | Yellow Time | 3 s | Yellow signal duration |
| Signal | All-Red Time | 2 s | Safety clearance interval |
| Display | Refresh Rate | 500 ms | Frame polling interval |
| Display | JPEG Quality | 70 | Detection frame output quality |
| Alerts | Congestion Threshold | 15 | Vehicle count to trigger a congestion alert |

---

## API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Server health check |
| `/upload` | POST | Upload 4 videos and start detection |
| `/stop` | POST | Stop the active detection process |
| `/progress` | GET | Live detection progress and metrics |
| `/frame/<direction>` | GET | Latest detection frame as JPEG |
| `/analytics/summary` | GET | Historical analytics data |
| `/system/stats` | GET | System resource statistics |
| `/settings` | GET | Retrieve current settings |
| `/settings` | POST | Update settings |
| `/settings/reset` | POST | Reset settings to defaults |
| `/system/clear-frames` | POST | Clear cached detection frames |

### Example — Fetch Live Progress

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
| Model | YOLOv8s (22 MB) |
| Inference Resolution | 384 × 384 |
| Detection FPS (CPU) | 3 – 5 FPS |
| Detection FPS (GPU) | 15 – 25 FPS |
| Directions Processed | All 4 simultaneously |
| Tracker Latency | < 1 ms per direction |
| Dashboard Refresh | 500 ms (2 Hz) |
| Vehicle Classes | 5 (car, truck, bus, motorcycle, bicycle) |

### Model Comparison

| Model | Size | CPU Speed | Accuracy | Status |
|---|---|---|---|---|
| YOLOv8n | 6 MB | ~15 FPS | Good | Available |
| **YOLOv8s** | **22 MB** | **~5 FPS** | **Great** | **Default** |
| YOLOv8m | 52 MB | ~2 FPS | Excellent | Available |
| YOLOv8x | 136 MB | ~0.5 FPS | Maximum | Available |

To switch models, change the `MODEL` value in the `Cfg` class inside `vehicle_tracker_ultra.py`.

---

## Docker Deployment

```bash
# Build and start both services
docker-compose up --build

# Access the dashboard at http://localhost:3000
```

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-improvement`
3. Commit your changes: `git commit -m "Add your improvement"`
4. Push to the branch: `git push origin feature/your-improvement`
5. Open a Pull Request

Please ensure all changes are tested and existing functionality is not broken before submitting.

---

## License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for full details.

---

<div align="center">

Built for the **Smart India Hackathon (SIH)**

*Reducing urban congestion through AI-powered adaptive traffic signals*

If this project was useful to you, consider giving it a star on GitHub.

</div>
