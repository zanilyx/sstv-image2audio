"""
SSTV Encoder Pro
----------------
A modern GUI tool to encode images into SSTV (Robot36, Scottie 1, Martin M1, Martin M2) audio with real-time playback and image enhancement.
"""
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import numpy as np
from scipy.io.wavfile import write
from pysstv.color import Robot36, ScottieS1, MartinM1, MartinM2
import simpleaudio as sa
import threading
import time
import wave

class SSTVEncoder:
    """
    Main application class for the SSTV Encoder Pro GUI.
    Handles image selection, processing, SSTV encoding, audio playback, and UI.
    """
    def __init__(self, root):
        self.root = root
        self.wave_obj = None
        self.play_obj = None
        self.playback_active = False
        self.playback_thread = None
        self.audio_length = 0
        self.setup_ui()

    def setup_ui(self):
        """Set up the main GUI layout and widgets."""
        self.root.title("📡 SSTV Encoder with Playback")
        self.root.geometry("520x500")
        self.root.resizable(False, False)

        # Main title
        tk.Label(self.root, text="SSTV Encoder Pro", font=("Arial", 14, "bold")).pack(pady=10)

        # Mode selection
        tk.Label(self.root, text="Select SSTV Mode:").pack()
        self.sstv_mode_var = tk.StringVar(value="Robot36")
        modes = ["Robot36", "Scottie 1", "Martin M1", "Martin M2"]
        tk.OptionMenu(self.root, self.sstv_mode_var, *modes).pack(pady=5)

        # Sample rate selection
        tk.Label(self.root, text="Sample Rate (Hz):").pack()
        self.samplerate_var = tk.StringVar(value="44100")
        tk.OptionMenu(self.root, self.samplerate_var, "44100", "48000", "22050").pack(pady=5)

        # Image processing options
        self.enhance_var = tk.BooleanVar(value=True)
        tk.Checkbutton(self.root, text="🖼️ Auto-enhance image", variable=self.enhance_var).pack()

        # Encode button
        tk.Button(self.root, text="📷 Encode Image to SSTV", command=self.start_encoding_thread,
                 height=2, width=35).pack(pady=10)

        # Playback controls frame
        playback_frame = tk.Frame(self.root)
        playback_frame.pack(pady=10)

        # Play/Stop button
        self.play_button = tk.Button(playback_frame, text="▶", width=5, command=self.toggle_playback, state=tk.DISABLED)
        self.play_button.pack(side=tk.LEFT, padx=5)

        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(playback_frame, orient="horizontal", 
                                          length=300, mode="determinate", 
                                          variable=self.progress_var)
        self.progress_bar.pack(side=tk.LEFT, padx=5)

        # Time label
        self.time_label = tk.Label(playback_frame, text="00:00 / 00:00")
        self.time_label.pack(side=tk.LEFT, padx=5)

        # Status label
        self.status_label = tk.Label(self.root, text="Ready", fg="gray")
        self.status_label.pack(pady=10)

    def start_encoding_thread(self):
        """Start encoding in a background thread to keep UI responsive."""
        threading.Thread(target=self.encode_image_to_sstv, daemon=True).start()

    def toggle_playback(self):
        """Toggle audio playback (play/stop)."""
        if self.playback_active:
            self.stop_playback()
        else:
            self.start_playback()

    def start_playback(self):
        """Start audio playback and update progress bar."""
        if self.wave_obj:
            self.playback_active = True
            self.play_button.config(text="⏹")
            self.play_obj = self.wave_obj.play()
            self.playback_thread = threading.Thread(target=self.update_playback_progress, daemon=True)
            self.playback_thread.start()

    def stop_playback(self):
        """Stop audio playback and reset progress bar."""
        if self.play_obj:
            self.playback_active = False
            self.play_button.config(text="▶")
            self.play_obj.stop()
            self.progress_var.set(0)
            self.update_time_label(0, self.audio_length)

    def update_playback_progress(self):
        """Update the progress bar and time label during playback."""
        start_time = time.time()
        while self.playback_active and self.play_obj and self.play_obj.is_playing():
            elapsed = time.time() - start_time
            progress = (elapsed / self.audio_length) * 100 if self.audio_length > 0 else 0
            self.progress_var.set(progress)
            self.update_time_label(elapsed, self.audio_length)
            time.sleep(0.1)
        self.stop_playback()

    def update_time_label(self, current, total):
        """Update the time label with current and total duration."""
        current_min, current_sec = divmod(int(current), 60)
        total_min, total_sec = divmod(int(total), 60)
        self.time_label.config(text=f"{current_min:02d}:{current_sec:02d} / {total_min:02d}:{total_sec:02d}")

    def adaptive_sharpen(self, img):
        """Apply adaptive sharpening based on image content."""
        img = img.filter(ImageFilter.UnsharpMask(radius=1, percent=200, threshold=1))
        return img

    def preprocess_image(self, img, mode):
        """Enhanced image processing pipeline for best SSTV results."""
        img = img.convert("RGB")
        img = ImageOps.exif_transpose(img)
        mode_resolutions = {
            "Robot36": (320, 240),
            "Scottie 1": (320, 256),
            "Martin M1": (320, 256),
            "Martin M2": (320, 256)
        }
        img = img.resize(mode_resolutions[mode], Image.LANCZOS)
        if self.enhance_var.get():
            img = ImageEnhance.Contrast(img).enhance(1.5)
            img = ImageEnhance.Color(img).enhance(1.3)
            img = self.adaptive_sharpen(img)
            # img = img.filter(ImageFilter.MedianFilter(size=3))  # Commented out for sharpness
        return img

    def encode_image_to_sstv(self):
        """Main encoding logic: select image, process, encode, save, and setup playback."""
        filepath = filedialog.askopenfilename(filetypes=[
            ("Image Files", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff")
        ])
        if not filepath:
            return
        try:
            self.status_label.config(text="Processing image...")
            self.root.update()
            mode = self.sstv_mode_var.get()
            samplerate = int(self.samplerate_var.get())
            img = Image.open(filepath)
            img = self.preprocess_image(img, mode)
            self.status_label.config(text="Generating SSTV signal...")
            self.root.update()
            sstv_classes = {
                "Robot36": Robot36,
                "Scottie 1": ScottieS1,
                "Martin M1": MartinM1,
                "Martin M2": MartinM2
            }
            if mode not in sstv_classes:
                messagebox.showerror("Error", f"Unsupported SSTV mode: {mode}")
                return
            # Use bits=8 for all modes for compatibility
            sstv = sstv_classes[mode](img, samplerate, 8)
            self.status_label.config(text="Generating audio samples...")
            self.root.update()
            samples = np.array(list(sstv.gen_samples()), dtype=np.float32)
            # Normalize amplitude to full int16 range
            max_val = np.max(np.abs(samples))
            if max_val > 0:
                samples = samples / max_val
            samples_int16 = np.int16(samples * 32767)
            # Ensure mono output
            if samples_int16.ndim == 1:
                wav_data = samples_int16
            else:
                wav_data = samples_int16[:, 0].copy()
            self.status_label.config(text="Saving WAV file...")
            self.root.update()
            save_path = filedialog.asksaveasfilename(
                defaultextension=".wav",
                filetypes=[("WAV Files", "*.wav")],
                title=f"Save {mode} SSTV WAV as..."
            )
            if not save_path:
                self.status_label.config(text="Ready")
                return
            write(save_path, samplerate, wav_data)
            self.setup_playback(save_path)
            messagebox.showinfo("Success", f"{mode} SSTV audio saved:\n{save_path}")
            self.status_label.config(text="Ready")
        except Exception as e:
            messagebox.showerror("Encoding Error", str(e))
            self.status_label.config(text="Error occurred")

    def setup_playback(self, wav_path):
        """Prepare audio playback for the generated WAV file."""
        if self.wave_obj:
            self.stop_playback()
        # Get audio length using wave module
        try:
            with wave.open(wav_path, 'rb') as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                self.audio_length = frames / float(rate)
        except Exception as e:
            self.status_label.config(text="Failed to load audio")
            messagebox.showerror("Audio Error", str(e))
            return
        self.wave_obj = sa.WaveObject.from_wave_file(wav_path)
        self.play_obj = None
        self.play_button.config(state=tk.NORMAL)
        self.progress_var.set(0)
        self.update_time_label(0, self.audio_length)

if __name__ == "__main__":
    root = tk.Tk()
    app = SSTVEncoder(root)
    root.mainloop()