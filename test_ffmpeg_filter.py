"""Quick test: run landscape filter with ffmpeg to see exact error."""
import subprocess
fc = "[0:v]setsar=1,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:10[bg_v];[0:v]setsar=1,scale=1080:-1[fg_v];[bg_v][fg_v]overlay=(W-w)/2:(H-h)/2[v_out]"
cmd = [
    "ffmpeg", "-y", "-ss", "175", "-t", "2", "-i", "projects/5C5B5/video.mp4",
    "-filter_complex", fc, "-map", "[v_out]", "-map", "0:a?", "-c:v", "libx264", "-preset", "fast", "-f", "null", "-"
]
p = subprocess.run(cmd, capture_output=True, text=True, timeout=30, cwd="j:\\HEATMAP5")
print("Return:", p.returncode)
print("STDERR (last 2k):")
print(p.stderr[-2000:] if p.stderr else "")
