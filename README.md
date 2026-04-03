# ✋ Gesture-Control

**Computer Vision Gesture Recognition System**

Control your computer with hand gestures using real-time webcam input. Built with Python, OpenCV, and MediaPipe for hand landmark detection.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-Headless-5C3EE8?logo=opencv&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Cross--Platform-green)

---

## 🚀 Features

- **Real-time hand tracking** via webcam with MediaPipe landmarks
- **Gesture mapping** — pinch, swipe, fist, open palm → system actions
- **GUI interface** for configuration and live preview
- **Modular architecture** — separate tracker, gesture, and controller layers

## 📁 Architecture

```
Gesture-Control/
├── main.py          # Application entry point
├── tracker.py       # Hand landmark detection (MediaPipe)
├── gestures.py      # Gesture classification logic
├── controller.py    # System action mapping (volume, mouse, etc.)
└── gui.py           # Tkinter GUI for live preview & settings
```

## ⚡ Quick Start

```bash
git clone https://github.com/jerrysm97/Gesture-Control.git
cd Gesture-Control
pip install mediapipe opencv-python pyautogui
python main.py
```

## 🛠️ Tech Stack

- **Computer Vision:** OpenCV, MediaPipe
- **System Control:** PyAutoGUI
- **GUI:** Tkinter
- **Language:** Python 3.10+

## 📜 License

MIT License
