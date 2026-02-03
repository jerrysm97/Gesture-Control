import math
import numpy as np

class GestureClassifier:
    def __init__(self):
        # Finger Landmark Indices (Tip, PIP, MCP)
        self.fingers = {
            "Thumb": [4, 3, 2, 1],
            "Index": [8, 6, 5],
            "Middle": [12, 10, 9],
            "Ring": [16, 14, 13],
            "Pinky": [20, 18, 17]
        }
    
    def classify(self, landmarks):
        """
        Classifies the gesture based on hand landmarks.
        Returns: gesture_name (str)
        """
        if not landmarks: return "None"
        
        # 1. Detect Finger States (Extended or Curled)
        states = self._get_finger_states(landmarks)
        
        # 2. Rule-Based Classification
        if self._is_fist(states): return "Fist"
        if self._is_open_palm(states): return "Open_Palm"
        if self._is_pointing(states): return "Pointing"
        if self._is_peace(states): return "Peace"
        if self._is_thumbs_up(states, landmarks): return "Thumbs_Up"
        
        return "Unknown"

    def _get_finger_states(self, landmarks):
        """
        Returns a dict of True (Extended) / False (Curled) for each finger.
        Logic: Tip distance to Wrist > PIP/MCP distance to Wrist.
        """
        states = {}
        wrist = landmarks[0]
        
        for name, indices in self.fingers.items():
            tip = landmarks[indices[0]] # Tip
            
            # For Thumb, logic is slightly different (lateral movement)
            # Use X-coordinate diff for thumb relative to knuckle (CMS/MCP) if hand is vertical?
            # Simple heuristic: Thumb Tip distance to Pinky MCP vs Thumb IP distance to Pinky MCP?
            # Let's stick to Distance from Wrist for simplicity first, refining for thumb later.
            
            if name == "Thumb":
                # Thumb is tricky using just wrist dist. 
                # Check if tip is "farther out" than IP joint relative to palm center (index MCP approx)
                # Or just simple check: X distance from Index MCP?
                
                # Simple Hack: Thumb Tip vs Thumb IP along x-axis? No, orientation issues.
                # Let's use: Distance(Tip, Wrist) > Distance(IP, Wrist) * 1.05
                ip = landmarks[indices[1]]
                states[name] = self._dist(tip, wrist) > self._dist(ip, wrist) * 1.1
            else:
                # For other fingers: Tip vs PIP (indices[1])
                pip = landmarks[indices[1]]
                # Also check against MCP (indices[2]) to be sure
                mcp = landmarks[indices[2]]
                
                d_tip = self._dist(tip, wrist)
                d_pip = self._dist(pip, wrist)
                d_mcp = self._dist(mcp, wrist)
                
                # Tip must be further than PIP, and PIP further than MCP (mostly)
                states[name] = (d_tip > d_pip) and (d_pip > d_mcp)
                
        return states

    def _dist(self, p1, p2):
        return math.hypot(p1.x - p2.x, p1.y - p2.y)

    # --- Rules ---
    
    def _is_fist(self, s):
        # All 4 fingers curled. Thumb can be anything (often curled or tucked).
        return (not s["Index"] and not s["Middle"] and not s["Ring"] and not s["Pinky"])

    def _is_open_palm(self, s):
        # All 5 extended
        return all(s.values())

    def _is_pointing(self, s):
        # Index extended, others curled
        return s["Index"] and not s["Middle"] and not s["Ring"] and not s["Pinky"]

    def _is_peace(self, s):
        # Index & Middle extended, Ring & Pinky curled
        return s["Index"] and s["Middle"] and not s["Ring"] and not s["Pinky"]
        
    def _is_thumbs_up(self, s, landmarks):
        # Thumb extended, others curled.
        # Plus orientation check: Thumb Tip Y < Wrist Y (Upwards)
        if not (s["Thumb"] and not s["Index"] and not s["Middle"] and not s["Ring"] and not s["Pinky"]):
            return False
            
        wrist = landmarks[0]
        thumb_tip = landmarks[4]
        return thumb_tip.y < wrist.y # Simple "Up" check (Y increases downwards in CV coords)
