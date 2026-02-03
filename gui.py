import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import cv2
import threading
import time
import queue

from tracker import HandTracker
from gestures import GestureClassifier
from controller import MacController

class GestureApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Hand Gesture Control Center")
        self.root.geometry("1000x700")
        
        # Backend
        self.tracker = HandTracker()
        self.classifier = GestureClassifier()
        self.controller = MacController()
        
        # Metrics
        self.running = True
        self.fps = 0
        self.frame_count = 0
        self.start_time = time.time()
        
        # State
        self.current_gesture = "None"
        self.active_mode = "INACTIVE" # INACTIVE, ACTIVE, CALIBRATION
        
        # Main Layout
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
        
        # Status Box
        self.status_frame = ttk.LabelFrame(self.control_panel, text="System Status")
        self.status_frame.pack(fill=tk.X, pady=5)
        
        self.lbl_fps = ttk.Label(self.status_frame, text="FPS: 0")
        self.lbl_fps.pack(ipady=2)
        
        self.lbl_gesture = ttk.Label(self.status_frame, text="Gesture: None", font=("Arial", 14, "bold"))
        self.lbl_gesture.pack(ipady=5)
        
        self.lbl_mode = ttk.Label(self.status_frame, text="Mode: INACTIVE", foreground="red")
        self.lbl_mode.pack(ipady=5)

        # Controls
        self.btn_toggle = ttk.Button(self.control_panel, text="Start Tracking", command=self.toggle_tracking)
        self.btn_toggle.pack(fill=tk.X, pady=10)
        
        self.btn_calib = ttk.Button(self.control_panel, text="Calibrate", command=self.start_calibration)
        self.btn_calib.pack(fill=tk.X, pady=5)
        
        # Settings
        self.settings_frame = ttk.LabelFrame(self.control_panel, text="Sensitivity")
        self.settings_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(self.settings_frame, text="Smoothing:").pack(anchor=tk.W)
        self.scale_smooth = ttk.Scale(self.settings_frame, from_=0.1, to=1.0, value=0.5)
        self.scale_smooth.pack(fill=tk.X)

    def _start_threads(self):
        self.cap = cv2.VideoCapture(0)
        self.thread = threading.Thread(target=self._process_loop, daemon=True)
        self.thread.start()
        self.root.after(100, self._update_gui)

    def _process_loop(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret: continue
            
            # 1. Flip & Color
            frame = cv2.flip(frame, 1)
            
            # 2. Tracking
            self.tracker.process_frame(frame)
            result = self.tracker.get_latest_landmarks()
            
            # 3. Logic
            gesture_name = "None"
            if result and result.hand_landmarks:
                landmarks = result.hand_landmarks[0]
                gesture_name = self.classifier.classify(landmarks)
                
                # Draw Landmarks (Simple Lines)
                self._draw_landmarks(frame, landmarks)
                
                # Execute Logic (If Active)
                if self.active_mode == "ACTIVE":
                    self._handle_gesture_action(gesture_name, landmarks)

            self.current_gesture = gesture_name
            
            # 4. Display
            # Draw Status Overlay
            cv2.putText(frame, f"Mode: {self.active_mode}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, f"Gesture: {gesture_name}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            
            # Convert for Tkinter
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb)
            img = img.resize((640, 480)) # Resize for GUI
            self.current_image = ImageTk.PhotoImage(image=img)
            
            # FPS Calculation
            self.frame_count += 1
            if time.time() - self.start_time > 1.0:
                self.fps = self.frame_count / (time.time() - self.start_time)
                self.frame_count = 0
                self.start_time = time.time()
                
            time.sleep(0.01)

    def _handle_gesture_action(self, gesture, landmarks):
        """Map Gestures to Controller Actions"""
        # Mouse Move (Open Palm)
        if gesture == "Open_Palm":
            # Index Finger Base (5) or Palm Center (0, 9, 17 avg) as anchor
            # Let's use Index MCP (5) for stability
            point = landmarks[5]
            # Simple direct mapping (Needs calibration logic, using raw 0-1 for now)
            # Apply basic margin to allow reaching corners
            x = (point.x - 0.2) / 0.6
            y = (point.y - 0.2) / 0.6
            self.controller.move_mouse(x, y)
            
        elif gesture == "Pointing":
             # Move + Click ? Or just Move?
             # Let's say Pointing = Move & Hover. 
             # Pinched Pointing usually better for drag.
             pass

        elif gesture == "Fist":
             # Scroll or Drag? Let's say Grab
             # Not implemented in controller distinct drag yet without state
             pass
             
        elif gesture == "Thumbs_Up":
             self.controller.volume_up()

        elif gesture == "Peace":
             self.controller.click('right')

    def _draw_landmarks(self, frame, landmarks):
        h, w, _ = frame.shape
        for lm in landmarks:
            cx, cy = int(lm.x * w), int(lm.y * h)
            cv2.circle(frame, (cx, cy), 4, (0, 255, 0), -1)

    def _update_gui(self):
        """Main Thread UI Update"""
        if hasattr(self, 'current_image'):
            self.video_label.configure(image=self.current_image)
        
        self.lbl_fps.configure(text=f"FPS: {self.fps:.1f}")
        self.lbl_gesture.configure(text=f"Last: {self.current_gesture}")
        self.lbl_mode.configure(text=f"Mode: {self.active_mode}", foreground="green" if self.active_mode == "ACTIVE" else "red")
        
        self.root.after(30, self._update_gui)

    def toggle_tracking(self):
        if self.active_mode == "INACTIVE":
            self.active_mode = "ACTIVE"
            self.btn_toggle.configure(text="Stop Tracking")
        else:
            self.active_mode = "INACTIVE"
            self.btn_toggle.configure(text="Start Tracking")

    def start_calibration(self):
        self.active_mode = "CALIBRATION"
        self.calib_step = 0
        self.calib_bounds = {"x_min": 1.0, "x_max": 0.0, "y_min": 1.0, "y_max": 0.0}

    def _draw_calibration(self, frame):
        h, w, _ = frame.shape
        cv2.rectangle(frame, (0,0), (w,h), (0,0,0), -1)
        
        steps = ["Top-Left", "Top-Right", "Bottom-Right", "Bottom-Left"]
        if self.calib_step < 4:
            msg = f"Touch {steps[self.calib_step]} Corner"
            cv2.putText(frame, msg, (50, h//2), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)
            cv2.putText(frame, "Hold 'Fist' to Capture", (50, h//2 + 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200,200,200), 1)
            
            # Draw target dots
            pts = [(50,50), (w-50,50), (w-50,h-50), (50,h-50)]
            cv2.circle(frame, pts[self.calib_step], 20, (0,255,255), -1)
        else:
            cv2.putText(frame, "Calibration Done!", (w//2-100, h//2), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)
            
    def _handle_calibration_input(self, gesture, landmarks):
        if gesture == "Fist":
            # Taking average of wrist or index MCP as cursor point
            point = landmarks[5] # Index MCP
            
            # Store bounds (simplistic approach: just recording the limit)
            # A real wizard would wait for a "hold" confirmation.
            # We'll just advance step for this demo on first detection.
            # Ideally debounce this.
            
            if not hasattr(self, 'last_calib_time'): self.last_calib_time = 0
            if time.time() - self.last_calib_time < 1.0: return
            
            self.last_calib_time = time.time()
            self.calib_step += 1
            if self.calib_step >= 4:
                self.active_mode = "INACTIVE"
                print("Calibration Completed (Mock).")

    def _process_loop(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret: continue
            
            frame = cv2.flip(frame, 1)
            self.tracker.process_frame(frame)
            result = self.tracker.get_latest_landmarks()
            
            gesture_name = "None"
            landmarks = None
            
            if result and result.hand_landmarks:
                landmarks = result.hand_landmarks[0]
                gesture_name = self.classifier.classify(landmarks)
                self._draw_landmarks(frame, landmarks)
                
                if self.active_mode == "ACTIVE":
                    self._handle_gesture_action(gesture_name, landmarks)
                elif self.active_mode == "CALIBRATION":
                    self._handle_calibration_input(gesture_name, landmarks)

            if self.active_mode == "CALIBRATION":
                self._draw_calibration(frame)
            else:
                 # Standard Overlay
                cv2.putText(frame, f"Mode: {self.active_mode}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(frame, f"Gesture: {gesture_name}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

            self.current_gesture = gesture_name
            
            # Tkinter Convert
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb)
            img = img.resize((640, 480))
            self.current_image = ImageTk.PhotoImage(image=img)
            
            self.frame_count += 1
            if time.time() - self.start_time > 1.0:
                self.fps = self.frame_count / (time.time() - self.start_time)
                self.frame_count = 0
                self.start_time = time.time()
                
            time.sleep(0.01)

    def close(self):
        self.running = False
        if hasattr(self, 'cap') and self.cap.isOpened():
            self.cap.release()
        if hasattr(self, 'tracker'):
            self.tracker.close()
        self.root.destroy()
