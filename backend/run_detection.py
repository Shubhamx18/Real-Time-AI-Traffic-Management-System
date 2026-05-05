import sys
import json
import os

# Ensure we're in the correct directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Import ultra tracker (YOLOv8x + StrongSORT)
from vehicle_tracker_ultra import detect_cars_4
print("[OK] Using YOLOv8x + StrongSORT Ultra Tracker", file=sys.stderr)

if __name__ == '__main__':
    # Get video paths from command line argument
    video_paths = json.loads(sys.argv[1])

    print(f"Processing {len(video_paths)} videos with Ultra Tracker...", file=sys.stderr)

    # Run detection
    num_cars_list = detect_cars_4(video_paths)

    print(f"Detection complete: {num_cars_list}", file=sys.stderr)

    # Output result as JSON (stdout will be captured by parent process)
    print(f"RESULT_JSON:{json.dumps(num_cars_list)}")
