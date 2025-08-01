import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pynput import mouse, keyboard
from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Controller as KeyboardController, Key, KeyCode
import os
import sys
import random
import json

input_events = []    # Stores all recorded input events
recording = False
playback_running = False
mouse_controller = MouseController()
keyboard_controller = KeyboardController()
record_thread = None
playback_thread = None

toggle_key = None
kill_key = None
keybind_menu_open = False

# --- Helper functions ---

def key_to_str(key):
    if isinstance(key, KeyCode):
        return key.char if key.char else str(key)
    elif isinstance(key, Key):
        return key.name
    else:
        return str(key)

def str_to_key(s):
    try:
        return getattr(Key, s)
    except AttributeError:
        if len(s) == 1:
            return s
        return KeyCode.from_char(s)

def handle_event(event):
    etype = event["type"]
    if etype == "move":
        mouse_controller.position = (event["x"], event["y"])
    elif etype == "click":
        btn = Button[event["button"]]
        if event["pressed"]:
            mouse_controller.press(btn)
        else:
            mouse_controller.release(btn)
    elif etype == "scroll":
        mouse_controller.scroll(event["dx"], event["dy"])
    elif etype == "key_press":
        try:
            k = str_to_key(event["key"])
            keyboard_controller.press(k)
        except:
            pass
    elif etype == "key_release":
        try:
            k = str_to_key(event["key"])
            keyboard_controller.release(k)
        except:
            pass

# --- Recording & Playback ---

def record_all_inputs(duration=None):
    global input_events, recording, record_thread
    input_events.clear()
    recording = True
    t0 = time.time()
    event_count.set(0)
    status_label.config(text="⏺️ Recording inputs...", foreground="orange")
    record_window = tk.Toplevel(root)
    record_window.title("Record Inputs")
    record_window.geometry("320x220")
    record_window.grab_set()
    record_window.configure(bg="#2e2e2e")

    # Info and controls
    info = tk.Label(record_window, text="All mouse & keyboard actions will be recorded.\nPress Stop to finish.", bg="#2e2e2e", fg="white")
    info.pack(pady=10)
    events_label = tk.Label(record_window, text="Events recorded: 0", bg="#2e2e2e", fg="lightblue")
    events_label.pack(pady=8)

    def update_event_count():
        events_label.config(text=f"Events recorded: {event_count.get()}")
        if recording:
            record_window.after(250, update_event_count)

    def stop_btn_cmd():
        stop_recording_inputs()
        record_window.destroy()
        update_status_label()

    stop_btn = ttk.Button(record_window, text="Stop Recording", command=stop_btn_cmd)
    stop_btn.pack(pady=15)

    record_window.protocol("WM_DELETE_WINDOW", stop_btn_cmd)
    update_event_count()

    lock = threading.Lock()

    def add_event(event):
        with lock:
            event["t"] = time.time() - t0
            input_events.append(event)
            event_count.set(len(input_events))

    # Mouse events
    def on_move(x, y):
        if recording:
            add_event({"type": "move", "x": x, "y": y})

    def on_click(x, y, button, pressed):
        if recording:
            add_event({"type": "click", "x": x, "y": y, "button": button.name, "pressed": pressed})

    def on_scroll(x, y, dx, dy):
        if recording:
            add_event({"type": "scroll", "x": x, "y": y, "dx": dx, "dy": dy})

    # Keyboard events
    def on_press(key):
        if recording:
            add_event({"type": "key_press", "key": key_to_str(key)})

    def on_release(key):
        if recording:
            add_event({"type": "key_release", "key": key_to_str(key)})

    m_listener = mouse.Listener(on_move=on_move, on_click=on_click, on_scroll=on_scroll)
    k_listener = keyboard.Listener(on_press=on_press, on_release=on_release)

    m_listener.start()
    k_listener.start()

    # Thread to auto-stop if duration is set
    def auto_stop():
        if duration:
            time.sleep(duration)
            stop_btn_cmd()
    if duration:
        threading.Thread(target=auto_stop, daemon=True).start()

def stop_recording_inputs():
    global recording
    recording = False
    update_status_label()

def playback_inputs(loop=False):
    global playback_running
    if not input_events:
        messagebox.showwarning("No input", "No input events loaded!")
        return
    playback_running = True
    t_last = 0
    status_label.config(text="▶️ Playing back...", foreground="green")
    t_start = time.time()
    while playback_running:
        t_last = 0
        for event in input_events:
            if not playback_running:
                break
            t_wait = (event["t"] - t_last) if t_last != 0 else event["t"]
            time.sleep(max(0, t_wait))
            handle_event(event)
            t_last = event["t"]
        if not loop:
            break
    status_label.config(text="🔴 Idle – not playing", foreground="gray")

def stop_playback():
    global playback_running
    playback_running = False
    status_label.config(text="🔴 Idle – not playing", foreground="gray")

def save_input_events():
    if not input_events:
        messagebox.showwarning("Nothing to save", "No input events to save!")
        return
    file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("Input Recording", "*.json")])
    if file_path:
        with open(file_path, "w") as f:
            json.dump(input_events, f)
        loaded_file_label.config(text=f"💾 Saved: {os.path.basename(file_path)}")
        messagebox.showinfo("Saved", f"Recording saved to {file_path}")

def load_input_events():
    global input_events
    file_path = filedialog.askopenfilename(defaultextension=".json", filetypes=[("Input Recording", "*.json")])
    if file_path and os.path.exists(file_path):
        with open(file_path, "r") as f:
            input_events = json.load(f)
        loaded_file_label.config(text=f"📂 Loaded: {os.path.basename(file_path)}")
        status_label.config(text=f"✅ Loaded {len(input_events)} events", foreground="green")
        messagebox.showinfo("Loaded", f"Loaded {len(input_events)} events.")

def clear_recording():
    global input_events
    if not input_events:
        messagebox.showinfo("Nothing to clear", "There are no recorded inputs to clear.")
        return
    input_events.clear()
    loaded_file_label.config(text="")
    update_status_label()

# --- Keybind / Utility ---

def update_status_label():
    if input_events:
        status_label.config(text="✅ Input events loaded", foreground="green")
    else:
        status_label.config(text="❌ No input loaded", foreground="red")

def update_keybind_label():
    global toggle_key, kill_key
    toggle_text = format_key(toggle_key) if toggle_key else "None"
    kill_text = format_key(kill_key) if kill_key else "None"
    keybind_status_label.config(text=f"Toggle: {toggle_text} | Kill: {kill_text}")

def format_key(key):
    if isinstance(key, KeyCode):
        return key.char or str(key)
    elif isinstance(key, Key):
        return key.name
    return str(key)

def start_keyboard_listener():
    def on_press(key):
        if keybind_menu_open:
            return
        if toggle_key and keys_equal(key, toggle_key):
            if playback_running:
                stop_playback()
            else:
                start_playback_thread()
        elif kill_key and keys_equal(key, kill_key):
            stop_playback()
            root.quit()
    global keyboard_listener
    keyboard_listener = keyboard.Listener(on_press=on_press)
    keyboard_listener.start()

def keys_equal(k1, k2):
    return format_key(k1).lower() == format_key(k2).lower()

def open_keybind_window():
    global keybind_menu_open
    keybind_menu_open = True
    settings_window = tk.Toplevel(root)
    settings_window.title("Keybind Settings")
    settings_window.geometry("320x270")
    settings_window.grab_set()
    settings_window.configure(bg="#2e2e2e")

    tk.Label(settings_window, text="Click a button to set a keybind:", bg="#2e2e2e", fg="white").pack(pady=10)

    toggle_label = tk.Label(settings_window, text="Toggle: None", relief="sunken", width=25, bg="white")
    toggle_label.pack(pady=5)
    kill_label = tk.Label(settings_window, text="Kill: None", relief="sunken", width=25, bg="white")
    kill_label.pack(pady=5)
    status_msg = tk.Label(settings_window, text="", foreground="lightblue", bg="#2e2e2e")
    status_msg.pack(pady=5)

    def wait_for_keybind(label_to_update, bind_type):
        status_msg.config(text="Press a key...")
        listener = None

        def on_press(key):
            nonlocal listener
            global toggle_key, kill_key
            if bind_type == "Toggle" and keys_equal(key, kill_key):
                status_msg.config(text="❌ Already used for Kill!", foreground="red")
                return
            if bind_type == "Kill" and keys_equal(key, toggle_key):
                status_msg.config(text="❌ Already used for Toggle!", foreground="red")
                return

            key_str = format_key(key)
            label_to_update.config(text=f"{bind_type}: {key_str}")
            status_msg.config(text=f"{bind_type} set to: {key_str}", foreground="green")

            if bind_type == "Toggle":
                toggle_key = key
            elif bind_type == "Kill":
                kill_key = key

            update_keybind_label()
            if listener:
                listener.stop()

        listener = keyboard.Listener(on_press=on_press)
        listener.start()

    ttk.Button(settings_window, text="Set TOGGLE Key", command=lambda: wait_for_keybind(toggle_label, "Toggle")).pack(pady=3)
    ttk.Button(settings_window, text="Set KILL Key", command=lambda: wait_for_keybind(kill_label, "Kill")).pack(pady=3)

    def close_window():
        global keybind_menu_open
        if toggle_key is None or kill_key is None:
            messagebox.showwarning("Incomplete", "Please set both keybinds.")
            return
        keybind_menu_open = False
        settings_window.destroy()

    ttk.Button(settings_window, text="Save & Close", command=close_window).pack(pady=15)

# --- GUI Layout ---

root = tk.Tk()
root.title("Super Input Recorder")
root.geometry("620x275")
root.configure(bg="#2e2e2e")

try:
    icon_path = os.path.join(sys._MEIPASS if hasattr(sys, "_MEIPASS") else ".", "icon.ico")
    root.iconbitmap(icon_path)
except Exception as e:
    print("Icon could not be set:", e)

loop_enabled = tk.BooleanVar()
event_count = tk.IntVar(value=0)

# Dark theme style
style = ttk.Style()
style.theme_use('default')
style.configure('TLabel', background="#2e2e2e", foreground="white")
style.configure('TButton', background="#444444", foreground="white")
style.configure('TCheckbutton',
    background="#2e2e2e",
    foreground="white",
    focuscolor="",
    selectcolor="#2e2e2e"
)
style.map('TCheckbutton',
    background=[('active', '#2e2e2e'), ('selected', '#2e2e2e')],
    foreground=[('active', 'white'), ('selected', 'white')]
)

left_frame = tk.Frame(root, bg="#2e2e2e")
right_frame = tk.Frame(root, bg="#2e2e2e")
left_frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=30, pady=10)
right_frame.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH, padx=30, pady=10)

ttk.Checkbutton(left_frame, text="Loop Playback", variable=loop_enabled).pack(pady=10)

status_label = ttk.Label(left_frame, text="❌ No input loaded", foreground="red", background="#2e2e2e")
status_label.pack(pady=(10, 0))

loaded_file_label = ttk.Label(left_frame, text="", foreground="lightgray", background="#2e2e2e", font=("Segoe UI", 9))
loaded_file_label.pack(pady=(0, 10))

keybind_status_label = ttk.Label(left_frame, text="Toggle: None | Kill: None", foreground="lightblue", background="#2e2e2e")
keybind_status_label.pack(pady=10)

def start_recording_thread():
    global record_thread
    stop_playback()
    if record_thread and record_thread.is_alive():
        return
    record_thread = threading.Thread(target=record_all_inputs, kwargs={'duration': None}, daemon=True)
    record_thread.start()

def start_playback_thread():
    global playback_thread
    stop_playback()
    if playback_thread and playback_thread.is_alive():
        return
    playback_thread = threading.Thread(target=playback_inputs, kwargs={'loop': loop_enabled.get()}, daemon=True)
    playback_thread.start()

# Right column
ttk.Button(right_frame, text="Record Inputs", command=start_recording_thread).pack(pady=10)
ttk.Button(right_frame, text="▶️ Playback Recording", command=start_playback_thread).pack(pady=10)
ttk.Button(right_frame, text="💾 Save Recording", command=save_input_events).pack(pady=10)
ttk.Button(right_frame, text="📂 Load Recording", command=load_input_events).pack(pady=10)
ttk.Button(right_frame, text="🧹 Clear Recording", command=clear_recording).pack(pady=10)
ttk.Button(right_frame, text="Open Keybind Settings", command=open_keybind_window).pack(pady=10)

# Startup
start_keyboard_listener()
update_status_label()
update_keybind_label()

root.mainloop()
