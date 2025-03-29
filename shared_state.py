import json
import os
import threading
import time

STATE_FILE = os.path.join(os.path.dirname(__file__), "state.json")

def init_state():
    if not os.path.exists(STATE_FILE):
        save_state({"searches": [], "rainbow": False})

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)

def load_state():
    try:
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    except:
        init_state()
        return {"searches": [], "rainbow": False}

def start_file_monitor(callback):
    def monitor():
        last_mtime = 0
        while True:
            try:
                mtime = os.path.getmtime(STATE_FILE)
                if mtime > last_mtime:
                    last_mtime = mtime
                    callback(load_state())
            except:
                pass
            time.sleep(0.1)  

    thread = threading.Thread(target=monitor, daemon=True)
    thread.start()
