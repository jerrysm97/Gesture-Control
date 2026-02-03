import pyautogui
import os
import time
import platform

class MacController:
    def __init__(self):
        # Configuration
        pyautogui.FAILSAFE = False # We handle boundaries manually if needed
        self.screen_w, self.screen_h = pyautogui.size()
        
        # Debouncing
        self.last_action_time = 0
        self.action_cooldown = 0.5 # Seconds between discrete actions like clicks

    # --- Mouse Control ---
    def move_mouse(self, x_norm, y_norm):
        """
        Moves mouse to normalized coordinates (0.0 to 1.0).
        """
        target_x = int(x_norm * self.screen_w)
        target_y = int(y_norm * self.screen_h)
        try:
            pyautogui.moveTo(target_x, target_y, _pause=False)
        except Exception:
            pass

    def click(self, button='left'):
        """Performs a click."""
        if self._can_act():
            pyautogui.click(button=button)
            self._record_action()

    def double_click(self):
        if self._can_act():
            pyautogui.doubleClick()
            self._record_action()

    def scroll(self, dy):
        """
        Scrolls vertically. dy positive = up, negative = down.
        """
        pyautogui.scroll(dy * 10) # Scale factor

    def zoom(self, direction="in"):
        """
        Zoom using keyboard shortcuts (Cmd + +/-).
        """
        if self._can_act():
            key = '+' if direction == "in" else '-'
            pyautogui.hotkey('command', key)
            self._record_action()

    def drag(self, x_norm, y_norm):
        """Drags from current position to target."""
        tx, ty = int(x_norm * self.screen_w), int(y_norm * self.screen_h)
        pyautogui.dragTo(tx, ty, button='left', _pause=False)

    # --- System Control ---
    def volume_up(self):
        self._run_applescript("set volume output volume (output volume of (get volume settings) + 5)")
    
    def volume_down(self):
        self._run_applescript("set volume output volume (output volume of (get volume settings) - 5)")

    def brightness_up(self):
        # Brightness is tricky on non-Apple displays, but for Mac built-in:
        # Key code 144 is usually brightness up, 145 down
        self._key_press(144)
    
    def brightness_down(self):
        self._key_press(145)

    def switch_app(self):
        """Switch triggers Alt+Tab (Win) or Cmd+Tab (Mac)"""
        if self._can_act():
            mod = 'command' if platform.system() == 'Darwin' else 'alt'
            pyautogui.hotkey(mod, 'tab')
            self._record_action()

    def swipe_left(self):
        """Triggers Desktop Switch Left"""
        if self._can_act():
            if platform.system() == 'Darwin':
                # Mac: Ctrl + Left Arrow
                pyautogui.hotkey('ctrl', 'left')
            else:
                # Windows: Ctrl + Win + Left Arrow
                pyautogui.hotkey('ctrl', 'win', 'left')
            self._record_action()

    def swipe_right(self):
        """Triggers Desktop Switch Right"""
        if self._can_act():
            if platform.system() == 'Darwin':
                # Mac: Ctrl + Right Arrow
                pyautogui.hotkey('ctrl', 'right')
            else:
                # Windows: Ctrl + Win + Right Arrow
                pyautogui.hotkey('ctrl', 'win', 'right')
            self._record_action()

    def mouse_down(self):
        pyautogui.mouseDown(button='left')
        
    def mouse_up(self):
        pyautogui.mouseUp(button='left')

    # --- Utils ---
    def _can_act(self):
        return (time.time() - self.last_action_time) > self.action_cooldown

    def _record_action(self):
        self.last_action_time = time.time()

    def _run_applescript(self, script):
        os.system(f"osascript -e '{script}' &")

    def _key_press(self, key_code):
        # Uses dedicated key code implementation via Applescript for special keys
        # Or pyautogui if standard key
        os.system(f"osascript -e 'tell application \"System Events\" to key code {key_code}' &")
