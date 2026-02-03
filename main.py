import tkinter as tk
from gui import GestureApp
import sys

def main():
    root = tk.Tk()
    
    # Handle graceful exit
    def on_close():
        app.close()
        sys.exit(0)
        
    root.protocol("WM_DELETE_WINDOW", on_close)
    
    app = GestureApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
