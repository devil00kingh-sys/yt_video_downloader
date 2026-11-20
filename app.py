"""
YouTube Downloader - Flask + yt-dlp
Video (multiple resolutions) aur Audio (MP3 / M4A, multiple bitrates).
Sirf apne content ya jis content ko download karne ki permission hai, uske liye use karein.
"""
import os
import ipaddress
import shutil
import socket
import tempfile
from urllib.parse import urlparse

import yt_dlp
from flask import Flask, jsonify, request, send_file, send_from_directory

app = Flask(__name__, static_folder="static")

AUDIO_BITRATES = ["128", "192", "320"]


def valid_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        host = parsed.hostname
        port = parsed.port
    except Exception:
        return False
    if (
        parsed.scheme not in ("http", "https")
        or not host
        or parsed.username is not None
        or parsed.password is not None
        or port not in (None, 80, 443)
        or host.lower().endswith((".localhost", ".local", ".internal", ".test"))
    ):
        return False

    try:
        addresses = {ipaddress.ip_address(host)}
    except ValueError:
        # Resolve hostnames before handing them to yt-dlp, and reject private,
        # loopback, link-local, and otherwise non-public destinations.
        try:
            addresses = {
                ipaddress.ip_address(result[4][0])
                for result in socket.getaddrinfo(host, port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)
            }
        except (OSError, ValueError):
            return False
    return bool(addresses) and all(address.is_global for address in addresses)


def fmt_size(num_bytes):
    return round(num_bytes / 1024 / 1024, 1) if num_bytes else None


@app.get("/")
def index():
    return send_from_directory("static", "index.html")


@app.post("/api/info")
def info():
    url = (request.get_json(silent=True) or {}).get("url", "").strip()
    if not valid_url(url):
        return jsonify(error="Please paste a valid public video or audio link (HTTP or HTTPS)."), 400

    opts = {"quiet": True, "noplaylist": True, "skip_download": True}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            data = ydl.extract_info(url, download=False)
    except Exception as e:
        return jsonify(error=f"Could not read this video: {str(e)[:200]}"), 400

    formats = data.get("formats", [])
    audio_sizes = [
        f.get("filesize") or f.get("filesize_approx") or 0
        for f in formats
        if f.get("vcodec") == "none" and f.get("acodec") != "none"
    ]
    best_audio = max(audio_sizes, default=0)

    best_by_height = {}
    for f in formats:
        h = f.get("height")
        if not h or f.get("vcodec") in (None, "none"):
            continue
        size = f.get("filesize") or f.get("filesize_approx") or 0
        if h not in best_by_height or size > best_by_height[h]:
            best_by_height[h] = size

    video = [
        {"height": h, "label": f"{h}p", "size_mb": fmt_size(s + best_audio)}
        for h, s in sorted(best_by_height.items(), reverse=True)
    ]
    audio = [{"fmt": "mp3", "abr": b, "label": f"MP3 {b} kbps"} for b in AUDIO_BITRATES]
    audio.append({"fmt": "m4a", "abr": "best", "label": "M4A (original quality)"})

    return jsonify(
        title=data.get("title"),
        channel=data.get("uploader"),
        thumbnail=data.get("thumbnail"),
        duration=data.get("duration"),
        video=video,
        audio=audio,
    )


@app.get("/api/download")
def download():
    url = request.args.get("url", "").strip()
    kind = request.args.get("type", "video")
    if not valid_url(url):
        return jsonify(error="Invalid link. Use a public HTTP or HTTPS video/audio URL."), 400

    tmp = tempfile.mkdtemp(prefix="ytdl_")
    opts = {
        "quiet": True,
        "noplaylist": True,
        "outtmpl": os.path.join(tmp, "%(id)s.%(ext)s"),
    }

    if kind == "audio":
        fmt = request.args.get("fmt", "mp3")
        abr = request.args.get("abr", "192")
        if fmt == "mp3":
            if abr not in AUDIO_BITRATES:
                abr = "192"
            opts["format"] = "bestaudio/best"
            opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": abr,
            }]
        else:
            opts["format"] = "bestaudio[ext=m4a]/bestaudio/best"
    else:
        try:
            height = int(request.args.get("height", "720"))
        except ValueError:
            height = 720
        opts["format"] = (
            f"bestvideo[height<={height}]+bestaudio/best[height<={height}]/best"
        )
        opts["merge_output_format"] = "mp4"

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            data = ydl.extract_info(url, download=True)
        files = [
            os.path.join(root, name)
            for root, _, names in os.walk(tmp)
            for name in names
            if not name.endswith((".part", ".ytdl"))
        ]
        if not files:
            raise RuntimeError(
                "yt-dlp finished without creating a media file. The selected format may be unavailable, "
                "or the server may have run out of temporary storage. Check the server logs for yt-dlp output."
            )
        path = max(files, key=os.path.getsize)
        ext = os.path.splitext(path)[1]
        safe_title = "".join(c for c in (data.get("title") or "video") if c not in '\\/:*?"<>|')[:80]
        resp = send_file(path, as_attachment=True, download_name=f"{safe_title}{ext}")
        resp.call_on_close(lambda: shutil.rmtree(tmp, ignore_errors=True))
        return resp
    except Exception as e:
        shutil.rmtree(tmp, ignore_errors=True)
        return jsonify(error=f"Download failed: {str(e)[:200]}"), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
