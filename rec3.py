import tkinter as tk
from tkinter import messagebox, filedialog
import sqlite3
import os
import threading
import pyscreenrec
import wave
import struct
import bcrypt
import ffmpeg
from pvrecorder import PvRecorder

conn = sqlite3.connect('users.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT, password TEXT)''')
conn.commit()
conn.close()

rec = pyscreenrec.ScreenRecorder()

class RegisterPage:
    def __init__(self, root):
        self.root = root
        self.root.title("Register")
        self.root.geometry("400x300")
        
        self.frame = tk.Frame(root)
        self.frame.pack(expand=True, fill='both')
        
        tk.Label(self.frame, text="Username", font=('Helvetica', 16)).pack(pady=10)
        self.username = tk.Entry(self.frame, font=('Helvetica', 16))
        self.username.pack(pady=10)
        
        tk.Label(self.frame, text="Password", font=('Helvetica', 16)).pack(pady=10)
        self.password = tk.Entry(self.frame, show="*", font=('Helvetica', 16))
        self.password.pack(pady=10)
        
        tk.Button(self.frame, text="Register", font=('Helvetica', 16), command=self.register).pack(pady=20)
        tk.Button(self.frame, text="Go to Login", font=('Helvetica', 16), command=self.goto_login).pack(pady=5)
    
    def register(self):
        username = self.username.get()
        password = self.password.get()
        if username and password:
            hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute("INSERT INTO users VALUES (?, ?)", (username, hashed))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Registration successful")
        else:
            messagebox.showwarning("Error", "Please fill in all fields")
    
    def goto_login(self):
        self.root.destroy()
        root = tk.Tk()
        LoginPage(root)
        root.mainloop()

class LoginPage:
    def __init__(self, root):
        self.root = root
        self.root.title("Login")
        self.root.geometry("400x300")
        
        self.frame = tk.Frame(root)
        self.frame.pack(expand=True, fill='both')
        
        tk.Label(self.frame, text="Username", font=('Helvetica', 16)).pack(pady=10)
        self.username = tk.Entry(self.frame, font=('Helvetica', 16))
        self.username.pack(pady=10)
        
        tk.Label(self.frame, text="Password", font=('Helvetica', 16)).pack(pady=10)
        self.password = tk.Entry(self.frame, show="*", font=('Helvetica', 16))
        self.password.pack(pady=10)
        
        tk.Button(self.frame, text="Login", font=('Helvetica', 16), command=self.login).pack(pady=20)
        tk.Button(self.frame, text="Go to Register", font=('Helvetica', 16), command=self.goto_register).pack(pady=5)
    
    def login(self):
        username = self.username.get()
        password = self.password.get()
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT password FROM users WHERE username = ?", (username,))
        result = c.fetchone()
        if result and bcrypt.checkpw(password.encode('utf-8'), result[0]):
            self.root.destroy()
            root = tk.Tk()
            RecorderPage(root)
            root.mainloop()
        else:
            messagebox.showerror("Error", "Invalid credentials")
        conn.close()
    
    def goto_register(self):
        self.root.destroy()
        root = tk.Tk()
        RegisterPage(root)
        root.mainloop()

class RecorderPage:
    def __init__(self, root):
        self.root = root
        self.root.title("Screen Recorder")
        self.root.geometry("400x300")
        
        self.frame = tk.Frame(root)
        self.frame.pack(expand=True, fill='both')
        
        self.is_recording = False
        self.audio_data = []
        
        self.start_button = tk.Button(self.frame, text="Start Recording", font=('Helvetica', 16), command=self.start_recording)
        self.start_button.pack(pady=10)
        
        self.stop_button = tk.Button(self.frame, text="Stop Recording", font=('Helvetica', 16), command=self.stop_recording, state=tk.DISABLED)
        self.stop_button.pack(pady=10)
        
        self.device_label = tk.Label(self.frame, text="", font=('Helvetica', 10))
        self.device_label.pack(pady=10)

        self.root.bind("<B1-Motion>", self.move_window)
        self.root.bind("<ButtonPress-1>", self.start_move)
        self.root.bind("<ButtonRelease-1>", self.stop_move)

        self.x = 0
        self.y = 0

        # Audio recorder setup
        self.audio_device_index = self.find_stereo_mix_device()
        if self.audio_device_index is not None:
            self.recorder = PvRecorder(device_index=self.audio_device_index, frame_length=512)
            device_name = PvRecorder.get_available_devices()[self.audio_device_index]
            self.device_label.config(text=f"Using device: {device_name}")
        else:
            messagebox.showerror("Error", "Stereo Mix device not found. Please enable it in your sound settings.")
            self.root.destroy()

    def find_stereo_mix_device(self):
        devices = PvRecorder.get_available_devices()
        for index, device in enumerate(devices):
            if "stereo mix" in device.lower():
                return index
        return None

    def start_move(self, event):
        self.x = event.x
        self.y = event.y

    def stop_move(self, event):
        self.x = None
        self.y = None

    def move_window(self, event):
        x = self.root.winfo_pointerx() - self.x
        y = self.root.winfo_pointery() - self.y
        self.root.geometry(f"+{x}+{y}")

    def start_recording(self):
        if not self.is_recording:
            self.is_recording = True
            self.audio_data = []
            self.audio_thread = threading.Thread(target=self.record_audio)
            self.audio_thread.start()
            rec.start_recording("output.mp4", 30)
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            messagebox.showinfo("Recording", "Screen and audio recording started.")
        else:
            messagebox.showwarning("Warning", "Recording is already running.")

    def stop_recording(self):
        if self.is_recording:
            self.is_recording = False
            rec.stop_recording()
            self.audio_thread.join()
            self.save_recording()
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)

    def record_audio(self):
        self.recorder.start()
        while self.is_recording:
            frame = self.recorder.read()
            self.audio_data.extend(frame)
        self.recorder.stop()

    def save_recording(self):
        audio_path = 'output_audio.wav'
        with wave.open(audio_path, 'w') as f:
            f.setparams((1, 2, 16000, 512, "NONE", "NONE"))
            f.writeframes(struct.pack("h" * len(self.audio_data), *self.audio_data))

        # Merge audio and video using ffmpeg
        input_video = ffmpeg.input('output.mp4')
        input_audio = ffmpeg.input(audio_path)
        output_file = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4 files", "*.mp4")])
        
        if output_file:
            try:
                ffmpeg.concat(input_video, input_audio, v=1, a=1).output(output_file).run(overwrite_output=True)
                messagebox.showinfo("Success", "Recording saved successfully.")
                # Clean up temporary files
                os.remove("output.mp4")
                os.remove(audio_path)
            except FileNotFoundError:
                messagebox.showerror("Error", "ffmpeg not found. Ensure it is installed and added to PATH.")
            except ffmpeg.Error as e:
                messagebox.showerror("Error", f"Failed to save recording: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    LoginPage(root)
    root.mainloop()