"""Cut the four rendered shots together with soft cross-dissolves, grade, add the soundtrack, export MP4.

python3 assemble.py <frames_dir> <music.wav> <out.mp4>
Each shot was rendered with HANDLE extra frames that play underneath the dissolve into the next shot.
"""
import subprocess
import sys

from shots import SHOTS, HANDLE

frames, music, out = sys.argv[1:4]
FPS = 30
XF = HANDLE / FPS                     # dissolve length (s)
order = ["A", "B", "C", "D"]
inputs, chain = [], []
for i, s in enumerate(order):
    inputs += ["-framerate", str(FPS), "-i", f"{frames}/{s}_%04d.png"]
t = 0.0; prev = "[0:v]"
for i in range(1, len(order)):
    t += SHOTS[order[i - 1]] / FPS
    lab = f"[x{i}]"
    chain.append(f"{prev}[{i}:v]xfade=transition=fade:duration={XF:.4f}:offset={t:.4f}{lab}")
    prev = lab
total = t + (SHOTS[order[-1]] + HANDLE) / FPS
# grade: gentle S-curve, a touch of warmth in the highlights, soft vignette, fade from/to black
grade = (f"{prev}format=gbrp,curves=master='0/0 0.06/0.045 0.5/0.5 0.9/0.93 1/1':r='0/0 0.5/0.51 1/1':b='0/0 0.5/0.49 1/1',"
         f"vignette=angle=0.42:mode=forward,fade=t=in:st=0:d=0.25,fade=t=out:st={total - 0.6:.3f}:d=0.6,format=yuv420p[v]")
chain.append(grade)
cmd = ["ffmpeg", "-loglevel", "error", "-y", *inputs, "-i", music, "-filter_complex", ";".join(chain),
       "-map", "[v]", "-map", f"{len(order)}:a", "-c:v", "libx264", "-preset", "slow", "-crf", "14", "-profile:v", "high",
       "-tune", "film", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
       "-c:a", "aac", "-b:a", "320k", "-t", f"{total:.3f}", "-movflags", "+faststart", out]
subprocess.run(cmd, check=True)
print("wrote", out, f"{total:.2f}s")
