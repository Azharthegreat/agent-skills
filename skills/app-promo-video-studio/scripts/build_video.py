# -*- coding: utf-8 -*-
"""
build_video.py - assemble scene PNGs + per-scene VO + music into a finished vertical promo.

It AUTO-TIMES the video: each scene lasts long enough to contain its VO line plus padding, so
English and Urdu versions (different VO lengths) both fit without hand-tuning. It computes the
xfade offsets, places each VO line at its scene start, loudnorm-mixes music under the voice, and
encodes a clean 1080x1920 H.264/AAC MP4.

Usage:
    python build_video.py --scenes <dir> --vo <dir> --music <wav> --out <mp4> [--ffmpeg <path>]
                          [--min 3.0] [--pad 0.5] [--xfade 0.4] [--music-vol 0.85] [--fps 30] [--zoom 0.05]

- scenes dir: s1.png .. sN.png
- vo dir:     l1.mp3 .. lN.mp3  (optional; omit --vo for a music-only cut)
- music wav:  already loudnormed bed (see build_music.sh). Must be >= final duration.

The caller is responsible for making the music bed at least as long as the result; build_music.sh
takes a target length - pass it a few seconds more than the sum of scene durations.
"""
import sys, os, glob, json, argparse, subprocess

def dur(ffprobe, path):
    out = subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nk=1:nw=1", path], capture_output=True, text=True).stdout.strip()
    return float(out) if out else 0.0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenes", required=True); ap.add_argument("--vo", default="")
    ap.add_argument("--music", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--ffmpeg", default="ffmpeg"); ap.add_argument("--ffprobe", default="")
    ap.add_argument("--min", type=float, default=3.0); ap.add_argument("--pad", type=float, default=0.5)
    ap.add_argument("--xfade", type=float, default=0.4); ap.add_argument("--music-vol", type=float, default=0.85)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--zoom", type=float, default=0.0,
                    help="slow push-in per scene, e.g. 0.05 = 5%% over the scene (0 = static, the default)")
    a = ap.parse_args()
    os.environ["MSYS_NO_PATHCONV"] = "1"
    ffprobe = a.ffprobe or (a.ffmpeg[:-len("ffmpeg")] + "ffprobe" if a.ffmpeg.endswith("ffmpeg") else "ffprobe")
    if a.ffmpeg.lower().endswith("ffmpeg.exe"):
        ffprobe = a.ffmpeg[:-len("ffmpeg.exe")] + "ffprobe.exe"

    scenes = sorted(glob.glob(os.path.join(a.scenes, "s*.png")),
                    key=lambda p: int(os.path.basename(p)[1:-4]))
    n = len(scenes)
    if n == 0:
        sys.exit("no scenes found")
    vos = []
    if a.vo:
        for i in range(1, n+1):
            p = os.path.join(a.vo, f"l{i}.mp3")
            vos.append(p if os.path.isfile(p) else None)
    else:
        vos = [None]*n

    # scene duration = max(min, vo_dur + pad)
    scene_d = []
    for i in range(n):
        vd = dur(ffprobe, vos[i]) if vos[i] else 0.0
        scene_d.append(round(max(a.min, vd + a.pad), 2))

    # Cumulative scene start times on the growing xfade composite. Each xfade begins `xfade`
    # seconds before scene k ends, i.e. at start[k], so xfade_off[k-1] = start[k].
    start = [0.0]*n
    for i in range(1, n):
        start[i] = round(start[i-1] + scene_d[i-1] - a.xfade, 2)
    xfade_off = [round(start[i], 2) for i in range(1, n)]
    final = round(start[-1] + scene_d[-1], 2)

    # VO placement offsets (ms): scene start + small lead
    LEAD = 0.25
    vo_off_ms = [int((start[i] + LEAD)*1000) for i in range(n)]

    # ---- build filter_complex ----
    inp = []
    for i in range(n):
        inp += ["-loop", "1", "-framerate", str(a.fps), "-t", str(scene_d[i]), "-i", scenes[i]]
    inp += ["-i", a.music]
    vo_inputs = [v for v in vos if v]
    for v in vo_inputs:
        inp += ["-i", v]
    music_idx = n
    vo_start_idx = n + 1

    fc = ""
    for i in range(n):
        if a.zoom > 0:
            # Ken Burns push-in. Upscale first so the crop steps are sub-pixel at output size,
            # which keeps the zoom smooth instead of jittering one pixel at a time.
            frames = max(1, int(scene_d[i] * a.fps))
            fc += (f"[{i}:v]scale=2160:3840,zoompan=z='1+{a.zoom}*on/{frames}':"
                   f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps={a.fps},"
                   f"setsar=1,format=yuv420p[v{i}];")
        else:
            fc += f"[{i}:v]scale=1080:1920,setsar=1,fps={a.fps},format=yuv420p[v{i}];"
    prev = "[v0]"
    for k in range(1, n):
        lbl = f"[x{k}]" if k < n-1 else "[v]"
        fc += f"{prev}[v{k}]xfade=transition=fade:duration={a.xfade}:offset={xfade_off[k-1]}{lbl};"
        prev = lbl
    if n == 1:
        fc += "[v0]copy[v];"

    # audio
    if vo_inputs:
        j = vo_start_idx
        vo_lbls = []
        k = 0
        for i in range(n):
            if vos[i]:
                fc += f"[{j}]adelay={vo_off_ms[i]}|{vo_off_ms[i]}[d{k}];"
                vo_lbls.append(f"[d{k}]"); j += 1; k += 1
        fc += "".join(vo_lbls) + f"amix=inputs={len(vo_lbls)}:normalize=0:duration=longest," \
              f"aformat=sample_rates=48000:channel_layouts=stereo,apad,atrim=0:{final}[voc];"
        fc += f"[{music_idx}:a]volume={a.music_vol}[m];" \
              f"[m][voc]amix=inputs=2:normalize=0:duration=longest," \
              f"afade=t=out:st={round(final-1.3,2)}:d=1.3,alimiter=limit=0.96[a]"
    else:
        fc += f"[{music_idx}:a]volume=1.0,afade=t=out:st={round(final-1.3,2)}:d=1.3,atrim=0:{final}[a]"

    music_dur = dur(ffprobe, a.music)
    if music_dur and music_dur < final - 0.05:
        sys.stderr.write(f"WARNING: music bed is {music_dur}s but the video is {final}s. "
                         f"Rebuild the bed with build_music.sh <{int(final)+3}> or the audio will "
                         f"end early.\n")

    cmd = [a.ffmpeg, "-y"] + inp + ["-filter_complex", fc,
           "-map", "[v]", "-map", "[a]", "-r", str(a.fps),
           "-c:v", "libx264", "-preset", "medium", "-crf", "20",
           "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", "-t", str(final), a.out]
    print("scene_d:", scene_d, "final:", final)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stderr[-2000:]); sys.exit("ffmpeg failed")
    print("video written:", a.out, f"({final}s)")

if __name__ == "__main__":
    main()
