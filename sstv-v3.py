# SSTV Encoder Pro v3
# Modern GUI SSTV encoder with separate playback, dark mode, drag-and-drop, watermark, and more.

import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageEnhance, ImageFilter, ImageOps, ImageDraw, ImageFont, ImageTk
import numpy as np
from scipy.io.wavfile import write
from pysstv.color import Robot36, ScottieS1, MartinM1, MartinM2
import simpleaudio as sa
import subprocess
import logging
from datetime import datetime
import wave

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('sstv_encoder.log')
    ]
)
logger = logging.getLogger(__name__)

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    logger.info("tkinterdnd2 imported successfully")
except ImportError:
    logger.warning("tkinterdnd2 not available - drag and drop will be disabled")
    TkinterDnD = None
    DND_FILES = None

class SSTVEncoderV3:
    """
    Main application class for SSTV Encoder Pro v3.
    Features: drag-and-drop, preview, watermark, export, separate playback process.
    """
    def __init__(self, root):
        logger.info("Initializing SSTV Encoder Pro v3")
        self.root = root
        self.current_image = None
        self.current_image_path = None
        self.preview_photo = None
        self.preview_lock = threading.Lock()
        self.current_wav_path = None
        self.current_audio_length = 0
        self.setup_ui()
        self.setup_drag_drop()
        logger.info("SSTV Encoder Pro v3 initialized successfully")

    def setup_ui(self):
        """Set up the main GUI layout and widgets."""
        logger.info("Setting up UI")
        self.root.title("📡 SSTV Encoder Pro v3")
        self.root.geometry("900x800")
        self.root.resizable(True, True)

        # Main container
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Title
        title_frame = tk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 10))
        tk.Label(title_frame, text="SSTV Encoder Pro v3", font=("Arial", 16, "bold")).pack(side=tk.LEFT)

        # Left panel for controls
        left_panel = tk.Frame(main_frame)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        # Mode selection
        tk.Label(left_panel, text="SSTV Mode:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        self.sstv_mode_var = tk.StringVar(value="Robot36")
        modes = ["Robot36", "Scottie 1", "Martin M1", "Martin M2"]
        mode_menu = tk.OptionMenu(left_panel, self.sstv_mode_var, *modes, command=self.update_preview)
        mode_menu.config(width=15)
        mode_menu.pack(anchor=tk.W, pady=(0, 10))

        # Sample rate selection
        tk.Label(left_panel, text="Sample Rate (Hz):", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        self.samplerate_var = tk.StringVar(value="44100")
        tk.OptionMenu(left_panel, self.samplerate_var, "44100", "48000", "22050").pack(anchor=tk.W, pady=(0, 10))

        # Image processing options
        tk.Label(left_panel, text="Image Processing:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        self.enhance_var = tk.BooleanVar(value=True)
        tk.Checkbutton(left_panel, text="🖼️ Auto-enhance", variable=self.enhance_var, command=self.update_preview).pack(anchor=tk.W)

        # Watermark section
        tk.Label(left_panel, text="Watermark:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(10, 0))
        self.watermark_var = tk.BooleanVar(value=False)
        tk.Checkbutton(left_panel, text="Add watermark", variable=self.watermark_var, command=self.update_preview).pack(anchor=tk.W)
        tk.Label(left_panel, text="Callsigns/Text:").pack(anchor=tk.W)
        self.watermark_text = tk.StringVar(value="CALLSIGN")
        watermark_entry = tk.Entry(left_panel, textvariable=self.watermark_text, width=15)
        watermark_entry.pack(anchor=tk.W, pady=(0, 10))
        watermark_entry.bind('<KeyRelease>', lambda e: self.update_preview())

        # Buttons
        tk.Button(left_panel, text="📁 Select Image", command=self.select_image, height=2, width=20).pack(pady=5)
        tk.Button(left_panel, text="📷 Encode to SSTV", command=self.start_encoding_thread, height=2, width=20).pack(pady=5)

        # Export options
        tk.Label(left_panel, text="Export Options:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(10, 0))
        self.export_wav_var = tk.BooleanVar(value=True)
        self.export_mp3_var = tk.BooleanVar(value=False)
        self.export_ogg_var = tk.BooleanVar(value=False)
        tk.Checkbutton(left_panel, text="WAV", variable=self.export_wav_var).pack(anchor=tk.W)
        tk.Checkbutton(left_panel, text="MP3", variable=self.export_mp3_var).pack(anchor=tk.W)
        tk.Checkbutton(left_panel, text="OGG", variable=self.export_ogg_var).pack(anchor=tk.W)

        # Stats section
        tk.Label(left_panel, text="Statistics:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(20, 0))
        self.stats_frame = tk.Frame(left_panel)
        self.stats_frame.pack(anchor=tk.W, fill=tk.X)
        self.image_size_label = tk.Label(self.stats_frame, text="Image: Not loaded", fg="gray")
        self.image_size_label.pack(anchor=tk.W)
        self.audio_info_label = tk.Label(self.stats_frame, text="Audio: Not generated", fg="gray")
        self.audio_info_label.pack(anchor=tk.W)
        self.encode_time_label = tk.Label(self.stats_frame, text="Last encode: Never", fg="gray")
        self.encode_time_label.pack(anchor=tk.W)

        # Right panel for preview and playback
        right_panel = tk.Frame(main_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Preview area
        tk.Label(right_panel, text="Image Preview:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        self.preview_canvas = tk.Canvas(right_panel, width=320, height=256, bg="white", relief=tk.SUNKEN, bd=1)
        self.preview_canvas.pack(pady=(0, 10))
        self.drop_hint = tk.Label(self.preview_canvas, text="Drop image here\nor click 'Select Image'", fg="gray", font=("Arial", 12))
        self.preview_canvas.create_window(160, 128, window=self.drop_hint)

        # Playback section
        playback_frame = tk.Frame(right_panel)
        playback_frame.pack(fill=tk.X, pady=10)
        self.play_button = tk.Button(playback_frame, text="▶ Play Audio", command=self.open_playback_window, state=tk.DISABLED, font=("Arial", 12), width=15, height=2)
        self.play_button.pack(pady=10)
        self.file_location_label = tk.Label(playback_frame, text="No audio file available", fg="gray", wraplength=300)
        self.file_location_label.pack(pady=5)

        # Status label
        self.status_label = tk.Label(right_panel, text="Ready - Drop an image to get started", fg="gray")
        self.status_label.pack(pady=10)
        logger.info("UI setup completed")

    def setup_drag_drop(self):
        if TkinterDnD is None:
            logger.warning("Drag and drop not available - tkinterdnd2 not installed")
            return
        try:
            if hasattr(self.preview_canvas, 'drop_target_register'):
                self.preview_canvas.drop_target_register(DND_FILES)
            if hasattr(self.preview_canvas, 'dnd_bind'):
                self.preview_canvas.dnd_bind('<<Drop>>', self.handle_drop)
            logger.info("Drag and drop setup completed")
        except Exception as e:
            logger.error(f"Failed to setup drag and drop: {e}")

    def handle_drop(self, event):
        logger.info(f"File dropped: {event.data}")
        file_path = event.data
        if file_path.startswith('{'):
            file_path = file_path.strip('{}')
        if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff')):
            self.load_image(file_path)
        else:
            logger.warning(f"Invalid file type dropped: {file_path}")
            messagebox.showwarning("Invalid File", "Please drop an image file (PNG, JPG, BMP, TIF)")

    def update_preview(self, event=None):
        if self.current_image:
            threading.Thread(target=self._update_preview_thread, daemon=True).start()

    def _update_preview_thread(self):
        try:
            with self.preview_lock:
                if not self.current_image:
                    return
                mode = self.sstv_mode_var.get()
                img = self.preprocess_image(self.current_image.copy(), mode)
                if self.watermark_var.get():
                    img = self.add_watermark(img)
                img.thumbnail((320, 256), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.root.after(0, self._update_preview_canvas, photo)
        except Exception as e:
            logger.error(f"Error updating preview: {e}")

    def _update_preview_canvas(self, photo):
        try:
            self.preview_photo = photo
            self.preview_canvas.delete("all")
            self.preview_canvas.create_image(160, 128, image=photo)
        except Exception as e:
            logger.error(f"Error updating preview canvas: {e}")

    def select_image(self):
        filepath = filedialog.askopenfilename(filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff")])
        if filepath:
            self.load_image(filepath)

    def load_image(self, filepath):
        try:
            logger.info(f"Loading image: {filepath}")
            self.current_image = Image.open(filepath)
            self.current_image_path = filepath
            width, height = self.current_image.size
            self.image_size_label.config(text=f"Image: {width}x{height} pixels", fg="black")
            self.update_preview()
            self.status_label.config(text=f"Loaded: {os.path.basename(filepath)}")
        except Exception as e:
            logger.error(f"Error loading image: {e}")
            messagebox.showerror("Error", f"Failed to load image: {str(e)}")

    def add_watermark(self, img):
        try:
            draw = ImageDraw.Draw(img)
            try:
                font = ImageFont.truetype("arial.ttf", 20)
            except:
                font = ImageFont.load_default()
            text = self.watermark_text.get()
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = img.width - text_width - 10
            y = img.height - text_height - 10
            draw.text((x+1, y+1), text, font=font, fill='black')
            draw.text((x-1, y-1), text, font=font, fill='black')
            draw.text((x+1, y-1), text, font=font, fill='black')
            draw.text((x-1, y+1), text, font=font, fill='black')
            draw.text((x, y), text, font=font, fill='white')
            return img
        except Exception as e:
            logger.error(f"Error adding watermark: {e}")
            return img

    def start_encoding_thread(self):
        threading.Thread(target=self.encode_image_to_sstv, daemon=True).start()

    def open_playback_window(self):
        if self.current_wav_path and os.path.exists(self.current_wav_path):
            cmd = [sys.executable, os.path.join(os.path.dirname(__file__), 'playback_window.py'), self.current_wav_path]
            try:
                subprocess.Popen(cmd)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to launch playback window: {str(e)}")
        else:
            messagebox.showwarning("No Audio", "No audio file available for playback")

    def adaptive_sharpen(self, img):
        try:
            img = img.filter(ImageFilter.UnsharpMask(radius=1, percent=200, threshold=1))
            return img
        except Exception as e:
            logger.error(f"Error in adaptive sharpen: {e}")
            return img

    def preprocess_image(self, img, mode):
        try:
            logger.debug(f"Preprocessing image for mode: {mode}")
            img = img.convert("RGB")
            img = ImageOps.exif_transpose(img)
            mode_resolutions = {
                "Robot36": (320, 240),
                "Scottie 1": (320, 256),
                "Martin M1": (320, 256),
                "Martin M2": (320, 256)
            }
            img = img.resize(mode_resolutions[mode], Image.Resampling.LANCZOS)
            if self.enhance_var.get():
                img = ImageEnhance.Contrast(img).enhance(1.5)
                img = ImageEnhance.Color(img).enhance(1.3)
                img = self.adaptive_sharpen(img)
            logger.debug("Image preprocessing completed")
            return img
        except Exception as e:
            logger.error(f"Error in image preprocessing: {e}")
            raise

    def encode_image_to_sstv(self):
        if not self.current_image:
            logger.warning("No image available for encoding")
            return
        try:
            logger.info("Starting SSTV encoding process")
            self.status_label.config(text="Processing image...")
            self.root.update()
            mode = self.sstv_mode_var.get()
            samplerate = int(self.samplerate_var.get())
            logger.info(f"Encoding with mode: {mode}, sample rate: {samplerate}")
            img = self.preprocess_image(self.current_image.copy(), mode)
            if self.watermark_var.get():
                img = self.add_watermark(img)
            self.status_label.config(text="Generating SSTV signal...")
            self.root.update()
            sstv_classes = {
                "Robot36": Robot36,
                "Scottie 1": ScottieS1,
                "Martin M1": MartinM1,
                "Martin M2": MartinM2
            }
            if mode not in sstv_classes:
                logger.error(f"Unsupported SSTV mode: {mode}")
                messagebox.showerror("Error", f"Unsupported SSTV mode: {mode}")
                return
            sstv = sstv_classes[mode](img, samplerate, 8)
            self.status_label.config(text="Generating audio samples...")
            self.root.update()
            samples = np.array(list(sstv.gen_samples()), dtype=np.float32)
            max_val = np.max(np.abs(samples))
            if max_val > 0:
                samples = samples / max_val
            samples_int16 = np.int16(samples * 32767)
            if len(samples_int16.shape) == 1:
                wav_data = samples_int16
            else:
                wav_data = samples_int16[:, 0].copy()
            logger.info("Audio samples generated successfully")
            base_path = filedialog.asksaveasfilename(defaultextension=".wav", filetypes=[("WAV Files", "*.wav")], title=f"Save {mode} SSTV audio as...")
            if not base_path:
                logger.info("User cancelled file save")
                self.status_label.config(text="Ready")
                return
            base_path = os.path.splitext(base_path)[0]
            exported_files = []
            if self.export_wav_var.get():
                wav_path = f"{base_path}.wav"
                write(wav_path, samplerate, wav_data)
                exported_files.append(wav_path)
                self.setup_playback(wav_path)
                logger.info(f"WAV exported: {wav_path}")
            if self.export_mp3_var.get():
                mp3_path = f"{base_path}.mp3"
                self.export_to_mp3(wav_data, samplerate, mp3_path)
                exported_files.append(mp3_path)
                logger.info(f"MP3 exported: {mp3_path}")
            if self.export_ogg_var.get():
                ogg_path = f"{base_path}.ogg"
                self.export_to_ogg(wav_data, samplerate, ogg_path)
                exported_files.append(ogg_path)
                logger.info(f"OGG exported: {ogg_path}")
            if exported_files:
                logger.info(f"Encoding completed successfully. Exported: {exported_files}")
                messagebox.showinfo("Success", f"Exported {mode} SSTV audio:\n" + "\n".join(exported_files))
                self.status_label.config(text="Ready")
                duration_min, duration_sec = divmod(int(self.current_audio_length), 60)
                self.audio_info_label.config(text=f"Audio: {duration_min:02d}:{duration_sec:02d} ({self.current_audio_length:.1f}s)", fg="black")
                self.encode_time_label.config(text=f"Last encode: {datetime.now().strftime('%H:%M:%S')}", fg="black")
            else:
                logger.warning("No export formats selected")
                messagebox.showwarning("No Export", "Please select at least one export format")
        except Exception as e:
            logger.error(f"Encoding error: {e}")
            messagebox.showerror("Encoding Error", str(e))
            self.status_label.config(text="Error occurred")

    def export_to_mp3(self, audio_data, samplerate, output_path):
        try:
            logger.info(f"Exporting to MP3: {output_path}")
            temp_wav = f"{output_path}_temp.wav"
            write(temp_wav, samplerate, audio_data)
            cmd = ['ffmpeg', '-i', temp_wav, '-acodec', 'libmp3lame', '-ab', '128k', output_path, '-y']
            subprocess.run(cmd, check=True, capture_output=True)
            os.remove(temp_wav)
            logger.info("MP3 export completed successfully")
        except Exception as e:
            logger.error(f"MP3 export error: {e}")
            messagebox.showerror("MP3 Export Error", f"Failed to export MP3: {str(e)}\nMake sure ffmpeg is installed.")

    def export_to_ogg(self, audio_data, samplerate, output_path):
        try:
            logger.info(f"Exporting to OGG: {output_path}")
            temp_wav = f"{output_path}_temp.wav"
            write(temp_wav, samplerate, audio_data)
            cmd = ['ffmpeg', '-i', temp_wav, '-acodec', 'libvorbis', '-ab', '128k', output_path, '-y']
            subprocess.run(cmd, check=True, capture_output=True)
            os.remove(temp_wav)
            logger.info("OGG export completed successfully")
        except Exception as e:
            logger.error(f"OGG export error: {e}")
            messagebox.showerror("OGG Export Error", f"Failed to export OGG: {str(e)}\nMake sure ffmpeg is installed.")

    def setup_playback(self, wav_path):
        try:
            logger.info(f"Setting up playback for: {wav_path}")
            with wave.open(wav_path, 'rb') as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                self.current_audio_length = frames / float(rate)
                logger.info(f"Audio length: {self.current_audio_length:.2f} seconds")
            self.current_wav_path = wav_path
            self.play_button.config(state=tk.NORMAL)
            self.file_location_label.config(text=f"File: {os.path.basename(wav_path)}", fg="blue")
            logger.info("Playback setup completed successfully")
        except Exception as e:
            logger.error(f"Failed to setup playback: {e}")
            self.status_label.config(text="Failed to load audio")
            messagebox.showerror("Audio Error", str(e))

if __name__ == "__main__":
    logger.info("Starting SSTV Encoder Pro v3")
    try:
        if TkinterDnD:
            root = TkinterDnD.Tk()
            logger.info("Using TkinterDnD for drag and drop support")
        else:
            root = tk.Tk()
            logger.info("Using standard Tkinter (no drag and drop)")
    except Exception as e:
        logger.error(f"Failed to create root window: {e}")
        root = tk.Tk()
    try:
        app = SSTVEncoderV3(root)
        logger.info("Application started successfully")
        root.mainloop()
    except Exception as e:
        logger.error(f"Application error: {e}")
        raise