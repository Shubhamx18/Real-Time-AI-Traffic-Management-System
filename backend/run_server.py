import os
import sys
import time
import threading

# Ensure we're in the correct directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Import required modules
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import traceback
import subprocess
import json
from algo import optimize_traffic

# Create Flask app
app = Flask(__name__)
CORS(app)
app.config['PROPAGATE_EXCEPTIONS'] = True

DETECTION_ENGINE = "YOLOv8s + CentroidTracker"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROGRESS_FILE = os.path.join(BASE_DIR, 'detection_progress.json')
FRAMES_DIR = os.path.join(BASE_DIR, 'frames')
ANALYTICS_FILE = os.path.join(BASE_DIR, 'analytics_history.json')
SETTINGS_FILE = os.path.join(BASE_DIR, 'settings.json')
SYSTEM_STATS_FILE = os.path.join(BASE_DIR, 'system_stats.json')

os.makedirs(FRAMES_DIR, exist_ok=True)

# ══════════════════════════════════════════════════════════════
# DEFAULT SETTINGS
# ══════════════════════════════════════════════════════════════

DEFAULT_SETTINGS = {
    "detection": {
        "model": "YOLOv8x",
        "confidence_threshold": 0.20,
        "iou_threshold": 0.45,
        "image_size": 416,
        "max_disappeared": 15,
        "min_track_frames": 8,
        "frame_skip": 0,
    },
    "signal": {
        "base_green_time": 10,
        "max_green_time": 60,
        "yellow_time": 3,
        "all_red_time": 2,
        "cycle_time": 148,
        "auto_mode": True,
        "emergency_preemption": True,
        "pedestrian_phase": False,
    },
    "display": {
        "frame_quality": 70,
        "frame_refresh_rate": 500,
        "show_trails": True,
        "show_bounding_boxes": True,
        "show_confidence": True,
        "show_vehicle_count": True,
        "theme": "dark",
    },
    "alerts": {
        "congestion_threshold": 15,
        "low_traffic_threshold": 2,
        "emergency_vehicle_alert": True,
        "email_notifications": False,
        "sound_alerts": True,
    },
    "system": {
        "log_level": "info",
        "max_video_duration": 1200,
        "auto_cleanup_frames": True,
        "data_retention_days": 30,
    }
}

# ══════════════════════════════════════════════════════════════
# SYSTEM TRACKING
# ══════════════════════════════════════════════════════════════

system_start_time = time.time()
detection_history = []  # Track all detection runs
active_alerts = []
detection_count = 0
active_process = None  # Track running detection subprocess


def load_settings():
    """Load settings from file or return defaults."""
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r') as f:
                saved = json.load(f)
            # Merge with defaults to ensure all keys exist
            merged = DEFAULT_SETTINGS.copy()
            for category in saved:
                if category in merged:
                    merged[category].update(saved[category])
            return merged
    except:
        pass
    return DEFAULT_SETTINGS.copy()


def save_settings(settings):
    """Persist settings to file."""
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)
        return True
    except:
        return False


def load_analytics():
    """Load analytics history from file."""
    try:
        if os.path.exists(ANALYTICS_FILE):
            with open(ANALYTICS_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return {"runs": [], "daily_stats": {}, "hourly_distribution": {}}


def save_analytics(data):
    """Persist analytics to file."""
    try:
        with open(ANALYTICS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except:
        pass


def record_detection_run(vehicle_counts, green_times, elapsed_time):
    """Record a detection run for analytics."""
    global detection_count
    detection_count += 1
    
    analytics = load_analytics()
    
    run_data = {
        "id": detection_count,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "date": time.strftime("%Y-%m-%d"),
        "hour": int(time.strftime("%H")),
        "vehicle_counts": vehicle_counts,
        "green_times": green_times,
        "total_vehicles": sum(vehicle_counts.values()) if isinstance(vehicle_counts, dict) else sum(vehicle_counts),
        "elapsed_time": round(elapsed_time, 1),
        "detection_engine": DETECTION_ENGINE,
    }
    
    analytics["runs"].append(run_data)
    
    # Keep last 100 runs
    if len(analytics["runs"]) > 100:
        analytics["runs"] = analytics["runs"][-100:]
    
    # Update daily stats
    today = time.strftime("%Y-%m-%d")
    if today not in analytics["daily_stats"]:
        analytics["daily_stats"][today] = {
            "total_vehicles": 0,
            "total_runs": 0,
            "peak_vehicles": 0,
            "avg_vehicles_per_run": 0,
            "directions": {"north": 0, "south": 0, "east": 0, "west": 0}
        }
    
    daily = analytics["daily_stats"][today]
    total = run_data["total_vehicles"]
    daily["total_vehicles"] += total
    daily["total_runs"] += 1
    daily["peak_vehicles"] = max(daily["peak_vehicles"], total)
    daily["avg_vehicles_per_run"] = daily["total_vehicles"] // daily["total_runs"]
    
    if isinstance(vehicle_counts, dict):
        for d in ["north", "south", "east", "west"]:
            daily["directions"][d] += vehicle_counts.get(d, 0)
    
    # Update hourly distribution
    hour = str(int(time.strftime("%H")))
    if hour not in analytics["hourly_distribution"]:
        analytics["hourly_distribution"][hour] = 0
    analytics["hourly_distribution"][hour] += total
    
    save_analytics(analytics)
    return run_data


# ══════════════════════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════════════════════

@app.route('/frame/<direction>', methods=['GET'])
def get_frame(direction):
    """Serve latest detection frame for a direction (north/south/east/west)."""
    if direction not in ['north', 'south', 'east', 'west']:
        return jsonify({'error': 'Invalid direction'}), 400
    frame_path = os.path.join(FRAMES_DIR, f'{direction}.jpg')
    if os.path.exists(frame_path):
        return send_file(frame_path, mimetype='image/jpeg', max_age=0)
    else:
        return jsonify({'error': 'No frame available'}), 404


@app.route('/progress', methods=['GET'])
def get_progress():
    """Return live detection progress from the detection subprocess."""
    try:
        if os.path.exists(PROGRESS_FILE):
            with open(PROGRESS_FILE, 'r') as f:
                data = json.load(f)
            return jsonify(data)
        else:
            return jsonify({'status': 'idle'})
    except:
        return jsonify({'status': 'idle'})


@app.route('/upload', methods=['POST'])
def upload_files():
    try:
        # Clear old progress
        if os.path.exists(PROGRESS_FILE):
            os.remove(PROGRESS_FILE)

        files = request.files.getlist('videos')
        if len(files) != 4:
            return jsonify({'error': 'Please upload exactly 4 videos'}), 400

        video_paths = []
        for i, file in enumerate(files):
            video_path = os.path.join('uploads', f'video_{i}.mp4')
            file.save(video_path)
            video_paths.append(video_path)

        print(f"\nProcessing {len(video_paths)} videos...")
        print(f"Using: {DETECTION_ENGINE}")
        print("Launching detection in separate process...")

        start_time = time.time()

        # Run detection in separate process
        python_exe = os.path.join('venv', 'Scripts', 'python.exe')
        if not os.path.exists(python_exe):
            python_exe = 'python'

        cmd = [python_exe, 'run_detection.py', json.dumps(video_paths)]

        print(f"Running command: {' '.join(cmd)}")

        try:
            global active_process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )
            active_process = process
            # 20 minute timeout
            stdout, stderr = process.communicate(timeout=1200)
            active_process = None

            print("Detection STDERR:", stderr)

            if process.returncode != 0:
                # Check if it was killed by user (taskkill returns 1, kill returns -9)
                if process.returncode in (-9, -15, 1) and not stdout:
                    return jsonify({'status': 'stopped', 'message': 'Detection was stopped by user'}), 200
                print("Detection STDOUT:", stdout)
                raise Exception(f"Detection process failed with return code {process.returncode}")

        except subprocess.TimeoutExpired:
            process.kill()
            active_process = None
            raise Exception("Detection process timed out after 20 minutes")
        except Exception as e:
            active_process = None
            # If user stopped, don't raise as error
            if 'stopped by user' in str(e):
                return jsonify({'status': 'stopped', 'message': 'Detection stopped'}), 200
            raise Exception(f"Failed to run detection process: {str(e)}")

        # Parse results from stdout
        num_cars_list = None
        for line in stdout.split('\n'):
            if 'RESULT_JSON:' in line:
                try:
                    num_cars_list = json.loads(line.split('RESULT_JSON:')[1].strip())
                    break
                except json.JSONDecodeError as e:
                    print(f"JSON decode error: {e}")
                    print(f"Problematic line: {line}")

        if num_cars_list is None:
            print("Detection STDOUT:", stdout)
            print("Detection STDERR:", stderr)
            raise Exception("Failed to get detection results from subprocess. Check if videos are valid.")

        print(f"Vehicle counts detected: {num_cars_list}")

        elapsed = time.time() - start_time

        print("Optimizing traffic lights...")
        result = optimize_traffic(num_cars_list)
        print(f"Optimization complete: {result}")

        # Record analytics
        vehicle_counts = result.get('vehicle_counts', {
            'north': num_cars_list[0],
            'south': num_cars_list[1],
            'west': num_cars_list[2],
            'east': num_cars_list[3],
        })
        green_times = {
            'north': result.get('north', 0),
            'south': result.get('south', 0),
            'west': result.get('west', 0),
            'east': result.get('east', 0),
        }
        record_detection_run(vehicle_counts, green_times, elapsed)

        return jsonify(result)

    except Exception as e:
        print(f"\n[ERROR] ERROR during video processing:")
        print(traceback.format_exc())
        return jsonify({
            'error': f'Error processing videos: {str(e)}',
            'details': 'Check server console for full error details'
        }), 500


@app.route('/stop', methods=['POST'])
def stop_detection():
    """Stop the currently running detection process."""
    global active_process
    if active_process and active_process.poll() is None:
        try:
            pid = active_process.pid
            # On Windows, kill entire process tree
            if sys.platform == 'win32':
                subprocess.run(['taskkill', '/F', '/T', '/PID', str(pid)],
                              capture_output=True, timeout=10)
            else:
                active_process.kill()
            active_process = None
            # Clear progress file
            if os.path.exists(PROGRESS_FILE):
                os.remove(PROGRESS_FILE)
            print(f"[STOP] Detection process (PID {pid}) killed by user")
            return jsonify({'status': 'ok', 'message': 'Detection stopped'})
        except Exception as e:
            print(f"[STOP] Error killing process: {e}")
            active_process = None
            return jsonify({'status': 'ok', 'message': f'Process cleanup attempted: {str(e)}'})
    return jsonify({'status': 'ok', 'message': 'No active detection to stop'})


# ══════════════════════════════════════════════════════════════
# SETTINGS ENDPOINTS
# ══════════════════════════════════════════════════════════════

@app.route('/settings', methods=['GET'])
def get_settings():
    """Get current system settings."""
    return jsonify(load_settings())


@app.route('/settings', methods=['POST'])
def update_settings():
    """Update system settings."""
    try:
        new_settings = request.json
        current = load_settings()
        
        # Deep merge
        for category in new_settings:
            if category in current and isinstance(current[category], dict):
                current[category].update(new_settings[category])
            else:
                current[category] = new_settings[category]
        
        if save_settings(current):
            return jsonify({'status': 'ok', 'settings': current})
        else:
            return jsonify({'error': 'Failed to save settings'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/settings/reset', methods=['POST'])
def reset_settings():
    """Reset settings to defaults."""
    save_settings(DEFAULT_SETTINGS)
    return jsonify({'status': 'ok', 'settings': DEFAULT_SETTINGS})


# ══════════════════════════════════════════════════════════════
# ANALYTICS ENDPOINTS
# ══════════════════════════════════════════════════════════════

@app.route('/analytics', methods=['GET'])
def get_analytics():
    """Get full analytics data."""
    analytics = load_analytics()
    return jsonify(analytics)


@app.route('/analytics/summary', methods=['GET'])
def get_analytics_summary():
    """Get analytics summary for dashboard."""
    analytics = load_analytics()
    today = time.strftime("%Y-%m-%d")
    daily = analytics.get("daily_stats", {}).get(today, {
        "total_vehicles": 0,
        "total_runs": 0,
        "peak_vehicles": 0,
        "avg_vehicles_per_run": 0,
    })
    
    # Calculate peak hour
    hourly = analytics.get("hourly_distribution", {})
    peak_hour = "N/A"
    if hourly:
        peak_h = max(hourly, key=hourly.get)
        ph = int(peak_h)
        peak_hour = f"{ph}:00 - {ph+1}:00"
    
    # Get recent runs for trend
    runs = analytics.get("runs", [])
    recent = runs[-10:] if runs else []
    
    return jsonify({
        "today": daily,
        "peak_hour": peak_hour,
        "total_runs_all_time": len(runs),
        "recent_runs": recent,
        "hourly_distribution": hourly,
    })


@app.route('/analytics/clear', methods=['POST'])
def clear_analytics():
    """Clear all analytics data."""
    save_analytics({"runs": [], "daily_stats": {}, "hourly_distribution": {}})
    return jsonify({'status': 'ok'})


# ══════════════════════════════════════════════════════════════
# SYSTEM STATUS ENDPOINTS
# ══════════════════════════════════════════════════════════════

@app.route('/system/stats', methods=['GET'])
def get_system_stats():
    """Get system performance stats."""
    uptime = time.time() - system_start_time
    
    # Check frame freshness
    frame_ages = {}
    for d in ['north', 'south', 'east', 'west']:
        fp = os.path.join(FRAMES_DIR, f'{d}.jpg')
        if os.path.exists(fp):
            age = time.time() - os.path.getmtime(fp)
            frame_ages[d] = round(age, 1)
        else:
            frame_ages[d] = None
    
    return jsonify({
        'uptime_seconds': round(uptime, 1),
        'uptime_formatted': format_uptime(uptime),
        'detection_engine': DETECTION_ENGINE,
        'total_detections': detection_count,
        'frame_ages': frame_ages,
        'active_alerts': len(active_alerts),
        'settings_loaded': os.path.exists(SETTINGS_FILE),
        'analytics_available': os.path.exists(ANALYTICS_FILE),
        'backend_version': '4.0',
        'status': 'operational',
    })


@app.route('/system/clear-frames', methods=['POST'])
def clear_frames():
    """Clear all detection frames."""
    try:
        for d in ['north', 'south', 'east', 'west']:
            fp = os.path.join(FRAMES_DIR, f'{d}.jpg')
            if os.path.exists(fp):
                os.remove(fp)
        return jsonify({'status': 'ok', 'message': 'Frames cleared'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def format_uptime(seconds):
    """Format seconds into human readable uptime."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'OK',
        'message': 'Backend is running',
        'detection_engine': DETECTION_ENGINE,
        'uptime': format_uptime(time.time() - system_start_time),
        'version': '4.0',
    })


@app.route('/', methods=['GET'])
def index():
    return jsonify({
        'message': 'AI-Based Traffic Management System Backend',
        'version': '4.0',
        'detection_engine': DETECTION_ENGINE,
        'endpoints': {
            '/upload': 'POST - Upload 4 videos for traffic analysis',
            '/health': 'GET - Health check',
            '/progress': 'GET - Live detection progress',
            '/frame/<direction>': 'GET - Latest detection frame',
            '/settings': 'GET/POST - System settings',
            '/settings/reset': 'POST - Reset to defaults',
            '/analytics': 'GET - Full analytics data',
            '/analytics/summary': 'GET - Analytics summary',
            '/analytics/clear': 'POST - Clear analytics',
            '/system/stats': 'GET - System statistics',
            '/system/clear-frames': 'POST - Clear detection frames',
        }
    })


if __name__ == '__main__':
    # Create uploads directory if it doesn't exist
    if not os.path.exists('uploads'):
        os.makedirs('uploads')
        print("Created 'uploads' directory")

    # Clear stale frames from previous session
    for d in ['north', 'south', 'east', 'west']:
        fp = os.path.join(FRAMES_DIR, f'{d}.jpg')
        if os.path.exists(fp):
            os.remove(fp)
    print("Cleared stale detection frames from previous session")

    print("=" * 60)
    print("AI-Based Traffic Management System - Backend Server v4.0")
    print("=" * 60)
    print(f"Detection Engine: {DETECTION_ENGINE}")
    print("Starting Flask server...")
    print("Backend will be available at: http://127.0.0.1:5000")
    print("Health check endpoint: http://127.0.0.1:5000/health")
    print("=" * 60)

    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False, threaded=True)
