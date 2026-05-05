"""
╔══════════════════════════════════════════════════════════════════════════════╗
║   TRAFFIC QUEUE ANALYZER v8.0 — QUEUE ABOVE LINE = PRIORITY               ║
║   YOLOv8x + Queue Count Above Yellow Line + Line-Cross Counting           ║
║                                                                            ║
║   HOW IT WORKS:                                                            ║
║   ┌────────────────────────┐                                               ║
║   │  🚗 🚗 🚗 🚗 🚗 🚗   │  ← QUEUE ZONE (above yellow line)            ║
║   │  These vehicles decide │     Count = 6 → road gets PRIORITY           ║
║   │  signal priority       │                                               ║
║   │════ YELLOW LINE ═══════│  ← Boundary                                  ║
║   │  (passed through)      │     Vehicles below = already passed          ║
║   └────────────────────────┘                                               ║
║                                                                            ║
║   Road with MOST vehicles ABOVE line → gets GREEN first                   ║
║   Green time = proportional to queue size                                 ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import cv2
import numpy as np
import json
import time
import sys
import os
from collections import defaultdict

PROGRESS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'detection_progress.json')
FRAMES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'frames')
os.makedirs(FRAMES_DIR, exist_ok=True)

try:
    from ultralytics import YOLO
except ImportError:
    raise ImportError("Missing: pip install ultralytics lapx")


# ══════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════

class Cfg:
    MODEL      = "yolov8s.pt"    # Small model: ~10x faster than yolov8x, still accurate for vehicles
    CONF       = 0.25            # Balanced for lighter model
    IOU        = 0.45
    IMGSZ      = 384             # Fast inference with good accuracy
    CLASSES    = [1, 2, 3, 5, 7]
    CLASS_NAMES = {1: "bicycle", 2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}

    # Yellow line position — vehicles ABOVE this = queued
    LINE_RATIO = 0.65           # Yellow line at 65% of frame height

    # Tracker params
    MAX_DISAPPEARED = 8         # Remove track after 8 frames without detection
    MATCH_DIST = 100            # Centroid match distance
    MIN_BOX_W  = 15
    MIN_BOX_H  = 15
    TRAIL_LEN  = 12             # Shorter trails = faster drawing
    BOX_ALPHA  = 1.0            # 1.0 = boxes snap instantly to detection (no smoothing lag)
    MIN_TRACK_FRAMES = 3        # Fast track confirmation

    CELL_W     = 640
    CELL_H     = 380

    # Signal timing
    BASE_GREEN = 10
    MAX_GREEN  = 60

    # Performance tuning
    FRAME_SKIP    = 0           # 0 = process every frame (best accuracy)
    SAVE_EVERY    = 2           # Save frames to disk every N frames
    PROGRESS_EVERY = 3          # Write progress every N frames


# ══════════════════════════════════════════════════════════════
# IoU HELPER
# ══════════════════════════════════════════════════════════════

def iou(a, b):
    x1 = max(a[0], b[0])
    y1 = max(a[1], b[1])
    x2 = min(a[2], b[2])
    y2 = min(a[3], b[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    if inter == 0:
        return 0.0
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    return inter / (area_a + area_b - inter) if (area_a + area_b - inter) > 0 else 0


# ══════════════════════════════════════════════════════════════
# QUEUE TRACKER — Zone-based, velocity-aware
# ══════════════════════════════════════════════════════════════

class QueueTracker:
    """
    Queue = vehicles ABOVE the yellow line.
    Road with most vehicles above line → gets green first.
    When vehicle crosses the line → counted as 'passed' (info only).
    """

    def __init__(self, direction, fps=25):
        self.direction = direction
        self.fps = fps
        self.next_id = 1
        self.objects = {}           # Active tracks
        self.all_ids = set()        # All IDs ever seen
        self.by_class = defaultdict(int)
        self.passed_ids = set()     # IDs that crossed the yellow line
        self.passed_count = 0       # Total vehicles that crossed line

    def update(self, detections, frame_h):
        line_y = int(frame_h * Cfg.LINE_RATIO)

        # Age existing tracks (no position prediction — keeps boxes on last known position)
        for tid in list(self.objects):
            self.objects[tid]['age'] += 1
            if self.objects[tid]['age'] > Cfg.MAX_DISAPPEARED:
                obj = self.objects[tid]
                if obj.get('frames_seen', 0) >= Cfg.MIN_TRACK_FRAMES:
                    self.all_ids.add(tid)
                    if tid not in self.passed_ids:
                        self.by_class[obj['cls_name']] += 1
                del self.objects[tid]

        if not detections:
            return self.objects, line_y

        # Parse detections
        new_dets = []
        for det in detections:
            x1, y1, x2, y2, conf, cls_id = det
            if (x2 - x1) < Cfg.MIN_BOX_W or (y2 - y1) < Cfg.MIN_BOX_H:
                continue
            cx = (x1 + x2) / 2.0
            cy = (y1 + y2) / 2.0
            new_dets.append({
                'box': (x1, y1, x2, y2), 'cx': cx, 'cy': cy,
                'conf': conf, 'cls_id': cls_id,
                'cls_name': Cfg.CLASS_NAMES.get(cls_id, "vehicle"),
            })

        if not new_dets:
            return self.objects, line_y

        if not self.objects:
            for nd in new_dets:
                self._register(nd, line_y)
            return self.objects, line_y

        # Matching: IoU + centroid
        obj_ids = list(self.objects.keys())
        n_obj = len(obj_ids)
        n_det = len(new_dets)

        cost = np.full((n_obj, n_det), 1e6)
        for i, tid in enumerate(obj_ids):
            obj = self.objects[tid]
            obj_box = obj.get('smooth_box', obj['box'])
            for j, nd in enumerate(new_dets):
                iou_val = iou(obj_box, nd['box'])
                dx = obj['cx'] - nd['cx']
                dy = obj['cy'] - nd['cy']
                dist = np.sqrt(dx * dx + dy * dy)

                if iou_val > 0.15:
                    cost[i, j] = (1.0 - iou_val) * 40
                elif dist < Cfg.MATCH_DIST:
                    cost[i, j] = dist

        used_rows = set()
        used_cols = set()
        for idx in np.argsort(cost.ravel()):
            i = idx // n_det
            j = idx % n_det
            if i in used_rows or j in used_cols:
                continue
            if cost[i, j] >= 1e5:
                break
            used_rows.add(i)
            used_cols.add(j)

            tid = obj_ids[i]
            nd = new_dets[j]

            prev_cy = self.objects[tid]['cy']

            # Calculate velocity (for metrics only, not prediction)
            dx = nd['cx'] - self.objects[tid]['cx']
            dy = nd['cy'] - prev_cy
            velocity = np.sqrt(dx * dx + dy * dy)

            # Check if vehicle crossed the yellow line (prev above, now below)
            prev_above = prev_cy < line_y
            now_below = nd['cy'] >= line_y
            if prev_above and now_below and tid not in self.passed_ids:
                self.passed_ids.add(tid)
                self.passed_count += 1
                cls_name = nd['cls_name']
                self.by_class[cls_name] = self.by_class.get(cls_name, 0) + 1

            self.objects[tid].update({
                'box': nd['box'],
                'smooth_box': nd['box'],   # No smoothing — snap to detection
                'cx': nd['cx'], 'cy': nd['cy'],
                'conf': nd['conf'], 'cls_id': nd['cls_id'],
                'cls_name': nd['cls_name'], 'age': 0,
                'velocity': velocity,
                'frames_seen': self.objects[tid].get('frames_seen', 0) + 1,
            })
            self.objects[tid]['trail'].append((int(nd['cx']), int(nd['cy'])))
            if len(self.objects[tid]['trail']) > Cfg.TRAIL_LEN:
                self.objects[tid]['trail'].pop(0)

        # Register unmatched detections
        for j in range(n_det):
            if j not in used_cols:
                self._register(new_dets[j], line_y)

        return self.objects, line_y

    def _register(self, nd, line_y):
        tid = self.next_id
        self.next_id += 1
        self.objects[tid] = {
            'box': nd['box'],
            'smooth_box': nd['box'],
            'cx': nd['cx'], 'cy': nd['cy'],
            'conf': nd['conf'], 'cls_id': nd['cls_id'],
            'cls_name': nd['cls_name'], 'age': 0,
            'velocity': 0.0,
            'frames_seen': 1,
            'trail': [(int(nd['cx']), int(nd['cy']))],
        }

    def get_queue_metrics(self, line_y=None):
        """
        Queue = vehicles ABOVE the yellow line.
        This is what decides signal priority.
        Passed = vehicles that crossed the line (informational).
        """
        if line_y is None:
            line_y = int(Cfg.CELL_H * Cfg.LINE_RATIO)

        in_queue = []       # Above yellow line
        below_line = []     # Below yellow line (passed)

        for tid, obj in self.objects.items():
            if obj['age'] > 5:
                continue
            cy = obj.get('cy', 0)
            if cy < line_y:
                in_queue.append(obj)
            else:
                below_line.append(obj)

        queue_count = len(in_queue)  # THIS decides priority

        # Density = box area of queued vehicles / queue zone area
        zone_area = Cfg.CELL_W * line_y  # Area above the line
        if zone_area > 0 and in_queue:
            total_box_area = sum(
                (o['smooth_box'][2] - o['smooth_box'][0]) * (o['smooth_box'][3] - o['smooth_box'][1])
                for o in in_queue
            )
            density = min(1.0, total_box_area / zone_area)
        else:
            density = 0.0

        return {
            'queue_count': queue_count,         # Vehicles ABOVE line — decides priority
            'vehicles_on_road': queue_count,    # Alias
            'queue_length': queue_count,        # Alias
            'below_line': len(below_line),
            'density': round(density, 3),
            'queue_density': round(density, 3),
            'passed': self.passed_count,        # Total that crossed line
            'total_unique': len(self.all_ids) + len(self.passed_ids),
            'active': queue_count + len(below_line),
            'waiting': queue_count,
            'moving': len(below_line),
        }

    def compute_green_time(self, metrics):
        """
        Green time based on queue count (vehicles above line).
        More vehicles waiting → more green time.
        """
        q = metrics['queue_count']
        den = metrics['density']

        if q == 0:
            return Cfg.BASE_GREEN

        # Linear scaling: more vehicles = proportionally more time
        # 1 vehicle = 10s, 5 vehicles = 20s, 10 = 30s, 15 = 40s, 20 = 50s
        green = Cfg.BASE_GREEN + (q * 2.0)

        # Density bonus: packed road gets extra time
        green *= (1.0 + den * 0.5)

        return max(Cfg.BASE_GREEN, min(int(green), Cfg.MAX_GREEN))


# ══════════════════════════════════════════════════════════════
# DRAWING — Queue-based visualization
# ══════════════════════════════════════════════════════════════

def draw_panel(frame, tracker, line_y):
    h, w = frame.shape[:2]
    out = frame  # Draw directly on frame (no copy)
    metrics = tracker.get_queue_metrics(line_y)

    # ── Queue zone tint (lightweight) ──
    out[0:line_y, :, 1] = np.clip(out[0:line_y, :, 1].astype(np.int16) + 8, 0, 255).astype(np.uint8)

    # ── Yellow line ──
    cv2.line(out, (0, line_y), (w, line_y), (0, 200, 200), 4)
    cv2.line(out, (0, line_y), (w, line_y), (0, 255, 255), 2)

    # Queue count label above line
    qlabel = f"QUEUE: {metrics['queue_count']}"
    cv2.putText(out, qlabel, (8, line_y - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1, cv2.LINE_AA)
    # Passed count label below line
    plabel = f"PASSED: {metrics['passed']}"
    cv2.putText(out, plabel, (8, line_y + 18),
                cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 200, 0), 1, cv2.LINE_AA)

    # ── Vehicles ──
    for tid, obj in tracker.objects.items():
        if obj['age'] > 2:  # Only show tracks detected within last 2 frames
            continue

        box = obj.get('smooth_box', obj['box'])
        x1, y1, x2, y2 = [max(0, int(v)) for v in box]
        x2 = min(x2, w - 1)
        y2 = min(y2, h - 1)
        bw, bh = x2 - x1, y2 - y1
        if bw < 4 or bh < 4:
            continue

        cy = obj.get('cy', 0)
        above_line = cy < line_y
        has_passed = tid in tracker.passed_ids

        # Color: orange/red if in queue (above line), green if passed (below)
        if above_line:
            color = (0, 140, 255)        # ORANGE — in queue
            border = (0, 100, 200)
        elif has_passed:
            color = (50, 255, 50)        # GREEN — crossed line
            border = (30, 200, 30)
        else:
            color = (0, 200, 0)          # GREEN — below line
            border = (0, 150, 0)

        # Green glow for just-passed vehicles (lightweight version)
        if has_passed and not above_line:
            cv2.rectangle(out, (x1 - 2, y1 - 2), (x2 + 2, y2 + 2), (50, 255, 50), 2)

        # Double-border box
        cv2.rectangle(out, (x1 - 1, y1 - 1), (x2 + 1, y2 + 1), border, 2)
        cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)

        # Corner brackets
        L = min(12, bw // 3, bh // 3)
        if L > 3:
            for (sx, sy, dx, dy) in [(x1,y1,1,1),(x2,y1,-1,1),(x1,y2,1,-1),(x2,y2,-1,-1)]:
                cv2.line(out, (sx, sy), (sx + dx * L, sy), color, 3)
                cv2.line(out, (sx, sy), (sx, sy + dy * L), color, 3)

        # Label
        conf = obj.get('conf', 0)
        cls_name = obj['cls_name']
        tag = f"{cls_name} {conf:.0%}"

        fs = 0.33
        (tw, th_txt), _ = cv2.getTextSize(tag, cv2.FONT_HERSHEY_SIMPLEX, fs, 1)
        ly = max(y1 - 4, th_txt + 5)
        lx = x1
        cv2.rectangle(out, (lx - 1, ly - th_txt - 4), (lx + tw + 5, ly + 1), color, -1)
        cv2.putText(out, tag, (lx + 2, ly - 2),
                    cv2.FONT_HERSHEY_SIMPLEX, fs, (0, 0, 0), 1, cv2.LINE_AA)

        # Trail
        trail = obj.get('trail', [])
        tlen = len(trail)
        for i in range(1, tlen):
            alpha = i / max(tlen, 1)
            thickness = max(1, int(alpha * 2))
            tc = tuple(int(c * (0.3 + 0.7 * alpha)) for c in color)
            cv2.line(out, trail[i - 1], trail[i], tc, thickness, cv2.LINE_AA)

    # ── HUD (direct draw, no blending) ──
    cv2.rectangle(out, (0, 0), (w, 34), (8, 8, 16), -1)

    cv2.putText(out, tracker.direction.upper(), (8, 23),
                cv2.FONT_HERSHEY_DUPLEX, 0.5, (0, 255, 180), 2, cv2.LINE_AA)

    gt = tracker.compute_green_time(metrics)
    hud = (f"Q:{metrics['queue_count']}  "
           f"P:{metrics['passed']}  "
           f"D:{metrics['density']:.0%}  "
           f"GT:{gt}s")
    cv2.putText(out, hud, (100, 23),
                cv2.FONT_HERSHEY_SIMPLEX, 0.38, (180, 220, 255), 1, cv2.LINE_AA)

    cv2.circle(out, (w - 14, 17), 6, (0, 255, 0), -1)

    # Bottom: passed class breakdown
    bx = 6
    by = h - 8
    for cls, cnt in sorted(tracker.by_class.items()):
        badge = f"{cls}:{cnt}"
        (bw_t, bh_t), _ = cv2.getTextSize(badge, cv2.FONT_HERSHEY_SIMPLEX, 0.3, 1)
        cv2.rectangle(out, (bx, by - bh_t - 4), (bx + bw_t + 6, by + 2), (30, 30, 50), -1)
        cv2.putText(out, badge, (bx + 3, by - 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.3, (140, 200, 160), 1, cv2.LINE_AA)
        bx += bw_t + 10

    return out


# ══════════════════════════════════════════════════════════════
# PROGRESS FILE
# ══════════════════════════════════════════════════════════════

def write_progress(data):
    try:
        with open(PROGRESS_FILE, 'w') as f:
            json.dump(data, f)
    except:
        pass


# ══════════════════════════════════════════════════════════════
# MAIN: ALL 4 DIRECTIONS EVERY FRAME — QUEUE-BASED
# ══════════════════════════════════════════════════════════════

def detect_cars_4(video_files):
    """
    4-way 2x2 grid — ALL 4 directions detected EVERY frame.
    Zone-based queue detection for real-time signal timing.

    Args: [north.mp4, south.mp4, west.mp4, east.mp4]
    Returns: [north_count, south_count, west_count, east_count]
    """
    directions = ['North', 'South', 'West', 'East']

    print("\n" + "=" * 60)
    print("  TRAFFIC QUEUE ANALYZER v7.0")
    print("  Zone-based queue detection — ALL 4 active")
    print("=" * 60)

    print(f"\n  Loading {Cfg.MODEL}...")
    model = YOLO(Cfg.MODEL)
    print("  Model ready!\n")

    caps = []
    fps_vals = []
    for i, vf in enumerate(video_files):
        cap = cv2.VideoCapture(vf)
        if not cap.isOpened():
            print(f"  [ERROR] Cannot open: {vf}")
            return [0, 0, 0, 0]
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 25
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        print(f"  [{directions[i]:5s}] {vf}  ({w}x{h} @{fps:.0f}fps, {total} frames)")
        caps.append(cap)
        fps_vals.append(fps)

    trackers = [QueueTracker(d, fps_vals[i]) for i, d in enumerate(directions)]
    scales = []
    for cap in caps:
        ow = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        oh = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        scales.append((Cfg.CELL_W / ow, Cfg.CELL_H / oh))

    # Save frames to disk for web dashboard (no popup window)
    frames_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'frames')
    os.makedirs(frames_dir, exist_ok=True)
    dir_names_lower = ['north', 'south', 'west', 'east']

    frame_counter = 0
    start_time = time.time()
    max_frames = max(int(c.get(cv2.CAP_PROP_FRAME_COUNT)) for c in caps)
    panels = [None] * 4
    line_y = int(Cfg.CELL_H * Cfg.LINE_RATIO)

    # Check CUDA availability for FP16 (safe fallback)
    use_half = False
    device = 'cpu'
    try:
        import torch
        if torch.cuda.is_available():
            use_half = True
            device = 'cuda'
    except ImportError:
        pass
    print(f"  Device: {device}" + (" (FP16 enabled)" if use_half else " (FP32)"))
    print(f"  Frame skip: {Cfg.FRAME_SKIP} (process every {Cfg.FRAME_SKIP+1} frames)")
    print(f"  Mode: All 4 directions detected every frame (maximum accuracy)")
    print("=" * 60)

    while True:
        all_ok = True

        # Read ALL frames (to keep videos in sync)
        raws = []
        for idx in range(4):
            ret, raw = caps[idx].read()
            if not ret:
                all_ok = False
                break
            raws.append(raw)

        if not all_ok or len(raws) < 4:
            print("\n  End of video(s).")
            break

        frame_counter += 1

        # Frame skipping (if enabled)
        if Cfg.FRAME_SKIP > 0 and (frame_counter % (Cfg.FRAME_SKIP + 1)) != 0:
            continue

        # Detect ALL 4 directions every frame (no round-robin = boxes stick to cars)
        for idx in range(4):
            display = cv2.resize(raws[idx], (Cfg.CELL_W, Cfg.CELL_H))
            sx, sy = scales[idx]

            # Run YOLO on this direction
            results = model(raws[idx], conf=Cfg.CONF, iou=Cfg.IOU,
                            classes=Cfg.CLASSES, imgsz=Cfg.IMGSZ,
                            verbose=False, half=use_half)
            dets = []
            if results[0].boxes is not None:
                boxes = results[0].boxes.xyxy.cpu().numpy()
                confs = results[0].boxes.conf.cpu().numpy()
                clss  = results[0].boxes.cls.cpu().numpy().astype(int)
                for box, conf, cls_id in zip(boxes, confs, clss):
                    x1 = int(box[0] * sx)
                    y1 = int(box[1] * sy)
                    x2 = int(box[2] * sx)
                    y2 = int(box[3] * sy)
                    dets.append((x1, y1, x2, y2, float(conf), int(cls_id)))
            trackers[idx].update(dets, Cfg.CELL_H)

            panels[idx] = draw_panel(display, trackers[idx], line_y)

            # Save frame to disk for dashboard
            if frame_counter % Cfg.SAVE_EVERY == 0:
                try:
                    cv2.imwrite(os.path.join(frames_dir, f'{dir_names_lower[idx]}.jpg'), panels[idx], [cv2.IMWRITE_JPEG_QUALITY, 70])
                except:
                    pass

        if not all_ok:
            print("\n  End of video(s).")
            break

        # Write live progress
        if frame_counter % Cfg.PROGRESS_EVERY == 0:
            elapsed_now = time.time() - start_time
            fps_now = frame_counter / elapsed_now if elapsed_now > 0 else 0
            progress_pct = (frame_counter / max_frames * 100) if max_frames > 0 else 0

            dir_metrics = {}
            for i, d in enumerate(['north', 'south', 'west', 'east']):
                m = trackers[i].get_queue_metrics()
                m['green_time'] = trackers[i].compute_green_time(m)
                dir_metrics[d] = m

            write_progress({
                'status': 'detecting',
                'frame': frame_counter,
                'total_frames': max_frames,
                'progress': round(progress_pct, 1),
                'fps': round(fps_now, 1),
                'elapsed': round(elapsed_now, 1),
                'directions': dir_metrics,
                'vehicle_counts': {
                    d: dir_metrics[d]['total_unique'] for d in ['north','south','west','east']
                },
                'active': {
                    d: dir_metrics[d]['active'] for d in ['north','south','west','east']
                },
            })

        # No popup window — frames are saved to disk for the web UI

    for cap in caps:
        cap.release()
    # Clean up (no windows to destroy)

    elapsed = time.time() - start_time
    fps_f = frame_counter / elapsed if elapsed > 0 else 0

    # Final metrics
    final_metrics = {}
    counts = []
    for i, d in enumerate(directions):
        m = trackers[i].get_queue_metrics()
        m['green_time'] = trackers[i].compute_green_time(m)
        final_metrics[d.lower()] = m
        counts.append(m['total_unique'])

    print(f"\n{'=' * 60}")
    print("  FINAL TRAFFIC ANALYSIS")
    print(f"{'=' * 60}")
    for i, d in enumerate(directions):
        m = final_metrics[d.lower()]
        print(f"  {d:6s}: Unique={m['total_unique']:4d}  "
              f"Queue={m['queue_length']}  "
              f"Density={m['queue_density']:.0%}  "
              f"MaxWait={m['max_wait_secs']}s  "
              f"GreenTime={m['green_time']}s")
        for cls, cnt in trackers[i].by_class.items():
            print(f"          {cls}: {cnt}")
    print(f"  {'TOTAL':6s}: {sum(counts)} unique vehicles")
    print(f"  Frames: {frame_counter} | Time: {elapsed:.1f}s | {fps_f:.1f} FPS")
    print(f"{'=' * 60}")

    # Write final progress
    write_progress({
        'status': 'done',
        'vehicle_counts': {
            'north': counts[0], 'south': counts[1],
            'west': counts[2], 'east': counts[3],
        },
        'directions': final_metrics,
        'progress': 100,
        'frame': frame_counter,
        'total_frames': max_frames,
    })

    return counts


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--north", required=True)
    ap.add_argument("--south", required=True)
    ap.add_argument("--west",  required=True)
    ap.add_argument("--east",  required=True)
    args = ap.parse_args()
    counts = detect_cars_4([args.north, args.south, args.west, args.east])
    print(json.dumps({"counts": counts}))
