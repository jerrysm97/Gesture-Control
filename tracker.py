import mediapipe as mp
import cv2
import time
import threading
import numpy as np

# MediaPipe Task Aliases
BaseOptions = mp.tasks.BaseOptions
HandLandmarker = mp.tasks.vision.HandLandmarker
HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
HandLandmarkerResult = mp.tasks.vision.HandLandmarkerResult
VisionRunningMode = mp.tasks.vision.RunningMode

class HandTracker:
    def __init__(self, model_path='hand_gesture_control/models/hand_landmarker.task', num_hands=2):
        """
        Initializes the MediaPipe Hand Landmarker in LIVE_STREAM mode.
        """
        self.lock = threading.Lock()
        self.latest_result = None
        self.timestamp_ms = 0
        self.start_time = time.time()
        
        # Callback for async processing
        def result_callback(result: HandLandmarkerResult, output_image: mp.Image, timestamp_ms: int):
            with self.lock:
                self.latest_result = result
        
        # Configure Options
        options = HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=model_path),
            running_mode=VisionRunningMode.LIVE_STREAM,
            num_hands=num_hands,
            min_hand_detection_confidence=0.5,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5,
            result_callback=result_callback
        )
        
        # Create Landmarker
        try:
            self.landmarker = HandLandmarker.create_from_options(options)
            print("HandTracker Initialized Successfully.")
        except Exception as e:
            print(f"Failed to initialize HandTracker: {e}")
            raise e

    def process_frame(self, frame):
        """
        Sends a frame to MediaPipe for processing (Async).
        frame: BGR numpy array (OpenCV format).
        """
        # Convert to RGB and MediaPipe Image
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        
        # Calculate timestamp
        self.timestamp_ms = int((time.time() - self.start_time) * 1000)
        
        # Send for detection
        self.landmarker.detect_async(mp_image, self.timestamp_ms)

    def get_latest_landmarks(self):
        """
        Returns the latest available landmarks (thread-safe).
        Returns: HandLandmarkerResult or None
        """
        with self.lock:
            return self.latest_result

    def close(self):
        if self.landmarker:
            self.landmarker.close()
