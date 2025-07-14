# SSTV-Image2Audio

A modern, robust GUI tool to encode images into SSTV (Robot36, Scottie 1, Martin M1, Martin M2) audio with real-time playback, image enhancement, drag-and-drop, watermarking, and more. **v3 is the recommended version.**

---

## Features (v3)

- **Modern Tkinter GUI**
- **Drag-and-drop** image support (with tkinterdnd2)
- **Image preview** with auto-enhance and watermark overlay
- **SSTV encoding**: Robot36, Scottie 1, Martin M1, Martin M2
- **Export**: WAV, MP3, OGG (MP3/OGG require ffmpeg)
- **Custom sample rates**
- **Statistics panel**: image size, audio duration, last encode time
- **Playback**: Play audio in a fully separate window/process (no crashes, no UI freeze)
  - Progress bar and time label in playback window
- **No external dependencies for playback** (uses simpleaudio)
- **Batch encoding, decode, and other advanced features planned**

---

## Quick Start (v3)

1. **Install requirements:**
   ```bash
   pip install -r requirements.txt
   ```
   - For drag-and-drop: `pip install tkinterdnd2`
   - For MP3/OGG export: [Install ffmpeg](https://ffmpeg.org/download.html) and ensure it's in your PATH

2. **Run the encoder:**
   ```bash
   python sstv-v3.py
   ```

3. **Usage:**
   - Drag and drop or select an image
   - Optionally enable auto-enhance and watermark
   - Choose SSTV mode and sample rate
   - Click "Encode to SSTV" and save the audio file
   - Click "Play Audio" to open a separate playback window (with progress bar)

---

## File Structure

- `sstv-v3.py` — Main GUI encoder (recommended)
- `playback_window.py` — Standalone playback window (launched by v3)
- `sstv-v2.py` — Previous version with integrated playback (legacy)
- `sstv-v1.py` — Minimal/legacy version (see below)
- `requirements.txt` — Python dependencies
- `LICENSE` — License info
- `README.md` — This file

---

## Why Use v3?

- **No more UI freezes or crashes during playback**
- **Modern, user-friendly interface**
- **Separate playback process**: main app is always responsive
- **Watermark, drag-and-drop, and more**
- **Actively maintained and extensible**

---

## Old README (v1, legacy)

*The following is the original README for v1. For most users, v3 is recommended.*

---

```
SSTV-Image2Audio
----------------
A modern GUI tool to encode images into SSTV (Robot36, Scottie 1, Martin M1, Martin M2) audio with real-time playback and image enhancement.

Features:
- Tkinter GUI
- Image enhancement (contrast, color, sharpening)
- SSTV encoding (Robot36, Scottie 1, Martin M1, Martin M2)
- WAV export
- Real-time playback (simpleaudio)

Usage:
1. Install requirements: `pip install -r requirements.txt`
2. Run: `python sstv-v1.py`
3. Select image, encode, and play audio

Requirements:
- Python 3.7+
- Pillow, numpy, scipy, pysstv, simpleaudio

License: MIT
```

---

## License

See [LICENSE](LICENSE). 
