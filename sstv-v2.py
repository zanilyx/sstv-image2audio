"""
SSTV Encoder Pro v2
-------------------
A modern GUI tool to encode images into SSTV (Robot36, Scottie 1, Martin M1, Martin M2) audio 
with real-time playback, image enhancement, drag-and-drop, preview, watermark, and dark mode.
"""
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageEnhance, ImageFilter, ImageOps, ImageDraw, ImageFont
import numpy as np
from scipy.io.wavfile import write
from pysstv.color import Robot36, ScottieS1, MartinM1, MartinM2
import simpleaudio as sa
import threading
import time
import wave
import subprocess
import os
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.FileHandler('sstv_encoder.log')  # File output
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

class SSTVEncoderV2:
    """
    Enhanced SSTV Encoder with drag-and-drop, preview, watermark, export options, and dark mode.
    """
    def __init__(self, root):
        logger.info("Initializing SSTV Encoder Pro v2")
        self.root = root
        self.wave_obj = None
        self.play_obj = None
        self.playback_active = False
        self.playback_thread = None
        self.audio_length = 0
        self.current_image = None
        self.current_image_path = None
        self.dark_mode = False
        self.playback_lock = threading.Lock()  # Thread safety for playback
        self.preview_photo = None  # Store preview photo reference
        self.preview_lock = threading.Lock()  # Thread safety for preview
        self.setup_ui()
        self.setup_drag_drop()
        logger.info("SSTV Encoder Pro v2 initialized successfully")

    def setup_ui(self):
        """Set up the main GUI layout and widgets."""
        logger.info("Setting up UI")
        self.root.title("📡 SSTV Encoder Pro v2")
        self.root.geometry("800x700")
        self.root.resizable(True, True)

        # Main container
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Title and theme toggle
        title_frame = tk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(title_frame, text="SSTV Encoder Pro v2", font=("Arial", 16, "bold")).pack(side=tk.LEFT)
        
        # Dark mode toggle
        self.dark_mode_var = tk.BooleanVar(value=False)
        self.dark_mode_btn = tk.Checkbutton(title_frame, text="🌙 Dark Mode", 
                                          variable=self.dark_mode_var, 
                                          command=self.toggle_dark_mode)
        self.dark_mode_btn.pack(side=tk.RIGHT)

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
        tk.Checkbutton(left_panel, text="🖼️ Auto-enhance", variable=self.enhance_var, 
                      command=self.update_preview).pack(anchor=tk.W)

        # Watermark section
        tk.Label(left_panel, text="Watermark:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(10, 0))
        self.watermark_var = tk.BooleanVar(value=False)
        tk.Checkbutton(left_panel, text="Add watermark", variable=self.watermark_var, 
                      command=self.update_preview).pack(anchor=tk.W)
        
        tk.Label(left_panel, text="Callsigns/Text:").pack(anchor=tk.W)
        self.watermark_text = tk.StringVar(value="CALLSIGN")
        watermark_entry = tk.Entry(left_panel, textvariable=self.watermark_text, width=15)
        watermark_entry.pack(anchor=tk.W, pady=(0, 10))
        watermark_entry.bind('<KeyRelease>', lambda e: self.update_preview())

        # Buttons
        tk.Button(left_panel, text="📁 Select Image", command=self.select_image,
                 height=2, width=20).pack(pady=5)
        
        tk.Button(left_panel, text="📷 Encode to SSTV", command=self.start_encoding_thread,
                 height=2, width=20).pack(pady=5)

        # Export options
        tk.Label(left_panel, text="Export Options:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(10, 0))
        self.export_wav_var = tk.BooleanVar(value=True)
        self.export_mp3_var = tk.BooleanVar(value=False)
        self.export_ogg_var = tk.BooleanVar(value=False)
        
        tk.Checkbutton(left_panel, text="WAV", variable=self.export_wav_var).pack(anchor=tk.W)
        tk.Checkbutton(left_panel, text="MP3", variable=self.export_mp3_var).pack(anchor=tk.W)
        tk.Checkbutton(left_panel, text="OGG", variable=self.export_ogg_var).pack(anchor=tk.W)

        # Right panel for preview and playback
        right_panel = tk.Frame(main_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Preview area
        tk.Label(right_panel, text="Image Preview:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        self.preview_canvas = tk.Canvas(right_panel, width=320, height=256, bg="white", relief=tk.SUNKEN, bd=1)
        self.preview_canvas.pack(pady=(0, 10))
        
        # Drag and drop hint
        self.drop_hint = tk.Label(self.preview_canvas, text="Drop image here\nor click 'Select Image'", 
                                 fg="gray", font=("Arial", 12))
        self.preview_canvas.create_window(160, 128, window=self.drop_hint)

        # Playback controls
        playback_frame = tk.Frame(right_panel)
        playback_frame.pack(fill=tk.X, pady=10)

        self.play_button = tk.Button(playback_frame, text="▶", width=5, command=self.toggle_playback, state=tk.DISABLED)
        self.play_button.pack(side=tk.LEFT, padx=5)

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(playback_frame, orient="horizontal", 
                                          length=300, mode="determinate", 
                                          variable=self.progress_var)
        self.progress_bar.pack(side=tk.LEFT, padx=5)

        self.time_label = tk.Label(playback_frame, text="00:00 / 00:00")
        self.time_label.pack(side=tk.LEFT, padx=5)

        # Status label
        self.status_label = tk.Label(right_panel, text="Ready - Drop an image to get started", fg="gray")
        self.status_label.pack(pady=10)
        logger.info("UI setup completed")

    def setup_drag_drop(self):
        """Set up drag and drop functionality."""
        if TkinterDnD is None:
            logger.warning("Drag and drop not available - tkinterdnd2 not installed")
            return
        
        try:
            self.preview_canvas.drop_target_register(DND_FILES)
            self.preview_canvas.dnd_bind('<<Drop>>', self.handle_drop)
            logger.info("Drag and drop setup completed")
        except Exception as e:
            logger.error(f"Failed to setup drag and drop: {e}")

    def handle_drop(self, event):
        """Handle file drop events."""
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
        """Update the preview canvas with the processed image."""
        if not self.current_image:
            logger.debug("No image to preview")
            return
        
        # Run preview update in background to avoid blocking UI
        threading.Thread(target=self._update_preview_thread, daemon=True).start()

    def _update_preview_thread(self):
        """Background thread for updating preview."""
        try:
            logger.debug("Updating preview in background")
            mode = self.sstv_mode_var.get()
            img = self.preprocess_image(self.current_image.copy(), mode)
            
            # Add watermark if enabled
            if self.watermark_var.get():
                img = self.add_watermark(img)
            
            # Convert to PhotoImage for display
            img.thumbnail((320, 256), Image.LANCZOS)
            
            # Convert PIL Image to PhotoImage properly
            with self.preview_lock:
                # Convert PIL Image to PhotoImage using BytesIO
                import io
                img_bytes = io.BytesIO()
                img.save(img_bytes, format='PNG')
                img_bytes.seek(0)
                self.preview_photo = tk.PhotoImage(data=img_bytes.getvalue())
            
            # Update canvas in main thread
            self.root.after(0, self._update_preview_canvas)
            logger.debug("Preview updated successfully")
            
        except Exception as e:
            logger.error(f"Preview error: {e}")
            self.root.after(0, lambda: self.status_label.config(text=f"Preview error: {str(e)}"))

    def _update_preview_canvas(self):
        """Update the canvas in the main thread."""
        try:
            self.preview_canvas.delete("all")
            if self.preview_photo:
                self.preview_canvas.create_image(160, 128, image=self.preview_photo)
            logger.debug("Canvas updated successfully")
        except Exception as e:
            logger.error(f"Canvas update error: {e}")

    def toggle_dark_mode(self):
        """Toggle between light and dark themes."""
        logger.info(f"Toggling dark mode: {self.dark_mode_var.get()}")
        self.dark_mode = self.dark_mode_var.get()
        
        # Run theme update in background to avoid blocking UI
        threading.Thread(target=self._apply_theme, daemon=True).start()

    def _apply_theme(self):
        """Apply theme in background thread."""
        try:
            if self.dark_mode:
                logger.info("Applying dark theme")
                self._apply_dark_theme()
            else:
                logger.info("Applying light theme")
                self._apply_light_theme()
        except Exception as e:
            logger.error(f"Theme application error: {e}")

    def _apply_dark_theme(self):
        """Apply dark theme to all widgets."""
        def apply_to_widget(widget):
            try:
                if isinstance(widget, (tk.Label, tk.Button, tk.Checkbutton, tk.Entry, tk.OptionMenu)):
                    widget.configure(bg='#2b2b2b', fg='white')
                elif isinstance(widget, tk.Frame):
                    widget.configure(bg='#2b2b2b')
                elif isinstance(widget, tk.Canvas):
                    widget.configure(bg='#1e1e1e')
            except:
                pass
            
            # Recursively apply to children
            for child in widget.winfo_children():
                apply_to_widget(child)
        
        # Apply to root and all children
        self.root.configure(bg='#2b2b2b')
        apply_to_widget(self.root)

    def _apply_light_theme(self):
        """Apply light theme to all widgets."""
        def apply_to_widget(widget):
            try:
                if isinstance(widget, (tk.Label, tk.Button, tk.Checkbutton, tk.Entry, tk.OptionMenu)):
                    widget.configure(bg='SystemButtonFace', fg='black')
                elif isinstance(widget, tk.Frame):
                    widget.configure(bg='SystemButtonFace')
                elif isinstance(widget, tk.Canvas):
                    widget.configure(bg='white')
            except:
                pass
            
            # Recursively apply to children
            for child in widget.winfo_children():
                apply_to_widget(child)
        
        # Apply to root and all children
        self.root.configure(bg='SystemButtonFace')
        apply_to_widget(self.root)

    def select_image(self):
        """Select an image file using file dialog."""
        logger.info("Opening file dialog for image selection")
        filepath = filedialog.askopenfilename(filetypes=[
            ("Image Files", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff")
        ])
        if filepath:
            logger.info(f"Image selected: {filepath}")
            self.load_image(filepath)

    def load_image(self, filepath):
        """Load and display an image."""
        try:
            logger.info(f"Loading image: {filepath}")
            self.current_image_path = filepath
            self.current_image = Image.open(filepath)
            self.update_preview()
            self.status_label.config(text=f"Loaded: {os.path.basename(filepath)}")
            logger.info(f"Image loaded successfully: {os.path.basename(filepath)}")
        except Exception as e:
            logger.error(f"Failed to load image: {e}")
            messagebox.showerror("Error", f"Failed to load image: {str(e)}")

    def add_watermark(self, img):
        """Add text watermark to the image."""
        try:
            logger.debug("Adding watermark to image")
            draw = ImageDraw.Draw(img)
            # Try to use a default font, fallback to basic if not available
            try:
                font = ImageFont.truetype("arial.ttf", 20)
            except:
                font = ImageFont.load_default()
            
            text = self.watermark_text.get()
            # Get text size
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # Position text in bottom-right corner
            x = img.width - text_width - 10
            y = img.height - text_height - 10
            
            # Draw text with outline for visibility
            draw.text((x+1, y+1), text, fill="black", font=font)
            draw.text((x, y), text, fill="white", font=font)
            logger.debug("Watermark added successfully")
            
        except Exception as e:
            logger.error(f"Watermark error: {e}")
        
        return img

    def start_encoding_thread(self):
        """Start encoding in a background thread."""
        if not self.current_image:
            logger.warning("No image selected for encoding")
            messagebox.showwarning("No Image", "Please select an image first")
            return
        logger.info("Starting encoding thread")
        threading.Thread(target=self.encode_image_to_sstv, daemon=True).start()

    def toggle_playback(self):
        """Toggle audio playback."""
        with self.playback_lock:
            if self.playback_active:
                logger.info("Stopping playback")
                self.stop_playback()
            else:
                logger.info("Starting playback")
                self.start_playback()

    def start_playback(self):
        """Start audio playback."""
        with self.playback_lock:
            if self.wave_obj:
                try:
                    logger.info("Starting audio playback")
                    self.playback_active = True
                    # Update UI immediately
                    self.root.after(0, lambda: self.play_button.config(text="⏹"))
                    self.play_obj = self.wave_obj.play()
                    self.playback_thread = threading.Thread(target=self.update_playback_progress, daemon=True)
                    self.playback_thread.start()
                    logger.info("Playback started successfully")
                except Exception as e:
                    logger.error(f"Failed to start playback: {e}")
                    self.playback_active = False
                    self.root.after(0, lambda: messagebox.showerror("Playback Error", f"Failed to start playback: {str(e)}"))
            else:
                logger.warning("No wave object available for playback")
                self.root.after(0, lambda: messagebox.showwarning("No Audio", "No audio file loaded for playback"))

    def stop_playback(self):
        """Stop audio playback."""
        with self.playback_lock:
            try:
                logger.info("Stopping audio playback")
                self.playback_active = False
                # Update UI immediately
                self.root.after(0, lambda: self.play_button.config(text="▶"))
                if self.play_obj:
                    self.play_obj.stop()
                    self.play_obj = None
                self.root.after(0, lambda: self.progress_var.set(0))
                self.root.after(0, lambda: self.update_time_label(0, self.audio_length))
                logger.info("Playback stopped successfully")
            except Exception as e:
                logger.error(f"Error stopping playback: {e}")

    def update_playback_progress(self):
        """Update progress bar during playback."""
        logger.info("Starting playback progress thread")
        start_time = time.time()
        try:
            while self.playback_active and self.play_obj and self.play_obj.is_playing():
                elapsed = time.time() - start_time
                progress = (elapsed / self.audio_length) * 100 if self.audio_length > 0 else 0
                # Directly update progress bar and time label (thread-safe for DoubleVar and label text)
                self.progress_var.set(progress)
                self.update_time_label(elapsed, self.audio_length)
                time.sleep(0.1)
            logger.info("Playback finished naturally")
            # Use root.after to safely update play button and reset UI
            self.root.after(0, self.stop_playback)
        except Exception as e:
            logger.error(f"Error in playback progress thread: {e}")
            self.root.after(0, self.stop_playback)
        finally:
            logger.info("Playback progress thread ending")
            if self.playback_active:
                self.root.after(0, self.stop_playback)

    def update_time_label(self, current, total):
        """Update time label."""
        try:
            current_min, current_sec = divmod(int(current), 60)
            total_min, total_sec = divmod(int(total), 60)
            self.time_label.config(text=f"{current_min:02d}:{current_sec:02d} / {total_min:02d}:{total_sec:02d}")
        except Exception as e:
            logger.error(f"Error updating time label: {e}")

    def adaptive_sharpen(self, img):
        """Apply adaptive sharpening."""
        try:
            img = img.filter(ImageFilter.UnsharpMask(radius=1, percent=200, threshold=1))
            return img
        except Exception as e:
            logger.error(f"Error in adaptive sharpen: {e}")
            return img

    def preprocess_image(self, img, mode):
        """Enhanced image processing pipeline."""
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
            img = img.resize(mode_resolutions[mode], Image.LANCZOS)
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
        """Main encoding logic with multiple export options."""
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
            
            # Process image
            img = self.preprocess_image(self.current_image.copy(), mode)
            
            # Add watermark if enabled
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
            
            if samples_int16.ndim == 1:
                wav_data = samples_int16
            else:
                wav_data = samples_int16[:, 0].copy()
            
            logger.info("Audio samples generated successfully")
            
            # Export files based on user selection
            base_path = filedialog.asksaveasfilename(
                defaultextension=".wav",
                filetypes=[("WAV Files", "*.wav")],
                title=f"Save {mode} SSTV audio as..."
            )
            
            if not base_path:
                logger.info("User cancelled file save")
                self.status_label.config(text="Ready")
                return
            
            # Remove extension for base path
            base_path = os.path.splitext(base_path)[0]
            
            exported_files = []
            
            # Export WAV
            if self.export_wav_var.get():
                wav_path = f"{base_path}.wav"
                write(wav_path, samplerate, wav_data)
                exported_files.append(wav_path)
                self.setup_playback(wav_path)
                logger.info(f"WAV exported: {wav_path}")
            
            # Export MP3
            if self.export_mp3_var.get():
                mp3_path = f"{base_path}.mp3"
                self.export_to_mp3(wav_data, samplerate, mp3_path)
                exported_files.append(mp3_path)
                logger.info(f"MP3 exported: {mp3_path}")
            
            # Export OGG
            if self.export_ogg_var.get():
                ogg_path = f"{base_path}.ogg"
                self.export_to_ogg(wav_data, samplerate, ogg_path)
                exported_files.append(ogg_path)
                logger.info(f"OGG exported: {ogg_path}")
            
            if exported_files:
                logger.info(f"Encoding completed successfully. Exported: {exported_files}")
                messagebox.showinfo("Success", f"Exported {mode} SSTV audio:\n" + "\n".join(exported_files))
                self.status_label.config(text="Ready")
            else:
                logger.warning("No export formats selected")
                messagebox.showwarning("No Export", "Please select at least one export format")
                
        except Exception as e:
            logger.error(f"Encoding error: {e}")
            messagebox.showerror("Encoding Error", str(e))
            self.status_label.config(text="Error occurred")

    def export_to_mp3(self, audio_data, samplerate, output_path):
        """Export audio to MP3 using ffmpeg."""
        try:
            logger.info(f"Exporting to MP3: {output_path}")
            # Create temporary WAV file
            temp_wav = f"{output_path}_temp.wav"
            write(temp_wav, samplerate, audio_data)
            
            # Convert to MP3 using ffmpeg
            cmd = ['ffmpeg', '-i', temp_wav, '-acodec', 'libmp3lame', '-ab', '128k', output_path, '-y']
            subprocess.run(cmd, check=True, capture_output=True)
            
            # Clean up temp file
            os.remove(temp_wav)
            logger.info("MP3 export completed successfully")
            
        except Exception as e:
            logger.error(f"MP3 export error: {e}")
            messagebox.showerror("MP3 Export Error", f"Failed to export MP3: {str(e)}\nMake sure ffmpeg is installed.")

    def export_to_ogg(self, audio_data, samplerate, output_path):
        """Export audio to OGG using ffmpeg."""
        try:
            logger.info(f"Exporting to OGG: {output_path}")
            # Create temporary WAV file
            temp_wav = f"{output_path}_temp.wav"
            write(temp_wav, samplerate, audio_data)
            
            # Convert to OGG using ffmpeg
            cmd = ['ffmpeg', '-i', temp_wav, '-acodec', 'libvorbis', '-ab', '128k', output_path, '-y']
            subprocess.run(cmd, check=True, capture_output=True)
            
            # Clean up temp file
            os.remove(temp_wav)
            logger.info("OGG export completed successfully")
            
        except Exception as e:
            logger.error(f"OGG export error: {e}")
            messagebox.showerror("OGG Export Error", f"Failed to export OGG: {str(e)}\nMake sure ffmpeg is installed.")

    def setup_playback(self, wav_path):
        """Prepare audio playback."""
        try:
            logger.info(f"Setting up playback for: {wav_path}")
            if self.wave_obj:
                self.stop_playback()
            
            with wave.open(wav_path, 'rb') as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                self.audio_length = frames / float(rate)
                logger.info(f"Audio length: {self.audio_length:.2f} seconds")
            
            self.wave_obj = sa.WaveObject.from_wave_file(wav_path)
            self.play_obj = None
            self.play_button.config(state=tk.NORMAL)
            self.progress_var.set(0)
            self.update_time_label(0, self.audio_length)
            logger.info("Playback setup completed successfully")
            
        except Exception as e:
            logger.error(f"Failed to setup playback: {e}")
            self.status_label.config(text="Failed to load audio")
            messagebox.showerror("Audio Error", str(e))

if __name__ == "__main__":
    logger.info("Starting SSTV Encoder Pro v2")
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
        app = SSTVEncoderV2(root)
        logger.info("Application started successfully")
        root.mainloop()
    except Exception as e:
        logger.error(f"Application error: {e}")
        raise 