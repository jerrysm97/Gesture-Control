import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import cv2
import threading
import time
from collections import deque
import numpy as np

from tracker import HandTracker
from gestures import GestureClassifier
from controller import MacController

class GestureApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Hand Gesture Control Center v2.1")
        self.root.geometry("1100x750")
        
        # Backend
        self.tracker = HandTracker()
        self.classifier = GestureClassifier()
        self.controller = MacController()
        
        # Metrics
        self.running = True
        self.fps = 0
        self.frame_count = 0
        self.start_time = time.time()
        
        # State Management
        self.is_paused = True # Start Paused
        self.prev_gesture = "None"
        
        # Cursor Smoothing (EMA)
        self.smooth_x = 0.5
        self.smooth_y = 0.5
        self.smoothing_factor = 0.5 
        
        # Calibration (Active Region)
        # Default box (Center 60%)
        self.calib_bounds = {"x_min": 0.2, "x_max": 0.8, "y_min": 0.2, "y_max": 0.8}
        self.calibration_active = False
        self.calib_start_time = 0
        self.calib_duration = 5.0 # Seconds to measure bounds
        self.calib_temp_min_x = 1.0
        self.calib_temp_max_x = 0.0
        self.calib_temp_min_y = 1.0
        self.calib_temp_max_y = 0.0
        
        self.show_calib_box = tk.BooleanVar(value=True)
        
        # Pinch / Click Logic
        self.is_pinching = False
        self.pinch_start_time = 0
        self.is_dragging = False
        self.last_click_time = 0
        
        # Swipe Logic
        self.swipe_history = deque(maxlen=10)
        self.last_swipe_time = 0
        self.swipe_cooldown = 1.0
        
        # UI Setup
        self.main_container = ttk.Frame(root)
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self._setup_ui()
        self._start_threads()

    def _setup_ui(self):
        # Left Panel: Video Feed
        self.video_frame = ttk.LabelFrame(self.main_container, text="Live Feed")
        self.video_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.video_label = ttk.Label(self.video_frame)
        self.video_label.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Right Panel: Controls & Status
        self.control_panel = ttk.Frame(self.main_container, width=300)
        self.control_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=10)
        
        # Status
        self.status_frame = ttk.LabelFrame(self.control_panel, text="System Status")
        self.status_frame.pack(fill=tk.X, pady=5)
        
        self.lbl_fps = ttk.Label(self.status_frame, text="FPS: 0")
        self.lbl_fps.pack(ipady=2)
        
        self.lbl_gesture = ttk.Label(self.status_frame, text="Gesture: None", font=("Arial", 14, "bold"))
        self.lbl_gesture.pack(ipady=5)
        
        self.lbl_state = ttk.Label(self.status_frame, text="PAUSED", foreground="red", font=("Arial", 16))
        self.lbl_state.pack(ipady=5)

        # Calibration
        self.calib_frame = ttk.LabelFrame(self.control_panel, text="Calibration")
        self.calib_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(self.calib_frame, text="Start Calibration", command=self.start_calibration).pack(fill=tk.X, padx=5, pady=5)
        ttk.Checkbutton(self.calib_frame, text="Show Box", variable=self.show_calib_box).pack(anchor=tk.W, padx=5)

        # Settings
        self.settings_frame = ttk.LabelFrame(self.control_panel, text="Configuration")
        self.settings_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(self.settings_frame, text="Smoothing (EMA):").pack(anchor=tk.W, pady=(5,0))
        self.scale_smooth = ttk.Scale(self.settings_frame, from_=0.1, to=0.9, value=0.5, command=self._update_smooth)
        self.scale_smooth.pack(fill=tk.X)
        self.lbl_smooth_val = ttk.Label(self.settings_frame, text="0.5")
        self.lbl_smooth_val.pack(anchor=tk.E)
        
        # Instructions
        self.help_frame = ttk.LabelFrame(self.control_panel, text="Valid Gestures")
        self.help_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        help_text = (
            "• Fist: PAUSE\n"
            "• Open Palm: ACTIVATE\n"
            "• Pinch: Click / Drag\n"
            "• Thumbs Up: Vol Up\n"
            "• Thumbs Down: Vol Down\n"
            "• Swipe: Switch App/Desk"
        )
        ttk.Label(self.help_frame, text=help_text, justify=tk.LEFT).pack(padx=5, pady=5)

    def _update_smooth(self, val):
        self.smoothing_factor = float(val)
        self.lbl_smooth_val.configure(text=f"{self.smoothing_factor:.2f}")

    def start_calibration(self):
        self.calibration_active = True
        self.calib_start_time = time.time()
        # Reset temp bounds
        self.calib_temp_min_x = 1.0
        self.calib_temp_max_x = 0.0
        self.calib_temp_min_y = 1.0
        self.calib_temp_max_y = 0.0

    def _start_threads(self):
        self.cap = cv2.VideoCapture(0)
        self.thread = threading.Thread(target=self._process_loop, daemon=True)
        self.thread.start()
        self.root.after(100, self._update_gui)

    def _process_loop(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret: continue
            
            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape
            
            self.tracker.process_frame(frame)
            result = self.tracker.get_latest_landmarks()
            
            gesture_name = "None"
            
            if result and result.hand_landmarks:
                landmarks = result.hand_landmarks[0]
                gesture_name = self.classifier.classify(landmarks)
                
                # Check Calibration
                if self.calibration_active:
                    self._process_calibration(landmarks)
                else:
                    # Update State
                    if gesture_name == "Fist":
                        self.is_paused = True
                    elif gesture_name == "Open_Palm" and self.is_paused:
                        self.is_paused = False
                    elif gesture_name == "Thumbs_Up":
                        self.controller.volume_up() 
                    elif gesture_name == "Thumbs_Down":
                        self.controller.volume_down()
                        
                    # Core Logic
                    if not self.is_paused:
                        if gesture_name == "Three_Fingers":
                            self._handle_swipe_gesture(landmarks)
                        else:
                            self._handle_active_mode(gesture_name, landmarks)
                        
                self._draw_landmarks(frame, landmarks)
                
            self.current_gesture = gesture_name
            
            # Overlay
            self._draw_overlay(frame, gesture_name)
            
            # Tkinter Convert
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb)
            img = img.resize((720, 540))
            self.current_image = ImageTk.PhotoImage(image=img)
            
            self.frame_count += 1
            if time.time() - self.start_time > 1.0:
                self.fps = self.frame_count / (time.time() - self.start_time)
                self.frame_count = 0
                self.start_time = time.time()
                
            time.sleep(0.01)

    def _process_calibration(self, landmarks):
        # Time remaining
        elapsed = time.time() - self.calib_start_time
        if elapsed > self.calib_duration:
            # Finish
            self.calibration_active = False
            # Save bounds with a small margin padding? 
            # Or just take exactly what user did. Let's take exactly.
            self.calib_bounds["x_min"] = max(0.0, self.calib_temp_min_x)
            self.calib_bounds["x_max"] = min(1.0, self.calib_temp_max_x)
            self.calib_bounds["y_min"] = max(0.0, self.calib_temp_min_y)
            self.calib_bounds["y_max"] = min(1.0, self.calib_temp_max_y)
            print(f"New Bounds: {self.calib_bounds}")
            return
            
        # Update temp bounds with Index Tip (8) or Wrist (0)
        # Using Index Tip because that's what drives the cursor
        point = landmarks[8]
        self.calib_temp_min_x = min(self.calib_temp_min_x, point.x)
        self.calib_temp_max_x = max(self.calib_temp_max_x, point.x)
        self.calib_temp_min_y = min(self.calib_temp_min_y, point.y)
        self.calib_temp_max_y = max(self.calib_temp_max_y, point.y)

    def _handle_swipe_gesture(self, landmarks):
        # Update Swipe History (Wrist X)
        wrist = landmarks[0]
        self.swipe_history.append((wrist.x, time.time()))
        self._check_swipe()

    def _handle_active_mode(self, gesture, landmarks):
        # 1. Cursor Measurement 
        # SWITCHED to Index Tip (8) for precision
        # When Pinching, use midpoint of 4/8 or just keep using 8?
        # If we use 8, pinching moves the point. 
        # Let's use Index MCP (5) still? 
        # User requested "index finger and thum start to move" -> Precision.
        # Let's use Index Tip (8).
        pointer = landmarks[8] 
        self._move_cursor(pointer.x, pointer.y)
        
        # 3. Pinch / Click Logic
        if gesture == "Pinch":
            if not self.is_pinching:
                self.is_pinching = True
                self.pinch_start_time = time.time()
            else:
                duration = time.time() - self.pinch_start_time
                if duration > 0.2 and not self.is_dragging: # Reduced drag delay
                    self.is_dragging = True
                    self.controller.mouse_down()
        else:
            if self.is_pinching:
                # Released Pinch
                duration = time.time() - self.pinch_start_time
                self.is_pinching = False
                
                if self.is_dragging:
                    self.is_dragging = False
                    self.controller.mouse_up()
                else:
                    if duration < 0.2:
                        if time.time() - self.last_click_time < 0.4:
                            self.controller.double_click()
                        else:
                            self.controller.click()
                        self.last_click_time = time.time()

    def _move_cursor(self, raw_x, raw_y):
        # Map raw normalized coords (0-1) to screen using Dynamic Bounds
        min_x = self.calib_bounds["x_min"]
        max_x = self.calib_bounds["x_max"]
        min_y = self.calib_bounds["y_min"]
        max_y = self.calib_bounds["y_max"]
        
        # Normalize to 0-1 within the box
        width = max_x - min_x
        height = max_y - min_y
        
        if width == 0 or height == 0: return
        
        x_mapped = np.clip((raw_x - min_x) / width, 0.0, 1.0)
        y_mapped = np.clip((raw_y - min_y) / height, 0.0, 1.0)
        
        # Smoothing (EMA)
        alpha = self.smoothing_factor
        self.smooth_x = alpha * x_mapped + (1 - alpha) * self.smooth_x
        self.smooth_y = alpha * y_mapped + (1 - alpha) * self.smooth_y
        
        self.controller.move_mouse(self.smooth_x, self.smooth_y)

    def _check_swipe(self):
        if time.time() - self.last_swipe_time < self.swipe_cooldown: return
        if len(self.swipe_history) < 5: return
        
        start_x, start_t = self.swipe_history[0]
        end_x, end_t = self.swipe_history[-1]
        
        dt = end_t - start_t
        if dt == 0: return
        
        velocity = (end_x - start_x) / dt 
        
        if velocity > 0.8: 
            self.controller.swipe_right()
            self.last_swipe_time = time.time()
        elif velocity < -0.8: 
            self.controller.swipe_left()
            self.last_swipe_time = time.time()

    def _draw_overlay(self, frame, gesture):
        h, w, _ = frame.shape
        
        if self.calibration_active:
            elapsed = time.time() - self.calib_start_time
            remaining = int(self.calib_duration - elapsed)
            
            cv2.rectangle(frame, (0,0), (w,h), (0,0,0), -1)
            cv2.putText(frame, "CALIBRATION MODE", (w//2-150, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,255), 2)
            cv2.putText(frame, f"Move hand to all corners! {remaining}s", (50, h//2), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)
            return

        # Active Region
        if self.show_calib_box.get() and not self.is_paused:
            x1 = int(self.calib_bounds["x_min"] * w)
            y1 = int(self.calib_bounds["y_min"] * h)
            x2 = int(self.calib_bounds["x_max"] * w)
            y2 = int(self.calib_bounds["y_max"] * h)
            
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 2)
            cv2.putText(frame, "Active Region", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)

        # Status
        color = (0, 0, 255) if self.is_paused else (0, 255, 0)
        status = "PAUSED" if self.is_paused else "ACTIVE"
        cv2.putText(frame, f"System: {status}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        cv2.putText(frame, f"Gesture: {gesture}", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 200, 0), 2)
        
        if self.is_dragging:
             cv2.putText(frame, "DRAGGING", (w-150, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

    def _draw_landmarks(self, frame, landmarks):
        h, w, _ = frame.shape
        for lm in landmarks:
            cx, cy = int(lm.x * w), int(lm.y * h)
            cv2.circle(frame, (cx, cy), 4, (0, 255, 0), -1)

    def _update_gui(self):
        if hasattr(self, 'current_image'):
            self.video_label.configure(image=self.current_image)
        
        self.lbl_fps.configure(text=f"FPS: {self.fps:.1f}")
        self.lbl_gesture.configure(text=f"Gesture: {self.current_gesture}")
        
        if self.is_paused:
            self.lbl_state.configure(text="PAUSED", foreground="red")
        else:
            self.lbl_state.configure(text="ACTIVE", foreground="green")
            
        self.root.after(30, self._update_gui)

    def close(self):
        self.running = False
        if hasattr(self, 'cap') and self.cap.isOpened():
            self.cap.release()
        if hasattr(self, 'tracker'):
            self.tracker.close()
        self.root.destroy()
