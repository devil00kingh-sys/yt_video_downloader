# Video and Audio Downloader (multiple qualities)

Flask + yt-dlp. Paste a public video or audio link, choose a quality, and download it. yt-dlp supports many sites, including Instagram and Facebook, but site support can change and some links require login/cookies.

## Setup
1. Python 3.9+ aur **ffmpeg** install karein (video+audio merge aur MP3 ke liye zaroori).
   - Windows: `winget install ffmpeg`
   - Mac: `brew install ffmpeg`
   - Linux: `sudo apt install ffmpeg`
2. Dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Run:
   ```
   python app.py
   ```
4. Browser me kholein: http://127.0.0.1:5000

## Features
- Video: 144p se 4K tak (jo available ho), MP4 output
- Audio: MP3 128 / 192 / 320 kbps, ya original M4A
- Thumbnail, title, duration aur approx size preview
- Temp files download ke baad auto-delete
- No app-level video duration limit

## Tips
- Agar download fail ho to yt-dlp update karein: `pip install -U yt-dlp` (YouTube baar baar change hota hai).
- Playlist support nahi hai, sirf single video.
- Supported sites list: https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md

## Note
YouTube ke Terms of Service aur copyright ka dhyan rakhein. Sirf apna content ya jisme permission ho, wahi download karein.
