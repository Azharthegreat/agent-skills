#!/usr/bin/env bash
# build_music.sh - synthesize a soft, CONTINUOUS chord-pad music bed and loudnorm it.
#
# Usage: FFMPEG=/path/to/ffmpeg ./build_music.sh <out.wav> <target_seconds>
#
# Why this exact shape (all three are load-bearing, learned the hard way):
#  1. CONTINUOUS: each chord is sustained with NO fade-to-silence; consecutive chords are joined
#     with acrossfade. Per-chord fade-outs create dips that sound like the track "cuts" / stutters.
#  2. LOUDNORM: a raw synthesized sine pad sits near -25 dB and is INAUDIBLE under a continuous
#     voice-over. loudnorm to I=-16 LUFS brings it up so it is clearly heard beneath the VO.
#  3. Progression C-G-Am-F (repeat to length). Pleasant, non-cheesy, loops without a seam.
#
# Pair with a mix of: music(volume≈0.85 after loudnorm) + VO(volume 1.0), amix normalize=0, alimiter.
set -euo pipefail
FFMPEG="${FFMPEG:-ffmpeg}"
OUT="$1"; TARGET="${2:-32}"
# Temp dir must be a real OS path next to OUT: a native Windows ffmpeg cannot write to an
# MSYS `mktemp -d` (/tmp/...) path. Reuse OUT's own directory, which is already a real path.
TMP="$(dirname "$OUT")/_musictmp_$$"; mkdir -p "$TMP"; trap 'rm -rf "$TMP"' EXIT

gen () { # name f1 f2 f3 fbass  (4.6s sustained chord, no fade)
  "$FFMPEG" -y -f lavfi -i "sine=f=$2:d=4.6" -f lavfi -i "sine=f=$3:d=4.6" \
    -f lavfi -i "sine=f=$4:d=4.6" -f lavfi -i "sine=f=$5:d=4.6" \
    -filter_complex "[0]volume=0.5[a];[1]volume=0.42[b];[2]volume=0.36[c];[3]volume=0.62[d];[a][b][c][d]amix=inputs=4:normalize=0,lowpass=f=1100" \
    -c:a pcm_s16le "$TMP/$1.wav" 2>/dev/null
}
# Enough chords to cover TARGET (4.6s each minus 0.8 crossfade ≈ 3.8s net; add margin).
NEED=$(python -c "import math;print(max(4,math.ceil(($TARGET+2)/3.8)))")
PROG=(1c:261.63:329.63:392.00:130.81 2g:196.00:246.94:293.66:98.00 3a:220.00:261.63:329.63:110.00 4f:174.61:220.00:261.63:87.31)
INPUTS=(); FILTER=""; idx=0
for ((n=0; n<NEED; n++)); do
  IFS=: read -r nm f1 f2 f3 fb <<< "${PROG[$((n%4))]}"
  gen "c$n$nm" "$f1" "$f2" "$f3" "$fb"
  INPUTS+=(-i "$TMP/c$n$nm.wav")
done
# acrossfade chain for a seamless continuous bed
prev="[0]"
for ((n=1; n<NEED; n++)); do
  lbl="[x$n]"; [[ $n -eq $((NEED-1)) ]] && lbl="[xo]"
  FILTER+="${prev}[$n]acrossfade=d=0.8:c1=tri:c2=tri${lbl};"; prev="${lbl}"
done
FADEOUT=$(python -c "print(max(1.0,$TARGET-1.2))")
"$FFMPEG" -y "${INPUTS[@]}" -filter_complex \
  "${FILTER}[xo]aecho=0.8:0.85:70:0.2,afade=t=in:d=0.5,afade=t=out:st=${FADEOUT}:d=1.2,atrim=0:${TARGET}[c]" \
  -map "[c]" -c:a pcm_s16le "$TMP/cont.wav" 2>/dev/null
# loudnorm so it is actually audible under the voice
"$FFMPEG" -y -i "$TMP/cont.wav" -af "loudnorm=I=-16:TP=-2:LRA=11" -c:a pcm_s16le "$OUT" 2>/dev/null
echo "music written: $OUT (${TARGET}s, loudnorm -16 LUFS)"
