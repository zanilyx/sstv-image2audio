# SSTV Encoder Pro

A modern, user-friendly GUI tool to encode images into SSTV (Slow Scan Television) audio in various modes (Robot36, Scottie 1, Martin M1, Martin M2) with real-time playback and image enhancement.

## Features
- Encode images to SSTV audio (WAV) in Robot36, Scottie 1, Martin M1, and Martin M2 formats
- Image enhancement: auto-contrast, color boost, sharpening
- Selectable sample rate (44100, 48000, 22050 Hz)
- Real-time audio playback with progress bar
- User-friendly GUI (Tkinter)
- Cross-platform (Windows, Linux, macOS)

## Installation

1. **Clone the repository:**
   ```sh
   git clone https://github.com/yourusername/sstv-encoder-pro.git
   cd sstv-encoder-pro
   ```
2. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```

## Usage

1. Run the app:
   ```sh
   python sstv-v1.py
   ```
2. Select your desired SSTV mode and sample rate.
3. Click "Encode Image to SSTV" and choose an image file.
4. Save the generated WAV file and play it back or transmit it.
5. Use any SSTV decoder (e.g., MMSSTV, QSSTV) to decode the audio.

## Viewing SSTV Images on Android/iOS

**Android:**
- Download [Robot36 - SSTV Image Decoder](https://play.google.com/store/apps/details?id=xdsopl.robot36&hl=en) from the Play Store.
- Open the app, tap the menu, and select your WAV file to decode.

**iOS:**
- Download [SSTV Slow Scan TV](https://apps.apple.com/us/app/sstv-slow-scan-tv/id387910013) from the App Store.
- Use the app’s import/open feature to select your WAV file and decode the image.

## Dependencies
- Python 3.8+
- Pillow
- numpy
- scipy
- pysstv
- simpleaudio

Install all dependencies with:
```sh
pip install -r requirements.txt
```

## Supported Modes
- Robot36 (320x240)
- Scottie 1 (320x256)
- Martin M1 (320x256)
- Martin M2 (320x256)

## Troubleshooting
- If your decoded image is noisy or unclear, try different sample rates or disable/enable image enhancement.
- For best results, use high-contrast, sharp images.
- If you get errors about missing modules, ensure all dependencies are installed.

## License
See [LICENSE](LICENSE) for details. 