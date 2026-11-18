#!/usr/bin/env bash
# TikTok-Vorschnitt: Pausen raus (Auto-Editor) + deutsche Untertitel (Whisper)
#
# Benutzung:  ./tiktok-vorschnitt.sh rohvideo.mp4
# Ergebnis:   rohvideo_geschnitten.mp4   (Pausen entfernt)
#             rohvideo_geschnitten.srt   (Untertitel-Datei)
#             rohvideo_fertig.mp4        (Video mit eingebrannten Untertiteln)
#
# Einmalig installieren:
#   pip install auto-editor openai-whisper   (ffmpeg muss vorhanden sein)

set -euo pipefail

EINGABE="${1:?Bitte ein Video angeben, z. B. ./tiktok-vorschnitt.sh clip.mp4}"
NAME="${EINGABE%.*}"
GESCHNITTEN="${NAME}_geschnitten.mp4"
ORDNER="$(dirname "$EINGABE")"

echo "1/3 Pausen entfernen ..."
# --margin 0.15s lässt ein kleines Polster, damit es nicht abgehackt wirkt
auto-editor "$EINGABE" --margin 0.15sec --no-open --progress none -o "$GESCHNITTEN"

echo "2/3 Untertitel erstellen ..."
whisper "$GESCHNITTEN" --language de --model small --output_format srt \
  --output_dir "$ORDNER" --max_line_width 18 --max_line_count 2 --word_timestamps True

echo "3/3 Untertitel einbrennen ..."
SRT="${NAME}_geschnitten.srt"
ffmpeg -y -loglevel error -i "$GESCHNITTEN" \
  -vf "subtitles='${SRT}':force_style='Fontname=Arial,Fontsize=14,Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=0,Alignment=2,MarginV=90'" \
  -c:a copy "${NAME}_fertig.mp4"

echo "Fertig: ${NAME}_fertig.mp4"
