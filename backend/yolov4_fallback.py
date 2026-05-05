import cv2 as cv
import time
from collections import deque
import numpy as np
from scipy.signal import find_peaks, savgol_filter

def calculate_iou(box1, box2):
    """Calculate Intersection over Union (IoU) of two bounding boxes"""
    x1, y1, w1, h1 = box1[0], box1[1], box1[2], box1[3]
    x2, y2, w2, h2 = box2[0], box2[1], box2[2], box2[3]

    # Calculate intersection
    xi1 = max(x1, x2)
    yi1 = max(y1, y2)
    xi2 = min(x1 + w1, x2 + w2)
    yi2 = min(y1 + h1, y2 + h2)

    inter_area = max(0, xi2 - xi1) * max(0, yi2 - yi1)

    # Calculate union
    box1_area = w1 * h1
    box2_area = w2 * h2
    union_area = box1_area + box2_area - inter_area

    if union_area == 0:
        return 0

    return inter_area / union_area

def calculate_centroid_distance(box1, box2):
    """Calculate Euclidean distance between centroids of two boxes"""
    x1_center = box1[0] + box1[2] / 2
    y1_center = box1[1] + box1[3] / 2
    x2_center = box2[0] + box2[2] / 2
    y2_center = box2[1] + box2[3] / 2

    distance = np.sqrt((x1_center - x2_center)**2 + (y1_center - y2_center)**2)
    return distance

def get_centroid(box):
    """Get centroid coordinates of a bounding box"""
    x, y, w, h = box
    cx = x + w / 2
    cy = y + h / 2
    return (int(cx), int(cy))

class ImprovedVehicleTracker:
    """Enhanced vehicle tracker with velocity prediction, counting line, and better tracking"""
    def __init__(self, max_disappeared=15, counting_line_position=0.55):
        self.next_object_id = 0
        self.objects = {}  # ID -> (box, class_id, disappeared_count, counted)
        self.disappeared = {}
        self.max_disappeared = max_disappeared
        self.velocities = {}  # ID -> list of (dx, dy) velocity vectors
        self.centroid_history = {}  # ID -> list of (cx, cy) centroid positions
        self.counting_line_position = counting_line_position
        self.counted_ids = set()  # Track which IDs have been counted
        self.total_count = 0
        self.crossing_state = {}  # ID -> 'above' or 'below' (for line crossing verification)

    def register(self, box, class_id):
        """Register a new vehicle with a unique ID"""
        self.objects[self.next_object_id] = (box, class_id, 0, False)
        self.disappeared[self.next_object_id] = 0
        self.velocities[self.next_object_id] = []
        centroid = get_centroid(box)
        self.centroid_history[self.next_object_id] = [centroid]
        self.next_object_id += 1

    def deregister(self, object_id):
        """Remove a vehicle that has disappeared"""
        if object_id in self.objects:
            del self.objects[object_id]
        if object_id in self.disappeared:
            del self.disappeared[object_id]
        if object_id in self.velocities:
            del self.velocities[object_id]
        if object_id in self.centroid_history:
            del self.centroid_history[object_id]
        if object_id in self.crossing_state:
            del self.crossing_state[object_id]

    def predict_position(self, object_id):
        """Predict next position based on velocity history"""
        if object_id not in self.velocities or len(self.velocities[object_id]) < 2:
            return None
        
        # Average recent velocities (last 5 frames)
        recent_vels = self.velocities[object_id][-5:]
        avg_dx = np.mean([v[0] for v in recent_vels])
        avg_dy = np.mean([v[1] for v in recent_vels])
        
        box = self.objects[object_id][0]
        x, y, w, h = box
        
        # Predict new position
        pred_x = int(x + avg_dx)
        pred_y = int(y + avg_dy)
        
        return (pred_x, pred_y, w, h)

    def check_counting_line(self, object_id, box, frame_height):
        """Check if vehicle crossed the counting line using direction-aware crossing detection"""
        if object_id in self.counted_ids:
            return False

        cy = box[1] + box[3] / 2  # Centroid Y
        counting_y = frame_height * self.counting_line_position

        # Initialize crossing state on first encounter
        if object_id not in self.crossing_state:
            if cy < counting_y:
                self.crossing_state[object_id] = 'above'
            else:
                self.crossing_state[object_id] = 'below'
            return False  # Don't count on first appearance

        # Check for actual crossing (above->below OR below->above)
        prev_state = self.crossing_state[object_id]
        
        threshold = 15  # pixels tolerance for being "on" the line
        
        if prev_state == 'above' and cy >= counting_y - threshold:
            # Vehicle crossed from above to below (or reached the line)
            self.crossing_state[object_id] = 'below'
            if object_id not in self.counted_ids:
                self.counted_ids.add(object_id)
                self.total_count += 1
                return True
        elif prev_state == 'below' and cy < counting_y - threshold:
            # Vehicle crossed from below to above
            self.crossing_state[object_id] = 'above'
            if object_id not in self.counted_ids:
                self.counted_ids.add(object_id)
                self.total_count += 1
                return True

        return False

    def update(self, detections, frame_height):
        """
        Update tracked vehicles with new detections
        detections: list of (box, class_id) tuples
        Returns: dict of {object_id: (box, class_id, disappeared_count, just_counted)}
        """
        # If no detections, increment disappeared counter
        if len(detections) == 0:
            for object_id in list(self.objects.keys()):
                self.disappeared[object_id] += 1
                if self.disappeared[object_id] > self.max_disappeared:
                    self.deregister(object_id)
            return self.objects

        # If no existing objects, register all detections
        if len(self.objects) == 0:
            for box, class_id in detections:
                self.register(box, class_id)
                # Initialize crossing state (don't count on first appearance)
                new_id = self.next_object_id - 1
                cy = box[1] + box[3] / 2
                counting_y = frame_height * self.counting_line_position
                self.crossing_state[new_id] = 'above' if cy < counting_y else 'below'
            return self.objects

        # Get current object IDs and boxes
        object_ids = list(self.objects.keys())
        object_boxes = [self.objects[oid][0] for oid in object_ids]

        # Use predicted positions for better matching if available
        predicted_boxes = []
        for oid in object_ids:
            pred = self.predict_position(oid)
            if pred is not None:
                predicted_boxes.append(pred)
            else:
                predicted_boxes.append(self.objects[oid][0])

        # Calculate matching matrix using both actual and predicted positions
        detection_boxes = [det[0] for det in detections]
        D = np.zeros((len(object_boxes), len(detection_boxes)))

        for i, (obj_box, pred_box) in enumerate(zip(object_boxes, predicted_boxes)):
            for j, det_box in enumerate(detection_boxes):
                # IoU with actual position
                iou_actual = calculate_iou(obj_box, det_box)
                # IoU with predicted position
                iou_predicted = calculate_iou(pred_box, det_box)
                # Use the better IoU
                iou = max(iou_actual, iou_predicted)
                
                # Distance from actual position
                dist_actual = calculate_centroid_distance(obj_box, det_box)
                # Distance from predicted position
                dist_predicted = calculate_centroid_distance(pred_box, det_box)
                # Use the shorter distance
                dist = min(dist_actual, dist_predicted)
                
                # Wider normalization range for fast-moving vehicles
                norm_dist = min(dist / 250.0, 1.0)
                D[i][j] = (1 - iou) + norm_dist

        # Hungarian-style greedy matching (sorted by best match)
        rows = D.min(axis=1).argsort()
        cols = D.argmin(axis=1)[rows]

        used_rows = set()
        used_cols = set()

        # Update matched objects
        for row, col in zip(rows, cols):
            if row in used_rows or col in used_cols:
                continue

            obj_box = object_boxes[row]
            pred_box = predicted_boxes[row]
            det_box, det_class = detections[col]
            
            iou_actual = calculate_iou(obj_box, det_box)
            iou_predicted = calculate_iou(pred_box, det_box)
            iou = max(iou_actual, iou_predicted)
            
            dist_actual = calculate_centroid_distance(obj_box, det_box)
            dist_predicted = calculate_centroid_distance(pred_box, det_box)
            dist = min(dist_actual, dist_predicted)

            # More lenient matching for better tracking continuity
            if iou > 0.2 or dist < 120:
                object_id = object_ids[row]
                box, class_id, _, was_counted = self.objects[object_id]

                # Update velocity
                old_centroid = get_centroid(obj_box)
                new_centroid = get_centroid(det_box)
                dx = new_centroid[0] - old_centroid[0]
                dy = new_centroid[1] - old_centroid[1]
                self.velocities[object_id].append((dx, dy))
                # Keep only last 10 velocity entries
                if len(self.velocities[object_id]) > 10:
                    self.velocities[object_id] = self.velocities[object_id][-10:]
                
                # Update centroid history
                self.centroid_history[object_id].append(new_centroid)
                if len(self.centroid_history[object_id]) > 30:
                    self.centroid_history[object_id] = self.centroid_history[object_id][-30:]

                # Check counting line crossing
                just_counted = self.check_counting_line(object_id, det_box, frame_height)

                self.objects[object_id] = (det_box, det_class, 0, was_counted or just_counted)
                self.disappeared[object_id] = 0
                used_rows.add(row)
                used_cols.add(col)

        # Mark unmatched objects as disappeared
        unused_rows = set(range(len(object_boxes))) - used_rows
        for row in unused_rows:
            object_id = object_ids[row]
            self.disappeared[object_id] += 1
            if self.disappeared[object_id] > self.max_disappeared:
                self.deregister(object_id)

        # Register new detections
        unused_cols = set(range(len(detections))) - used_cols
        for col in unused_cols:
            det_box, det_class = detections[col]
            self.register(det_box, det_class)
            # Initialize crossing state
            new_id = self.next_object_id - 1
            cy = det_box[1] + det_box[3] / 2
            counting_y = frame_height * self.counting_line_position
            self.crossing_state[new_id] = 'above' if cy < counting_y else 'below'

        return self.objects

    def get_count(self):
        """Get total number of vehicles counted"""
        return self.total_count

    def get_active_count(self):
        """Get number of currently tracked vehicles"""
        return len([obj for obj in self.objects.values() if obj[2] < 2])

def detect_cars_4(video_files):
    """
    Improved detection with better accuracy, multi-scale inference,
    velocity-based tracking, and direction-aware counting line
    """
    # Optimized thresholds for better detection
    Conf_threshold = 0.25   # Lower for better recall (catch more vehicles)
    NMS_threshold = 0.50    # Higher NMS to keep overlapping vehicles separate

    # Define colors for different classes
    COLORS = [(0, 255, 0), (0, 0, 255), (255, 0, 0),
              (255, 255, 0), (255, 0, 255), (0, 255, 255)]

    # Load class names from file
    class_name = []
    with open('classes.txt', 'r') as f:
        class_name = [cname.strip() for cname in f.readlines()]

    # Vehicle class indices — now including bicycle
    vehicle_classes = ['bicycle', 'car', 'bus', 'truck', 'motorbike']
    vehicle_indices = [class_name.index(v) for v in vehicle_classes if v in class_name]
    print(f"Detecting vehicle classes: {[class_name[i] for i in vehicle_indices]}")

    # Direction labels for each video
    directions = ['North', 'South', 'West', 'East']

    # Load the network
    print("Loading YOLOv4 model...")
    net = cv.dnn.readNet('yolov4-tiny.weights', 'yolov4-tiny.cfg')
    net.setPreferableBackend(cv.dnn.DNN_BACKEND_OPENCV)
    net.setPreferableTarget(cv.dnn.DNN_TARGET_CPU)

    # Initialize the detection model with HIGHER resolution for better accuracy
    model = cv.dnn_DetectionModel(net)
    model.setInputParams(size=(608, 608), scale=1/255, swapRB=True)
    print("Model loaded successfully! (608x608 input resolution)")

    # Open all 4 video files
    caps = [cv.VideoCapture(p) for p in video_files]

    # Check if videos opened successfully
    for idx, cap in enumerate(caps):
        if not cap.isOpened():
            print(f"ERROR: Could not open video {idx}: {video_files[idx]}")
            return [0, 0, 0, 0]

    # Get video properties
    fps_list = []
    frame_heights = []
    frame_widths = []

    for cap in caps:
        fps = cap.get(cv.CAP_PROP_FPS)
        h = int(cap.get(cv.CAP_PROP_FRAME_HEIGHT))
        w = int(cap.get(cv.CAP_PROP_FRAME_WIDTH))
        fps_list.append(fps if fps > 0 else 30)
        frame_heights.append(h)
        frame_widths.append(w)
        print(f"  Video: {w}x{h} @ {fps:.1f} FPS")

    # Initialize improved trackers for each direction with better persistence
    vehicle_trackers = [ImprovedVehicleTracker(max_disappeared=15, counting_line_position=0.55)
                       for _ in range(4)]

    # Statistics tracking
    frame_counter = 0
    process_every_n_frames = 1  # Process every frame for accuracy

    # Create window for 2x2 grid display
    window_name = '4-Way Traffic Analysis'
    cv.namedWindow(window_name, cv.WINDOW_NORMAL)
    cv.resizeWindow(window_name, 1280, 800)

    print("Starting video processing...")
    print("Detection window created - processing frames...")
    print("=" * 60)

    while True:
        frames = []
        all_ok = True

        for idx, cap in enumerate(caps):
            ret, frame = cap.read()
            if not ret:
                all_ok = False
                break

            h_frame, w_frame = frame.shape[:2]

            # Process this frame
            if frame_counter % process_every_n_frames == 0:
                # ---- Multi-scale detection for better accuracy ----
                all_detections = []
                
                # Primary detection at full frame
                classes1, scores1, boxes1 = model.detect(frame, Conf_threshold, NMS_threshold)
                
                if len(classes1) > 0:
                    for classid, score, box in zip(classes1, scores1, boxes1):
                        if classid in vehicle_indices:
                            all_detections.append((classid, float(score), tuple(box)))
                
                # Secondary detection: analyze top half of frame with boosted resolution
                # (catches distant/small vehicles near horizon)
                top_half = frame[0:h_frame//2, :]
                if top_half.shape[0] > 100:  # Only if top half is big enough
                    classes2, scores2, boxes2 = model.detect(top_half, Conf_threshold, NMS_threshold)
                    if len(classes2) > 0:
                        for classid, score, box in zip(classes2, scores2, boxes2):
                            if classid in vehicle_indices:
                                # Adjust box coordinates back to full frame
                                adjusted_box = (int(box[0]), int(box[1]), int(box[2]), int(box[3]))
                                # Only add if not already detected (check overlap with existing)
                                is_duplicate = False
                                for _, _, existing_box in all_detections:
                                    if calculate_iou(adjusted_box, existing_box) > 0.3:
                                        is_duplicate = True
                                        break
                                if not is_duplicate:
                                    all_detections.append((classid, float(score), adjusted_box))

                # Filter and validate detections
                detections = []
                MIN_BOX_WIDTH = 20    # Reduced for small/distant vehicles
                MIN_BOX_HEIGHT = 20
                MIN_BOX_AREA = 600    # Lower threshold for motorcycles/bicycles
                MAX_BOX_RATIO = 5.0   # Max aspect ratio to filter noise

                for classid, score, box in all_detections:
                    x, y, w, h = int(box[0]), int(box[1]), int(box[2]), int(box[3])

                    # Validate box dimensions and position
                    aspect_ratio = max(w, h) / (min(w, h) + 1e-6)
                    if (x >= 0 and y >= 0 and
                        x + w <= w_frame and y + h <= h_frame and
                        w >= MIN_BOX_WIDTH and h >= MIN_BOX_HEIGHT and
                        w * h >= MIN_BOX_AREA and
                        aspect_ratio < MAX_BOX_RATIO):
                        detections.append(((x, y, w, h), classid))

                # Update tracker with current detections
                tracked_objects = vehicle_trackers[idx].update(detections, h_frame)
            else:
                tracked_objects = vehicle_trackers[idx].objects

            # Draw counting line (horizontal line at 55% of frame height)
            counting_y = int(h_frame * 0.55)
            cv.line(frame, (0, counting_y), (w_frame, counting_y), (0, 255, 255), 2)
            cv.putText(frame, "COUNTING LINE", (10, counting_y - 10),
                      cv.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

            # Draw tracked vehicles
            for object_id, (box, class_id, disappeared_count, was_counted) in tracked_objects.items():
                # Only draw actively tracked vehicles (not disappeared)
                if disappeared_count > 2:
                    continue

                x, y, w, h = box

                # Validate boundaries
                if x < 0 or y < 0 or x + w > w_frame or y + h > h_frame:
                    continue

                # Choose color based on counted status
                if was_counted or object_id in vehicle_trackers[idx].counted_ids:
                    color = (0, 255, 0)  # Green for counted
                    status = "COUNTED"
                else:
                    color = COLORS[int(class_id) % len(COLORS)]
                    status = "TRACKING"

                vehicle_name = class_name[class_id]
                label = f"ID:{object_id} {vehicle_name} [{status}]"

                # Draw bounding box
                cv.rectangle(frame, (x, y), (x + w, y + h), color, 2)

                # Draw centroid
                cx, cy = get_centroid(box)
                cv.circle(frame, (cx, cy), 4, color, -1)
                
                # Draw trajectory trail (last 15 positions)
                if object_id in vehicle_trackers[idx].centroid_history:
                    history = vehicle_trackers[idx].centroid_history[object_id]
                    for k in range(1, len(history)):
                        if k >= len(history):
                            break
                        # Fade trail: more recent = brighter
                        alpha = k / len(history)
                        trail_color = (int(color[0] * alpha), int(color[1] * alpha), int(color[2] * alpha))
                        cv.line(frame, history[k-1], history[k], trail_color, 2)

                # Draw label with background
                label_size, _ = cv.getTextSize(label, cv.FONT_HERSHEY_SIMPLEX, 0.5, 2)
                cv.rectangle(frame, (x, y - label_size[1] - 10),
                           (x + label_size[0], y), color, -1)
                cv.putText(frame, label, (x, y - 5),
                          cv.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

            # Get counts
            total_counted = vehicle_trackers[idx].get_count()
            active_vehicles = vehicle_trackers[idx].get_active_count()

            # Display information on frame
            direction_label = directions[idx]

            # Draw info panel with semi-transparent background
            overlay = frame.copy()
            cv.rectangle(overlay, (10, 10), (w_frame - 10, 130), (0, 0, 0), -1)
            cv.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

            # Display direction and counts
            y_offset = 40
            cv.putText(frame, f"{direction_label} Direction", (20, y_offset),
                      cv.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
            y_offset += 30
            cv.putText(frame, f"Counted: {total_counted}", (20, y_offset),
                      cv.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            y_offset += 25
            cv.putText(frame, f"Active: {active_vehicles}", (20, y_offset),
                      cv.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

            frames.append(frame)

        if not all_ok:
            print("End of video(s) reached.")
            break

        frame_counter += 1

        # Create 2x2 grid display
        h, w = 360, 640
        frames_resized = [cv.resize(f, (w, h)) for f in frames]

        # Stack frames: [0 1]
        #                [2 3]
        top = np.hstack(frames_resized[0:2])
        bottom = np.hstack(frames_resized[2:4])
        grid = np.vstack((top, bottom))

        # Add overall statistics
        total_counted = sum([vehicle_trackers[i].get_count() for i in range(4)])
        total_active = sum([vehicle_trackers[i].get_active_count() for i in range(4)])

        # Draw title bar
        title_bar = np.zeros((60, grid.shape[1], 3), dtype=np.uint8)
        cv.putText(title_bar, f"TOTAL COUNTED: {total_counted}  |  ACTIVE: {total_active}  |  Frame: {frame_counter}",
                  (20, 40), cv.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)

        # Combine title bar with grid
        grid = np.vstack((title_bar, grid))

        # Add instruction at bottom
        cv.putText(grid, "Press 'q' to quit | 'p' to pause",
                  (20, grid.shape[0] - 20),
                  cv.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        # Display the 2x2 grid window
        cv.imshow(window_name, grid)

        # Wait for key press (critical for window refresh)
        key = cv.waitKey(1) & 0xFF
        if key == ord('q'):
            print("Quit requested by user.")
            break
        elif key == ord('p'):
            print("Paused. Press any key to continue...")
            cv.waitKey(0)

    # Cleanup
    for cap in caps:
        cap.release()
    cv.destroyAllWindows()

    # Get final counts from each tracker
    final_counts = []
    print("\n" + "=" * 60)
    print("FINAL VEHICLE COUNTS:")
    print("=" * 60)

    for idx in range(4):
        count = vehicle_trackers[idx].get_count()
        final_counts.append(count)
        active = vehicle_trackers[idx].get_active_count()
        total_tracked = vehicle_trackers[idx].next_object_id
        print(f"{directions[idx]:6} Direction: {count:3} vehicles (tracked {total_tracked} unique IDs)")

    print("=" * 60)
    print(f"TOTAL: {sum(final_counts)} vehicles across all directions")
    print("=" * 60)

    return final_counts
