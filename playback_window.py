import sys
import os
import argparse
import tkinter as tk
from tkinter import messagebox, ttk
import simpleaudio as sa
import wave
import time

def apply_dark_theme(root):
    def apply(widget):
        try:
            widget.configure(bg='#2b2b2b', fg='white')
            if hasattr(widget, 'children'):
                for child in widget.children.values():
                    apply(child)
        except:
            pass
    apply(root)

class PlaybackWindow:
    def __init__(self, wav_path, dark_mode=False):
        self.wav_path = wav_path
        self.play_obj = None
        self.playback_active = False
        self.window = tk.Tk()
        self.window.title("🎵 SSTV Audio Playback")
        self.window.geometry("400x250")
        self.window.resizable(False, False)

        # File info
        tk.Label(self.window, text="Playing:", font=("Arial", 12, "bold")).pack(pady=10)
        file_label = tk.Label(self.window, text=os.path.basename(wav_path), fg="blue")
        file_label.pack()

        # Duration info
        try:
            with wave.open(wav_path, 'rb') as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                self.audio_length = frames / float(rate)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read audio: {str(e)}")
            self.window.destroy()
            return
        duration_min, duration_sec = divmod(int(self.audio_length), 60)
        duration_text = f"Duration: {duration_min:02d}:{duration_sec:02d}"
        tk.Label(self.window, text=duration_text, font=("Arial", 10)).pack(pady=5)

        # Progress bar and time label
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.window, orient="horizontal", length=300, mode="determinate", variable=self.progress_var)
        self.progress_bar.pack(pady=5)
        self.time_label = tk.Label(self.window, text="00:00 / {:02d}:{:02d}".format(duration_min, duration_sec))
        self.time_label.pack(pady=2)

        # Play/Stop button
        self.play_button = tk.Button(self.window, text="▶ Play", command=self.toggle_playback,
                                   font=("Arial", 14), width=15, height=2)
        self.play_button.pack(pady=10)

        # Status
        self.status_label = tk.Label(self.window, text="Ready to play", fg="gray")
        self.status_label.pack(pady=5)

        # Close button
        tk.Button(self.window, text="Close", command=self.close_window).pack(pady=10)

        # Load audio
        try:
            self.wave_obj = sa.WaveObject.from_wave_file(wav_path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load audio: {str(e)}")
            self.window.destroy()
            return

        # Handle window close
        self.window.protocol("WM_DELETE_WINDOW", self.close_window)

        if dark_mode:
            apply_dark_theme(self.window)

        self._wall_start_time = None
        self.window.mainloop()

    def toggle_playback(self):
        if self.playback_active:
            self.stop_playback()
        else:
            self.start_playback()

    def start_playback(self):
        try:
            self.playback_active = True
            self.play_button.config(text="⏹ Stop")
            self.status_label.config(text="Playing...")
            self.play_obj = self.wave_obj.play()
            self._wall_start_time = time.time()
            self._update_progress_bar()
            self.monitor_playback()
        except Exception as e:
            self.playback_active = False
            messagebox.showerror("Playback Error", f"Failed to start playback: {str(e)}")

    def stop_playback(self):
        try:
            self.playback_active = False
            self.play_button.config(text="▶ Play")
            self.status_label.config(text="Stopped")
            if self.play_obj:
                self.play_obj.stop()
                self.play_obj = None
            self.progress_var.set(0)
            self.time_label.config(text="00:00 / {:02d}:{:02d}".format(*divmod(int(self.audio_length), 60)))
        except Exception as e:
            pass

    def monitor_playback(self):
        if self.playback_active and self.play_obj and self.play_obj.is_playing():
            self.window.after(100, self.monitor_playback)
        elif self.playback_active:
            self.stop_playback()
            self.status_label.config(text="Playback completed")

    def _update_progress_bar(self):
        if not self.playback_active or not self.play_obj:
            return
        elapsed = time.time() - self._wall_start_time if self._wall_start_time else 0
        progress = (elapsed / self.audio_length) * 100 if self.audio_length > 0 else 0
        self.progress_var.set(progress)
        cur_min, cur_sec = divmod(int(elapsed), 60)
        total_min, total_sec = divmod(int(self.audio_length), 60)
        self.time_label.config(text="{:02d}:{:02d} / {:02d}:{:02d}".format(cur_min, cur_sec, total_min, total_sec))
        if self.playback_active and self.play_obj and self.play_obj.is_playing():
            self.window.after(100, self._update_progress_bar)

    def close_window(self):
        if self.playback_active:
            self.stop_playback()
        self.window.destroy()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SSTV WAV Playback Window")
    parser.add_argument("wav_path", help="Path to WAV file")
    parser.add_argument("--dark", action="store_true", help="Enable dark mode")
    args = parser.parse_args()
    if not os.path.exists(args.wav_path):
        print(f"File not found: {args.wav_path}")
        sys.exit(1)
    PlaybackWindow(args.wav_path, dark_mode=args.dark) 