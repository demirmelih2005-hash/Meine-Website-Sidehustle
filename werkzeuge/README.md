# Werkzeuge

## `tiktok-vorschnitt.sh`

Macht aus einem Rohvideo in einem Schritt einen Vorschnitt:

1. **Auto-Editor** entfernt Pausen und Atmer.
2. **Whisper** (von OpenAI) schreibt deutsche Untertitel.
3. **ffmpeg** brennt die Untertitel groß und gut lesbar ins Video.

Der Schnitt läuft bei Claude, nicht auf deinem Laptop: Video in den Chat schicken, und du bekommst die fertige Datei zurück. Feinschliff (Hook, Reihenfolge, Musik) machst du danach wie gewohnt in deiner Schnitt-App.

Beide Programme sind kostenlos und Open Source:
- Auto-Editor: https://github.com/WyattBlue/auto-editor
- Whisper: https://github.com/openai/whisper
