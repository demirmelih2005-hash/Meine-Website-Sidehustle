#!/usr/bin/env python3
"""Website-Baukasten: baut aus einer Kunden-Datei eine fertige Website mit Unterseiten.

Aufruf:
    python3 generator.py beispiel/veedel-cut.json ausgabe/veedel-cut

Die Kunden-Datei (JSON) hat bis zu fünf Teile:
    fragebogen  – die Antworten aus dem Kunden-Fragebogen (Datenblock am Ende der WhatsApp-Nachricht)
    inhalt      – Texte, die Claude daraus schreibt (Überschriften, Vorteile, FAQ ...)
    design      – Thema (nacht, hell, edel) und Farben
    seite       – Domain, Hoster, Ersteller, Demo-Kennzeichen
    fotos       – optional: echte Fotos (siehe README)
Als Eingabe geht auch direkt der nackte Datenblock aus dem Fragebogen oder die ganze
WhatsApp-Nachricht als .txt. Fehlt ein Text in "inhalt", nimmt der Generator Angaben aus dem Fragebogen.

Nur Python mit Bordmitteln, nichts muss installiert werden. Ergebnis: reines HTML/CSS.
"""
import html, json, os, re, shutil, sys
from datetime import date
from urllib.parse import quote, quote_plus

HIER = os.path.dirname(os.path.abspath(__file__))
TAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
KURZ = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
TAGE_SCHEMA = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
THEMEN = {"nacht": {"bg": "#0d0f13", "flaeche": "#1d222b"}, "hell": {"bg": "#faf8f5", "flaeche": "#f2eee8"}, "edel": {"bg": "#f5f0e8", "flaeche": "#ece4d8"}}
WARNUNGEN = []

def warnung(text):
    WARNUNGEN.append(text)

# ---------- Text und Sicherheit ----------
def e(s):
    return html.escape(str(s or ""), quote=True)

def rich(s):
    """Erlaubt nur <em>...</em> in Überschriften, alles andere wird maskiert."""
    return e(s).replace("&lt;em&gt;", "<em>").replace("&lt;/em&gt;", "</em>")

def obj(x):
    return x if isinstance(x, dict) else {}

def liste(x):
    return x if isinstance(x, list) else ([x] if x else [])

def sichere_url(u):
    u = (u or "").strip()
    return u if re.match(r"^https?://[^\s\"'<>]+$", u, re.I) else ""

def farbe(x, standard):
    x = (x or "").strip()
    if re.fullmatch(r"#[0-9a-fA-F]{3}", x):
        x = "#" + "".join(c * 2 for c in x[1:])
    if re.fullmatch(r"#[0-9a-fA-F]{6}", x):
        return x.lower()
    if x:
        warnung(f"Farbe {x!r} ist kein Hex-Wert, nehme {standard}")
    return standard

def nummer_int(nr):
    d = re.sub(r"\(0\)", "", nr or "")
    d = re.sub(r"[^\d+]", "", d)
    if d.startswith("00"):
        d = "+" + d[2:]
    elif d.startswith("0"):
        d = "+49" + d[1:]
    return d

def ist_mobil(nr):
    return bool(re.match(r"^\+491[5-7]", nummer_int(nr)))

def wa_link(nr, text=""):
    return "https://wa.me/" + nummer_int(nr).lstrip("+") + ("?text=" + quote(text) if text else "")

def domain_ok(d):
    d = (d or "").strip().lower()
    d = re.sub(r"^https?://", "", d).split("/")[0]
    return d if re.fullmatch(r"[a-z0-9.-]+\.[a-z]{2,}", d) else ""

def insta_name(ig):
    n = re.sub(r"^(https?://)?(www\.)?instagram\.com/", "", (ig or "").strip()).strip("/@ ")
    return n if re.fullmatch(r"[A-Za-z0-9._]{1,30}", n) else ""

def kuerzen(t, n=155):
    t = re.sub(r"\s+", " ", t or "").strip()
    return t if len(t) <= n else t[:n].rsplit(" ", 1)[0].rstrip(",.;:") + " …"

# ---------- Farben ----------
def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))

def luminanz(h):
    def kanal(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (kanal(c) for c in hex_rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def kontrast(a, b):
    la, lb = sorted((luminanz(a), luminanz(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)

def schrift_auf(f):
    """Weiß oder fast Schwarz, je nachdem was auf der Farbe besser lesbar ist."""
    return "#ffffff" if kontrast(f, "#ffffff") >= kontrast(f, "#111318") else "#111318"

def lesbar(f, hinter, ziel=4.5):
    """Dunkelt bzw. hellt eine Farbe ab, bis sie als Text auf dem Hintergrund lesbar ist."""
    r, g, b = (int(f[i:i + 2], 16) for i in (1, 3, 5))
    hell = luminanz(hinter) > 0.18
    x = f
    for _ in range(80):
        x = "#%02x%02x%02x" % (r, g, b)
        if kontrast(x, hinter) >= ziel:
            return x
        r, g, b = [int(c * .93) if hell else min(255, round(c + (255 - c) * .1)) for c in (r, g, b)]
    return x

# ---------- Symbole (eigene, schlichte Linien-Icons) ----------
ICONS = {
    "whatsapp": '<path d="M20.5 11.7a8.5 8.5 0 0 1-12.6 7.4L3.5 20.5l1.4-4.2a8.5 8.5 0 1 1 15.6-4.6Z"/><path d="M9 8.6c.2-.5.5-.5.8-.5h.5c.2 0 .4 0 .6.5l.7 1.7c.1.2 0 .4-.1.6l-.5.6c-.1.2-.1.3 0 .5.6 1 1.4 1.8 2.5 2.4.2.1.4.1.5 0l.6-.7c.2-.2.4-.2.6-.1l1.6.8c.2.1.3.2.3.4 0 .6-.3 1.3-.9 1.6-.7.4-1.6.4-2.6 0a9.8 9.8 0 0 1-4.6-4.5c-.5-1-.5-2 0-2.8Z" fill="currentColor" stroke="none"/>',
    "telefon": '<path d="M5 4h3.5l1.6 4-2.1 1.4a11 11 0 0 0 6.6 6.6l1.4-2.1 4 1.6V19a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2Z"/>',
    "mail": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3.5 6.5 8.5 6.5 8.5-6.5"/>',
    "ort": '<path d="M12 21s-7-6.1-7-11.5a7 7 0 0 1 14 0C19 14.9 12 21 12 21Z"/><circle cx="12" cy="9.5" r="2.5"/>',
    "uhr": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "menu": '<path d="M4 7h16M4 12h16M4 17h16"/>',
    "schliessen": '<path d="M6 6l12 12M18 6 6 18"/>',
    "pfeil": '<path d="M5 12h14M13 6l6 6-6 6"/>',
    "zeit": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "herz": '<path d="M12 20s-7.5-4.6-7.5-10A4.3 4.3 0 0 1 12 7.4 4.3 4.3 0 0 1 19.5 10c0 5.4-7.5 10-7.5 10Z"/>',
    "haken": '<circle cx="12" cy="12" r="9"/><path d="m8 12.5 2.7 2.7L16 9.8"/>',
    "schere": '<circle cx="6.5" cy="17.5" r="3"/><circle cx="17.5" cy="17.5" r="3"/><path d="M8.6 15.3 18 4M15.4 15.3 6 4"/>',
    "kalender": '<rect x="3.5" y="5" width="17" height="15" rx="2"/><path d="M3.5 10h17M8 3v4M16 3v4"/>',
    "kaffee": '<path d="M4 9h12v5a5 5 0 0 1-5 5H9a5 5 0 0 1-5-5V9Z"/><path d="M16 10h1.5a2.5 2.5 0 0 1 0 5H16M8 3v3M12 3v3"/>',
    "werkzeug": '<path d="M14.5 6.5a4 4 0 0 0 5 5l-8.5 8.5a2.1 2.1 0 0 1-3-3l8.5-8.5a4 4 0 0 0-2-2Z"/>',
    "pinsel": '<path d="M4 20c3 0 5-1.5 5-4a2.5 2.5 0 0 0-5 0c0 1.6-1 2.5-1 4Z"/><path d="m9.5 14.5 9.8-9.8a1.8 1.8 0 0 0-2.5-2.5L7 12"/>',
    "funke": '<path d="M12 3v4M12 17v4M3 12h4M17 12h4M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M18.4 5.6l-2.8 2.8M8.4 15.6l-2.8 2.8"/>',
    "familie": '<circle cx="8" cy="7" r="3"/><circle cx="17" cy="9" r="2.3"/><path d="M3 20c0-3.3 2.2-6 5-6s5 2.7 5 6M13.5 20c.2-2.6 1.6-4.6 3.5-4.6s3.3 2 3.5 4.6"/>',
    "google": '<path d="M20 12.2c0-.6 0-1.1-.1-1.6H12v3.1h4.5a3.9 3.9 0 0 1-1.7 2.5v2h2.7c1.6-1.5 2.5-3.6 2.5-6Z"/><path d="M12 20.5c2.3 0 4.2-.8 5.5-2.1l-2.7-2a5 5 0 0 1-7.5-2.7H4.6v2.1A8.5 8.5 0 0 0 12 20.5Z"/><path d="M7.3 13.7a5 5 0 0 1 0-3.4V8.2H4.6a8.5 8.5 0 0 0 0 7.6l2.7-2.1Z"/><path d="M12 6.9c1.3 0 2.4.4 3.3 1.3l2.4-2.4A8.5 8.5 0 0 0 4.6 8.2l2.7 2.1A5 5 0 0 1 12 6.9Z"/>',
}

def icon(name):
    p = ICONS.get(name, '<circle cx="12" cy="12" r="9"/>')
    return f'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">{p}</svg>'

# ---------- Branchen-Wortschatz (überschreibbar über inhalt.woerter) ----------
BRANCHEN = {
    "barber": {"icon": "schere", "nav": "Leistungen", "seite": "Leistungen & Preise", "h2_du": "Das machen wir für dich.", "h2_sie": "Das machen wir für Sie.",
               "besuch_eyebrow": None, "besuch_h2": "Öffnungszeiten & Anfahrt", "galerie_lead": "Frische Schnitte und Eindrücke aus dem Laden.", "liste": False},
    "beauty": {"icon": "funke", "nav": "Leistungen", "seite": "Leistungen & Preise", "h2_du": "Das machen wir für dich.", "h2_sie": "Das machen wir für Sie.",
               "besuch_eyebrow": None, "besuch_h2": "Öffnungszeiten & Anfahrt", "galerie_lead": "Ergebnisse und Eindrücke aus dem Studio.", "liste": False},
    "cafe": {"icon": "kaffee", "nav": "Karte", "seite": "Unsere Karte", "h2_du": "Frisch aus Küche und Röstung.", "h2_sie": "Frisch aus Küche und Röstung.",
             "besuch_eyebrow": None, "besuch_h2": "Öffnungszeiten & Anfahrt", "galerie_lead": "Eindrücke aus dem Café.", "liste": True},
    "handwerk": {"icon": "pinsel", "nav": "Leistungen", "seite": "Leistungen", "h2_du": "Das machen wir für dich.", "h2_sie": "Das machen wir für Sie.",
                 "besuch_eyebrow": "Erreichbarkeit", "besuch_h2": "Bürozeiten & Kontakt", "galerie_lead": "Ausgewählte Projekte aus Köln und Umgebung.", "liste": False},
    "andere": {"icon": "haken", "nav": "Leistungen", "seite": "Leistungen & Preise", "h2_du": "Das machen wir für dich.", "h2_sie": "Das machen wir für Sie.",
               "besuch_eyebrow": None, "besuch_h2": "Öffnungszeiten & Anfahrt", "galerie_lead": "Eindrücke aus unserem Betrieb.", "liste": False},
}
SCHEMA_TYP = {"Barbershop / Friseur": "HairSalon", "Kosmetik / Nagelstudio": "BeautySalon", "Café / Restaurant": "CafeOrCoffeeShop",
              "Handwerk": "HomeAndConstructionBusiness", "Einzelhandel": "Store"}

# ---------- Platzhalter-Grafik, solange keine Fotos da sind ----------
class Zaehler:
    n = 0

def kunst(variante, motiv="linien"):
    """Abstrakte SVG-Grafik in Markenfarben, ohne Buchstaben. Wird durch echte Fotos ersetzt."""
    Zaehler.n += 1
    gid = f"k{Zaehler.n}"
    v = variante % 4
    if motiv == "barber":
        breite = (22, 14, 30, 18)[v]
        winkel = (35, -35, 55, 25)[v]
        muster = "".join(f'<rect x="{x}" y="-400" width="{breite}" height="1800" style="fill:var(--brand-ink)" opacity="{0.11 if n % 2 else 0.05}" transform="rotate({winkel} 400 500)"/>' for n, x in enumerate(range(-900, 1700, breite * 2)))
    elif motiv == "cafe":
        cx, cy = ((560, 380), (240, 700), (620, 820), (200, 260))[v]
        muster = "".join(f'<ellipse cx="{cx}" cy="{cy}" rx="{r}" ry="{int(r * .82)}" fill="none" style="stroke:var(--brand-ink)" stroke-opacity="{0.16 if n % 3 == 0 else 0.07}" stroke-width="{2 if n % 3 == 0 else 1.2}" transform="rotate({n * 4} {cx} {cy})"/>' for n, r in enumerate(range(40, 900, 34)))
    elif motiv == "handwerk":
        deck = (0.16, 0.09, 0.22, 0.05, 0.13, 0.19)
        b = 800 // 6
        muster = "".join(f'<rect x="{i * b + (v * 37) % b - b}" y="{(i * 113 + v * 71) % 260 - 120}" width="{b - 10}" height="1300" rx="18" style="fill:var(--brand-ink)" opacity="{deck[(i + v) % 6]}"/>' for i in range(8))
    else:
        cx, cy = (620 if v % 2 else 180), (760 if v < 2 else 240)
        muster = "".join(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" style="stroke:var(--brand-ink)" stroke-opacity="0.13" stroke-width="2"/>' for r in range(80, 900, 70))
    return (f'<svg class="art" viewBox="0 0 800 1000" preserveAspectRatio="xMidYMid slice" aria-hidden="true" focusable="false">'
            f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" style="stop-color:var(--brand)"/>'
            f'<stop offset="1" style="stop-color:color-mix(in srgb, var(--brand) 62%, #000)"/></linearGradient>'
            f'<filter id="{gid}r"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" stitchTiles="stitch"/><feColorMatrix values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 .5 0"/></filter></defs>'
            f'<rect width="800" height="1000" style="fill:var(--brand)"/><rect width="800" height="1000" fill="url(#{gid})"/>{muster}'
            f'<rect width="800" height="1000" filter="url(#{gid}r)" opacity=".07"/></svg>')

def stadtplan():
    """Ruhiges Straßenraster für die Anfahrt-Karte."""
    linien = "".join(f'<path d="M{x} -20 L{x + 60} 420"/>' for x in range(-40, 900, 110)) + "".join(f'<path d="M-20 {y} L880 {y - 40}"/>' for y in range(30, 460, 90))
    return (f'<svg class="stadtplan" viewBox="0 0 860 400" preserveAspectRatio="xMidYMid slice" aria-hidden="true" focusable="false">'
            f'<g fill="none" stroke="currentColor" stroke-width="10" stroke-linecap="round">{linien}</g>'
            f'<path d="M-20 300 C 200 240, 420 380, 880 250" fill="none" stroke="currentColor" stroke-width="34" opacity=".7"/></svg>')

# ---------- Fotos ----------
BREITEN = (480, 800, 1200)

def bild(f, sizes, wichtig=False, verh=(4, 5)):
    """Echtes Foto als <picture> mit WebP/JPG in drei Breiten. Dateien liegen in fotos/<name>-<breite>.<endung>."""
    f = obj(f)
    if not f.get("datei"):
        return ""
    if not f.get("alt"):
        warnung(f"Foto {f['datei']!r} hat keinen Alt-Text")
    n = e(f["datei"])
    w, h = 1200, round(1200 * verh[1] / verh[0])
    src = lambda ext: ", ".join(f"fotos/{n}-{b}.{ext} {b}w" for b in BREITEN)
    laden = 'fetchpriority="high"' if wichtig else 'loading="lazy"'
    return (f'<picture><source type="image/webp" srcset="{src("webp")}" sizes="{sizes}">'
            f'<img src="fotos/{n}-800.jpg" srcset="{src("jpg")}" sizes="{sizes}" width="{w}" height="{h}" '
            f'alt="{e(f.get("alt", ""))}" {laden} decoding="async"></picture>')

# ---------- Daten laden ----------
def lies_datei(pfad):
    with open(pfad, encoding="utf-8") as fh:
        roh = fh.read()
    if not pfad.endswith(".json"):
        m = re.search(r"DATEN FÜR DIE WEBSITE\s*—?\s*(\{.*\})\s*$", roh, re.S)
        if not m:
            sys.exit("In der Textdatei wurde kein Datenblock gefunden.")
        roh = m.group(1)
    d = json.loads(roh)
    if "betrieb" in d and "fragebogen" not in d:
        d = {"fragebogen": d}
    return d

def zeiten_lesen(fb):
    """Liest die Öffnungszeiten tolerant: '10:00–19:00', '9-18 Uhr', '09:00–13:00, 14:00–18:00'."""
    zeiten = [None] * 7
    for pos, z in enumerate(liste(fb.get("zeiten"))[:7]):
        z = obj(z)
        tag = z.get("tag")
        i = TAGE.index(tag) if tag in TAGE else pos
        t = str(z.get("zeit") or "").strip()
        bereiche = re.findall(r"(\d{1,2})(?::(\d{2}))?\s*(?:Uhr)?\s*[–-]\s*(\d{1,2})(?::(\d{2}))?", t)
        if bereiche:
            von = f"{int(bereiche[0][0]):02d}:{bereiche[0][1] or '00'}"
            bis = f"{int(bereiche[-1][2]):02d}:{bereiche[-1][3] or '00'}"
            zeiten[i] = [von, bis]
            if len(bereiche) > 1:
                warnung(f"{TAGE[i]}: Pause erkannt ({t}). Gezeigt wird {von}–{bis}, die Pause bitte in den Hinweis schreiben.")
        elif t.lower() not in ("", "geschlossen"):
            warnung(f"Öffnungszeit {TAGE[i]} nicht erkannt: {t!r}, wird als geschlossen gezeigt")
    return zeiten

def initialen_aus(name):
    fuell = {"und", "der", "die", "das", "am", "im", "in", "zum", "zur", "von"}
    w = [x for x in re.findall(r"[A-Za-zÄÖÜäöü]+", name) if x.lower() not in fuell]
    return "".join(x[0] for x in w[:2]).upper() or "W"

def lade(pfad):
    d = lies_datei(pfad)
    fb = obj(d.get("fragebogen"))
    b = obj(fb.get("betrieb"))
    inh = obj(d.get("inhalt"))
    des = obj(d.get("design"))
    seite = obj(d.get("seite"))
    stil = obj(fb.get("stil"))
    funk = obj(fb.get("funktionen"))
    texte = obj(fb.get("texte"))

    name = str(b.get("name") or "").strip() or "[Name des Betriebs]"
    branche_opt = b.get("branche") or ""
    bl = branche_opt.lower()
    art = ("barber" if ("barber" in bl or "friseur" in bl) else "cafe" if ("café" in bl or "cafe" in bl or "restaurant" in bl)
           else "beauty" if ("kosmetik" in bl or "nagel" in bl) else "handwerk" if "handwerk" in bl else "andere")
    motiv = {"barber": "barber", "cafe": "cafe", "handwerk": "handwerk"}.get(art, "linien")
    woerter = dict(BRANCHEN[art])
    woerter.update(obj(inh.get("woerter")))

    stimmung = " ".join(liste(stil.get("stimmung"))).lower()
    thema = des.get("thema") or ("nacht" if ("dunkel" in stimmung or "frech" in stimmung) else "edel" if ("edel" in stimmung or "klassisch" in stimmung) else "hell")
    if thema not in THEMEN:
        warnung(f"Unbekanntes Thema {thema!r}, nehme 'hell'")
        thema = "hell"
    vorgabe = {"nacht": ("#d4202a", "#f2c14e"), "hell": ("#c81e28", "#1f6feb"), "edel": ("#7a4a2a", "#b08d57")}[thema]
    fbf = liste(stil.get("farben"))
    df = obj(des.get("farben"))
    if stil.get("farbenVorhanden") == "Ja" and fbf:
        brand = farbe(df.get("brand") or fbf[0], vorgabe[0])
        accent = farbe(df.get("accent") or (fbf[-1] if len(fbf) > 1 else ""), vorgabe[1])
    else:
        brand = farbe(df.get("brand"), vorgabe[0])
        accent = farbe(df.get("accent"), vorgabe[1])
    flaeche = THEMEN[thema]["flaeche"]

    leistungen = [l for l in liste(fb.get("leistungen")) if isinstance(l, dict) and str(l.get("leistung") or "").strip()]
    zeige_preise = (fb.get("preiseZeigen") or "Ja, alle") != "Nein"
    if not zeige_preise:
        woerter["seite"] = woerter["seite"].replace(" & Preise", "")
    anrede = str(inh.get("anrede") or ("sie" if art == "handwerk" or "einzelhandel" in bl else "du")).lower()

    plz_ort = " ".join(x for x in [b.get("plz"), b.get("ort")] if x)
    adresse = ", ".join(x for x in [b.get("strasse"), plz_ort] if x)
    wa = b.get("whatsapp") or (b.get("telefon") if ist_mobil(b.get("telefon")) else "")
    inhalte = liste(funk.get("inhalte"))
    fotos = obj(d.get("fotos"))
    social = sichere_url(b.get("facebook"))

    faq = []
    for f in liste(inh.get("faq")):
        if isinstance(f, dict):
            faq.append((f.get("frage"), f.get("antwort")))
        elif isinstance(f, (list, tuple)) and len(f) >= 2:
            faq.append((f[0], f[1]))
    if inhalte and "Häufige Fragen" not in inhalte:
        faq = []

    ueber = liste(inh.get("ueber_text")) or [p for p in [texte.get("beschreibung"), texte.get("geschichte")] if p]
    beschreibung = inh.get("seo_beschreibung") or kuerzen(texte.get("beschreibung") or
                   f"{name}: {branche_opt.split(' / ')[0]} in {b.get('ort') or 'Köln'}. " + ", ".join(l["leistung"] for l in leistungen[:4]))

    k = {
        "art": art, "woerter": woerter, "anrede": anrede, "roh": d, "name": name, "initialen": initialen_aus(name), "motiv": motiv,
        "schema_typ": des.get("schema_typ") or SCHEMA_TYP.get(branche_opt, "LocalBusiness"),
        "thema": thema, "brand": brand, "accent": accent, "brand_ink": schrift_auf(brand),
        "brand_text": lesbar(brand, flaeche, 3.0 if thema == "nacht" else 4.5),
        "accent_text": lesbar(accent, flaeche),
        "branche": branche_opt, "ort": b.get("ort") or "", "adresse": adresse, "b": b,
        "maps": ("https://www.google.com/maps/search/?api=1&query=" + quote_plus(name + ", " + adresse)) if adresse else "",
        "telefon": b.get("telefon"), "whatsapp": wa, "email": str(b.get("email") or "").strip(),
        "instagram": insta_name(b.get("instagram")), "google": sichere_url(b.get("google")), "social": social,
        "zeiten": zeiten_lesen(fb), "zeiten_hinweis": fb.get("zeitenHinweis"),
        "leistungen": leistungen, "zeige_preise": zeige_preise, "ab_preise": fb.get("preiseZeigen") == "Nur ab-Preise",
        "zahlung": liste(fb.get("zahlung")), "team": [t for t in liste(fb.get("team")) if isinstance(t, dict) and t.get("name")],
        "sprachen": fb.get("sprachen"), "seit": b.get("seit"),
        "termin": liste(funk.get("termin")), "buchungstool": funk.get("buchungstool"), "buchungslink": sichere_url(funk.get("buchungslink")),
        "galerie": ("Fotogalerie" in inhalte or "Vorher/Nachher" in inhalte), "fotos": fotos,
        "impressum": obj(fb.get("impressum")),
        "slogan": inh.get("slogan") or (branche_opt.split(" / ")[0] + (" in " + b.get("ort") if b.get("ort") else "")),
        "hero_titel": inh.get("hero_titel") or name,
        "hero_text": inh.get("hero_text") or texte.get("beschreibung") or "",
        "fakten": [f for f in liste(inh.get("fakten")) if isinstance(f, (list, tuple)) and len(f) >= 2],
        "leistung_texte": obj(inh.get("leistungen_texte")),
        "leistungen_intro": inh.get("leistungen_intro") or "",
        "vorteile": [v for v in liste(inh.get("vorteile")) if isinstance(v, dict)],
        "ueber_titel": inh.get("ueber_titel") or "Über uns",
        "ueber_text": [str(p) for p in ueber],
        "zitat": inh.get("zitat") or "",
        "faq": faq,
        "cta_titel": inh.get("cta_titel") or ("Lust auf einen Termin?" if anrede == "du" else "Wir freuen uns auf Ihre Anfrage."),
        "cta_text": inh.get("cta_text") or ("Schreib uns kurz, wir melden uns schnell." if anrede == "du" else "Schreiben Sie uns kurz, wir melden uns schnell."),
        "seo_titel": inh.get("seo_titel") or " · ".join(x for x in [name, branche_opt.split(" / ")[0], b.get("ort")] if x),
        "seo_text": beschreibung,
        "domain": domain_ok(seite.get("domain") or funk.get("domain")),
        "hoster": seite.get("hoster") or "",
        "erstellt_von": seite.get("erstellt_von") or "[Dein Name]",
        "erstellt_link": sichere_url(seite.get("erstellt_link")),
        "demo": bool(seite.get("demo")),
    }
    for a, *_ in k["fakten"]:
        if len(str(a)) > 10:
            warnung(f"Fakt {a!r} ist lang. Besser: kurzer Wert (Zahl oder Wort) und der Rest ins Label.")
    return k

def T(k, du, sie):
    """Text in der passenden Anrede (du oder Sie)."""
    return du if k["anrede"] == "du" else sie

# ---------- Seitenbausteine ----------
def seiten_liste(k):
    s = [("index.html", "Start"), ("leistungen.html", k["woerter"]["nav"]), ("ueber-uns.html", "Über uns")]
    if k["galerie"]:
        s.append(("galerie.html", "Galerie"))
    s.append(("kontakt.html", "Kontakt"))
    return s

def termin_link(k):
    """Bester Weg zum Termin: Buchungstool, WhatsApp, Telefon oder Kontaktseite."""
    if k["buchungslink"] and "Online-Buchungstool" in k["termin"]:
        return k["buchungslink"], "Online buchen", "kalender"
    if k["whatsapp"] and ("Per WhatsApp" in k["termin"] or not k["termin"]):
        return wa_link(k["whatsapp"], f"Hallo {k['name']}, ich hätte gern einen Termin."), "Termin per WhatsApp", "whatsapp"
    if k["telefon"]:
        return "tel:" + nummer_int(k["telefon"]), "Jetzt anrufen", "telefon"
    return "kontakt.html", "Kontakt aufnehmen", "pfeil"

def extern(link):
    return ' target="_blank" rel="noopener"' if link.startswith("http") else ""

def kopf(k, aktiv, titel, beschreibung, pfad, fehlerseite=False):
    url = f"https://{k['domain']}/{'' if pfad == 'index.html' else pfad}" if k["domain"] and not k["demo"] and not fehlerseite else ""
    nav = "".join(f'<a href="{p}"{" aria-current=\"page\"" if p == aktiv else ""}>{e(n)}</a>' for p, n in seiten_liste(k))
    link, label, ic = termin_link(k)
    demo = '<div class="demo-leiste">Demo-Website · fiktiver Betrieb · Beispiel aus dem Website-Baukasten</div>' if k["demo"] else ""
    disp = {"nacht": "anton-latin-400-normal", "edel": "playfair-display-latin-700-normal", "hell": "manrope-latin-800-normal"}[k["thema"]]
    og_bild = k["fotos"].get("og") if k["domain"] else ""
    return f"""<!DOCTYPE html>
<html lang="de" data-theme="{k['thema']}" class="no-js">
<head>
<meta charset="utf-8">
<script>document.documentElement.classList.remove('no-js')</script>
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(titel)}</title>
<meta name="description" content="{e(beschreibung)}">
{f'<link rel="canonical" href="{e(url)}">' if url else ''}
{'<meta name="robots" content="noindex">' if k['demo'] or fehlerseite else ''}
<meta property="og:type" content="website">
<meta property="og:site_name" content="{e(k['name'])}">
<meta property="og:title" content="{e(titel)}">
<meta property="og:description" content="{e(beschreibung)}">
<meta property="og:locale" content="de_DE">
{f'<meta property="og:url" content="{e(url)}">' if url else ''}
{f'<meta property="og:image" content="https://{e(k["domain"])}/{e(og_bild)}"><meta name="twitter:card" content="summary_large_image">' if og_bild else ''}
<meta name="theme-color" content="{THEMEN[k['thema']]['bg']}">
<link rel="icon" href="assets/favicon.svg" type="image/svg+xml">
<link rel="preload" href="assets/fonts/{disp}.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="assets/fonts/manrope-latin-400-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="assets/style.css">
<style>:root{{--brand:{k['brand']};--brand-ink:{k['brand_ink']};--accent:{k['accent']};--brand-text:{k['brand_text']};--accent-text:{k['accent_text']};}}</style>
</head>
<body>
<a class="skip" href="#inhalt">Zum Inhalt springen</a>
{demo}
<header class="site-header">
  <div class="wrap header-inner">
    <a class="logo" href="index.html">
      <span class="logo-mark" aria-hidden="true">{e(k['initialen'])}</span>
      <span class="logo-text"><b>{e(k['name'])}</b><span>{e(k['slogan'])}</span></span>
    </a>
    <button class="menu-toggle" type="button" aria-expanded="false" aria-controls="nav" aria-label="Menü"><span class="ico-auf">{icon('menu')}</span><span class="ico-zu">{icon('schliessen')}</span></button>
    <nav class="nav" id="nav" aria-label="Hauptmenü">{nav}<a class="btn" href="{e(link)}"{extern(link)}>{icon(ic)}{e(label)}</a></nav>
  </div>
</header>
<main id="inhalt">
"""

def zeiten_kompakt(k):
    gruppen = []
    for i, z in enumerate(k["zeiten"]):
        w = f"{z[0]}–{z[1]}" if z else "geschlossen"
        if gruppen and gruppen[-1][2] == w:
            gruppen[-1][1] = i
        else:
            gruppen.append([i, i, w])
    out = []
    for a, b, w in gruppen:
        if w == "geschlossen":
            continue
        tage = KURZ[a] if a == b else f"{KURZ[a]}–{KURZ[b]}"
        out.append(f'<li><span class="nowrap">{tage}</span> {w} Uhr</li>')
    return "".join(out) or "<li>nach Vereinbarung</li>"

def fuss(k):
    link, label, ic = termin_link(k)
    kontakt = []
    if k["telefon"]:
        kontakt.append(f'<li><a class="nowrap" href="tel:{e(nummer_int(k["telefon"]))}">{e(k["telefon"])}</a></li>')
    if k["email"]:
        kontakt.append(f'<li><a href="mailto:{e(k["email"])}">{e(k["email"])}</a></li>')
    if k["instagram"]:
        kontakt.append(f'<li><a href="https://www.instagram.com/{e(k["instagram"])}/" target="_blank" rel="noopener">Instagram</a></li>')
    if k["social"]:
        kontakt.append(f'<li><a href="{e(k["social"])}" target="_blank" rel="noopener">Social Media</a></li>')
    if k["google"]:
        kontakt.append(f'<li><a href="{e(k["google"])}" target="_blank" rel="noopener">Google-Profil</a></li>')
    seiten = "".join(f'<li><a href="{p}">{e(n)}</a></li>' for p, n in seiten_liste(k))
    credit = f'<a href="{e(k["erstellt_link"])}">{e(k["erstellt_von"])}</a>' if k["erstellt_link"] else e(k["erstellt_von"])
    zeiten_titel = "Bürozeiten" if k["art"] == "handwerk" else "Öffnungszeiten"
    return f"""</main>
<footer class="site-footer">
  <div class="wrap">
    <div class="footer-grid">
      <div>
        <a class="logo" href="index.html"><span class="logo-mark" aria-hidden="true">{e(k['initialen'])}</span><span class="logo-text"><b>{e(k['name'])}</b><span>{e(k['slogan'])}</span></span></a>
        <p class="muted" style="margin-top:16px;max-width:34ch">{e(k['adresse'])}</p>
      </div>
      <nav aria-label="Fußzeile"><h2 class="footer-title">Seiten</h2><ul>{seiten}</ul></nav>
      <div><h2 class="footer-title">{zeiten_titel}</h2><ul>{zeiten_kompakt(k)}</ul></div>
      <div><h2 class="footer-title">Kontakt</h2><ul>{''.join(kontakt)}</ul></div>
    </div>
    <div class="footer-bottom">
      <span>© {date.today().year} {e(k['name'])} · <a href="impressum.html">Impressum</a> · <a href="datenschutz.html">Datenschutz</a></span>
      <span>Website: {credit}</span>
    </div>
  </div>
</footer>
<a class="float-cta float-{ic}" href="{e(link)}"{extern(link)}>{icon(ic)}<span>{e(label.replace('Termin per WhatsApp', 'WhatsApp'))}</span></a>
<script type="application/json" id="oeffnungszeiten">{json.dumps(k['zeiten'])}</script>
<script src="assets/app.js" defer></script>
</body>
</html>
"""

def preis(l, k):
    if not k["zeige_preise"] or not l.get("preis"):
        return ""
    p = str(l["preis"]).strip()
    if re.match(r"^[\d.,\s–-]+$", p):
        p += " €"
    return ("ab " if k["ab_preise"] and not p.lower().startswith("ab") else "") + p

def menu_liste(k, ls):
    zeilen = []
    for l in ls:
        pr = preis(l, k)
        txt = k["leistung_texte"].get(l["leistung"], "")
        klein = f"<small>{e(txt)}</small>" if txt else ""
        zeilen.append(f'<div class="menu-row"><b>{e(l["leistung"])}</b><span class="dots" aria-hidden="true"></span><span class="val">{e(pr)}</span>{klein}</div>')
    return f'<div class="menu-list">{"".join(zeilen)}</div>'

def leistung_karten(k, anzahl=None):
    ls = k["leistungen"][:anzahl] if anzahl else k["leistungen"]
    if k["woerter"]["liste"]:
        return menu_liste(k, ls)
    out = []
    for l in ls:
        txt = k["leistung_texte"].get(l["leistung"], "")
        pr, dauer = preis(l, k), l.get("dauer") or ""
        preis_html = f'<span class="price">{e(pr)}</span>' if pr else ""
        meta = f'<div class="meta"><span>{e(dauer)}</span>{preis_html}</div>' if (pr or dauer) else ""
        out.append(f"""<article class="service">
  <span class="ico">{icon(k['woerter']['icon'])}</span>
  <h3>{e(l['leistung'])}</h3>
  {f'<p>{e(txt)}</p>' if txt else ''}
  {meta}
</article>""")
    return f'<div class="service-grid n{len(ls)}">' + "\n".join(out) + "</div>"

def stunden_tabelle(k, kopf_id):
    zeilen = []
    for i, z in enumerate(k["zeiten"]):
        wert = f"{z[0]} – {z[1]} Uhr" if z else "geschlossen"
        zeilen.append(f'<tr data-tag="{i}"><th scope="row">{TAGE[i]}</th><td>{wert}</td></tr>')
    return f'<table class="hours" aria-labelledby="{kopf_id}">{"".join(zeilen)}</table>'

def kontakt_liste(k):
    li = []
    if k["adresse"]:
        li.append(f'<li><span class="ico">{icon("ort")}</span><span><a href="{e(k["maps"])}" target="_blank" rel="noopener">{e(k["adresse"])}</a><small>Route in Google Maps öffnen</small></span></li>')
    if k["telefon"]:
        li.append(f'<li><span class="ico">{icon("telefon")}</span><span><a class="nowrap" href="tel:{e(nummer_int(k["telefon"]))}">{e(k["telefon"])}</a><small>Anrufen</small></span></li>')
    if k["whatsapp"]:
        li.append(f'<li><span class="ico">{icon("whatsapp")}</span><span><a href="{e(wa_link(k["whatsapp"]))}" target="_blank" rel="noopener">WhatsApp schreiben</a><small>Nachricht statt Anruf</small></span></li>')
    if k["email"]:
        li.append(f'<li><span class="ico">{icon("mail")}</span><span><a href="mailto:{e(k["email"])}">{e(k["email"])}</a><small>E-Mail</small></span></li>')
    return f'<ul class="contact-list">{"".join(li)}</ul>'

def cta_band(k):
    link, label, ic = termin_link(k)
    return f"""<section class="cta-section"><div class="wrap"><div class="cta-band">
  {kunst(3, k['motiv'])}
  <div><h2>{rich(k['cta_titel'])}</h2><p>{e(k['cta_text'])}</p></div>
  <a class="btn" href="{e(link)}"{extern(link)}>{icon(ic)}{e(label)}</a>
</div></div></section>"""

def zahlen(p):
    out = []
    for z in re.findall(r"\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:[.,]\d+)?", p or ""):
        if re.search(r"\.\d{3}(?!\d)", z):
            z = z.replace(".", "")
        out.append(float(z.replace(",", ".")))
    return out

def schema(k):
    d = {"@context": "https://schema.org", "@type": k["schema_typ"], "name": k["name"]}
    b = k["b"]
    if k["domain"] and not k["demo"]:
        d["@id"] = "https://" + k["domain"] + "/#betrieb"
        d["url"] = "https://" + k["domain"] + "/"
    if k["adresse"]:
        ort = b.get("ort") or ""
        d["address"] = {"@type": "PostalAddress", "streetAddress": b.get("strasse"), "postalCode": b.get("plz"),
                        "addressLocality": "Köln" if ort.startswith("Köln") else ort, "addressCountry": "DE"}
        d["hasMap"] = k["maps"]
    if k["telefon"]:
        d["telephone"] = nummer_int(k["telefon"])
    if k["email"]:
        d["email"] = k["email"]
    if k["seo_text"]:
        d["description"] = k["seo_text"]
    gruppen = {}
    for i, z in enumerate(k["zeiten"]):
        if z:
            gruppen.setdefault(tuple(z), []).append(TAGE_SCHEMA[i])
    spec = [{"@type": "OpeningHoursSpecification", "dayOfWeek": tage, "opens": z[0], "closes": z[1]} for z, tage in gruppen.items()]
    if spec:
        d["openingHoursSpecification"] = spec
    if k["zeige_preise"]:
        preise = [x for l in k["leistungen"] for x in zahlen(l.get("preis"))]
        if preise:
            d["priceRange"] = f"{min(preise):g}–{max(preise):g} €".replace(".", ",")
    if k["zahlung"]:
        d["paymentAccepted"] = ", ".join(k["zahlung"])
    same = [x for x in [k["google"], ("https://www.instagram.com/" + k["instagram"] + "/") if k["instagram"] else None, k["social"]] if x]
    if same:
        d["sameAs"] = same
    hero = obj(k["fotos"].get("hero"))
    if hero.get("datei") and k["domain"]:
        d["image"] = [f"https://{k['domain']}/fotos/{hero['datei']}-1200.jpg"]
    d = {a: v for a, v in d.items() if v}
    if "address" in d:
        d["address"] = {a: v for a, v in d["address"].items() if v}
    return '<script type="application/ld+json">' + json.dumps(d, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e") + "</script>"

def visual(k, schluessel, variante, sizes, verh, wichtig=False):
    return bild(k["fotos"].get(schluessel), sizes, wichtig, verh) or kunst(variante, k["motiv"])

H3_STIL = 'style="font-family:var(--body);font-size:20px;text-transform:none;letter-spacing:-.01em"'

# ---------- Seiten ----------
def seite_start(k):
    link, label, ic = termin_link(k)
    w = k["woerter"]
    fakten = "".join(f'<div class="fact"><b>{e(f[0])}</b><span>{e(f[1])}</span></div>' for f in k["fakten"][:4])
    vorteile = "".join(f'<article class="usp"><span class="ico">{icon(v.get("icon", "haken"))}</span><h3>{e(v.get("titel"))}</h3><p>{e(v.get("text"))}</p></article>' for v in k["vorteile"][:3])
    ueber = "".join(f"<p>{e(p)}</p>" for p in k["ueber_text"][:2])
    faq = "".join(f"<details><summary>{e(q)}</summary><p>{e(a)}</p></details>" for q, a in k["faq"][:5])
    google_cta = f"""<section><div class="wrap"><div class="reviews-cta">
  <div><h2 {H3_STIL}>Was unsere Kunden sagen</h2><p class="muted" style="margin:6px 0 0">{T(k, "Echte Bewertungen findest du direkt bei Google.", "Echte Bewertungen finden Sie direkt bei Google.")}</p></div>
  <a class="btn btn-ghost" href="{e(k['google'])}" target="_blank" rel="noopener">{icon('google')}Bewertungen bei Google</a>
</div></div></section>""" if k["google"] else ""
    hero_foto = bool(obj(k["fotos"].get("hero")).get("datei"))
    zeit_id = "zeiten-start"
    besuch_eyebrow = w["besuch_eyebrow"] or T(k, "Besuch uns", "Besuchen Sie uns")
    leistungs_titel = w["h2_du"] if k["anrede"] == "du" else w["h2_sie"]
    zeiten_wort = "Bürozeiten" if k["art"] == "handwerk" else "Öffnungszeiten"
    vorteile_html = f'<section class="section-alt"><div class="wrap"><div class="section-head"><div><p class="eyebrow">Warum wir</p><h2>{T(k, "Darum kommen Leute wieder.", "Darum vertrauen uns unsere Kunden.")}</h2></div></div><div class="usp-grid">{vorteile}</div></div></section>' if vorteile else ""
    faq_html = f'<section><div class="wrap faq-wrap"><div class="section-head"><div><p class="eyebrow">Fragen</p><h2>Kurz gefragt.</h2></div></div><div class="faq">{faq}</div></div></section>' if faq else ""
    intro = f'<p class="lead">{e(k["leistungen_intro"])}</p>' if k["leistungen_intro"] else ""
    hinweis = f'<p class="muted" style="margin:14px 0 0;font-size:15px">{e(k["zeiten_hinweis"])}</p>' if k["zeiten_hinweis"] else ""
    zitat = f'<blockquote class="quote">„{e(k["zitat"])}“</blockquote>' if k["zitat"] else ""
    return kopf(k, "index.html", k["seo_titel"], k["seo_text"], "index.html") + f"""
<section class="hero">
  <div class="wrap hero-grid">
    <div>
      <p class="eyebrow reveal">{e(k['slogan'])}</p>
      <h1 class="reveal reveal-2">{rich(k['hero_titel'])}</h1>
      <p class="lead reveal reveal-3">{e(k['hero_text'])}</p>
      <div class="hero-actions reveal reveal-4">
        <a class="btn btn-primary" href="{e(link)}"{extern(link)}>{icon(ic)}{e(label)}</a>
        <a class="btn btn-ghost" href="leistungen.html">{e(w['seite'])}</a>
      </div>
    </div>
    <div class="hero-visual{' foto' if hero_foto else ''} reveal reveal-3">
      {visual(k, 'hero', 0, '(max-width: 900px) 100vw, 520px', (4, 5), True)}
      <div class="hero-badge"><span class="ico">{icon('uhr')}</span><div><b class="live" data-status hidden><i aria-hidden="true"></i><span></span></b><span>{e(k['zeiten_hinweis'] or k['adresse'])}</span></div></div>
    </div>
  </div>
</section>
{f'<div class="facts"><div class="wrap facts-grid">{fakten}</div></div>' if fakten else ''}
<section>
  <div class="wrap">
    <div class="section-head"><div><p class="eyebrow">{e(w['nav'])}</p><h2>{e(leistungs_titel)}</h2></div>{intro}</div>
    {leistung_karten(k, 6)}
    <p style="margin-top:28px"><a class="btn btn-ghost" href="leistungen.html">{'Ganze Karte ansehen' if k['art'] == 'cafe' else 'Alle Leistungen ansehen'} {icon('pfeil')}</a></p>
  </div>
</section>
{vorteile_html}
<section>
  <div class="wrap split">
    <div class="visual">{visual(k, 'ueber', 1, '(max-width: 860px) 100vw, 540px', (1, 1))}</div>
    <div>
      <p class="eyebrow">Über uns</p>
      <h2 style="margin-bottom:20px">{rich(k["ueber_titel"])}</h2>
      {zitat}
      {ueber}
      <a class="btn btn-ghost" href="ueber-uns.html">Mehr über uns {icon('pfeil')}</a>
    </div>
  </div>
</section>
{google_cta}
<section class="section-alt">
  <div class="wrap">
    <div class="section-head"><div><p class="eyebrow">{e(besuch_eyebrow)}</p><h2>{e(w['besuch_h2'])}</h2></div></div>
    <div class="info-grid">
      <div class="card"><h3 id="{zeit_id}">{zeiten_wort}</h3>{stunden_tabelle(k, zeit_id)}{hinweis}</div>
      <div class="card"><h3>{T(k, "So erreichst du uns", "So erreichen Sie uns")}</h3>{kontakt_liste(k)}<a class="btn btn-primary" href="{e(link)}"{extern(link)}>{icon(ic)}{e(label)}</a></div>
    </div>
  </div>
</section>
{faq_html}
{cta_band(k)}
{schema(k)}
""" + fuss(k)

def seite_leistungen(k):
    w = k["woerter"]
    if w["liste"]:
        inhalt = menu_liste(k, k["leistungen"])
    else:
        zeilen = []
        for l in k["leistungen"]:
            txt = k["leistung_texte"].get(l["leistung"], "")
            pr = preis(l, k)
            chip = f'<span class="chip">{e(l["dauer"])}</span>' if l.get("dauer") else ""
            val = f'<span class="val">{e(pr)}</span>' if pr else ""
            zeilen.append(f'<div class="price-row"><b>{e(l["leistung"])}</b><span class="dur">{chip}{e(txt)}</span>{val}</div>')
        inhalt = f'<div class="price-list">{"".join(zeilen)}</div>'
    zahlung = ", ".join(k["zahlung"])
    lead = T(k, "Alles auf einen Blick. Du bist unsicher, was passt? Frag einfach kurz nach.", "Alles auf einen Blick. Sie sind unsicher, was passt? Fragen Sie einfach kurz nach.")
    beschr = kuerzen(f"{w['seite']} von {k['name']}{' in ' + k['ort'] if k['ort'] else ''}: " + ", ".join(l['leistung'] for l in k['leistungen'][:5]) + ".")
    return kopf(k, "leistungen.html", f"{w['seite']} · {k['name']}", beschr, "leistungen.html") + f"""
<div class="page-hero"><div class="wrap">
  <p class="breadcrumb"><a href="index.html">Start</a> <span aria-hidden="true">›</span> {e(w['nav'])}</p>
  <h1>{e(w['seite'])}</h1>
  <p class="lead">{lead}</p>
</div></div>
<section><div class="wrap">
  {inhalt}
  {f'<p class="price-note">Zahlung: {e(zahlung)}.</p>' if zahlung else ''}
</div></section>
{cta_band(k)}
""" + fuss(k)

def seite_ueber(k):
    texte = "".join(f"<p>{e(p)}</p>" for p in k["ueber_text"])
    fotos_team = obj(k["fotos"].get("team"))
    team = []
    for n, t in enumerate(k["team"]):
        foto = bild(fotos_team.get(t["name"]), "(max-width: 640px) 100vw, 300px")
        portrait = foto or (kunst(n + 1, k["motiv"]) + f'<b aria-hidden="true">{e(t["name"][:1])}</b>')
        team.append(f'<div class="member"><div class="portrait">{portrait}</div><b>{e(t["name"])}</b><span class="role">{e(t.get("rolle") or "")}</span></div>')
    fakten = []
    if k["seit"]:
        fakten.append((k["seit"], T(k, "gegründet, seitdem für euch da", "gegründet, seitdem für Sie da")))
    if k["sprachen"]:
        fakten.append(("Sprachen", k["sprachen"]))
    fakt_html = "".join(f'<div class="fact"><b>{e(a)}</b><span>{e(b)}</span></div>' for a, b in fakten)
    team_titel = "Die Leute hinter dem Tresen." if k["art"] == "cafe" else T(k, "Die Leute hinter dem Laden.", "Ihre Ansprechpartner.")
    team_html = f'<section class="section-alt"><div class="wrap"><div class="section-head"><div><p class="eyebrow">Team</p><h2>{team_titel}</h2></div></div><div class="team-grid">{"".join(team)}</div></div></section>' if team else ""
    zitat = f'<blockquote class="quote">„{e(k["zitat"])}“</blockquote>' if k["zitat"] else ""
    beschr = kuerzen(f"Wer hinter {k['name']} steckt: " + (k['ueber_text'][0] if k['ueber_text'] else ""))
    return kopf(k, "ueber-uns.html", f"Über uns · {k['name']}", beschr, "ueber-uns.html") + f"""
<div class="page-hero"><div class="wrap">
  <p class="breadcrumb"><a href="index.html">Start</a> <span aria-hidden="true">›</span> Über uns</p>
  <h1>{rich(k['ueber_titel'])}</h1>
</div></div>
<section><div class="wrap split">
  <div class="visual">{visual(k, 'ueber', 2, '(max-width: 860px) 100vw, 540px', (1, 1))}</div>
  <div class="prose">{zitat}{texte}
    {f'<div class="mini-facts">{fakt_html}</div>' if fakt_html else ''}
  </div>
</div></section>
{team_html}
{cta_band(k)}
""" + fuss(k)

def seite_galerie(k):
    fotos = [f for f in liste(k["fotos"].get("galerie")) if isinstance(f, dict) and f.get("datei")]
    if fotos:
        kacheln = "".join(f'<figure>{bild(f, "(max-width: 640px) 50vw, 380px", verh=(1, 1))}' + (f'<figcaption>{e(f["titel"])}</figcaption>' if f.get("titel") else "") + "</figure>" for f in fotos)
    else:
        namen = [l["leistung"] for l in k["leistungen"]] or ["Eindruck"]
        kacheln = "".join(f'<figure>{kunst(n, k["motiv"])}<figcaption>{e(namen[n % len(namen)])}</figcaption></figure>' for n in range(6))
        if not k["demo"]:
            warnung("Galerie ohne echte Fotos: nur Platzhalter. So nicht live schalten.")
    beschr = kuerzen(f"{k['woerter']['galerie_lead']} {k['name']}{', ' + k['ort'] if k['ort'] else ''}.")
    return kopf(k, "galerie.html", f"Galerie · {k['name']}", beschr, "galerie.html") + f"""
<div class="page-hero"><div class="wrap">
  <p class="breadcrumb"><a href="index.html">Start</a> <span aria-hidden="true">›</span> Galerie</p>
  <h1>Galerie</h1>
  <p class="lead">{e(k['woerter']['galerie_lead'])}</p>
</div></div>
<section><div class="wrap"><div class="gallery">{kacheln}</div></div></section>
{cta_band(k)}
""" + fuss(k)

def seite_kontakt(k):
    link, label, ic = termin_link(k)
    termin = f'<p class="muted">Online-Termine {T(k, "buchst du", "buchen Sie")} über {e(k["buchungstool"])}.</p>' if k["buchungstool"] and not k["buchungslink"] else ""
    zeit_id = "zeiten-kontakt"
    zeiten_wort = "Bürozeiten" if k["art"] == "handwerk" else "Öffnungszeiten"
    hinweis = f'<p class="muted" style="margin:14px 0 0;font-size:15px">{e(k["zeiten_hinweis"])}</p>' if k["zeiten_hinweis"] else ""
    karte = ""
    if k["adresse"]:
        karte = (f'<div class="wrap" style="margin-top:18px"><div class="map-card">{stadtplan()}<div><p class="eyebrow" style="justify-content:center">Anfahrt</p>'
                 f'<h2 {H3_STIL} style="margin-bottom:10px">{e(k["adresse"])}</h2>'
                 f'<p class="muted">Die Route öffnet sich bei Google Maps. Erst beim Klick werden Daten an Google übertragen.</p>'
                 f'<a class="btn btn-primary" href="{e(k["maps"])}" target="_blank" rel="noopener">{icon("ort")}Route planen</a></div></div></div>')
    beschr = kuerzen(f"Adresse, {zeiten_wort} und Kontakt von {k['name']}{' in ' + k['ort'] if k['ort'] else ''}.")
    return kopf(k, "kontakt.html", f"Kontakt & Anfahrt · {k['name']}", beschr, "kontakt.html") + f"""
<div class="page-hero"><div class="wrap">
  <p class="breadcrumb"><a href="index.html">Start</a> <span aria-hidden="true">›</span> Kontakt</p>
  <h1>Kontakt &amp; Anfahrt</h1>
  <p class="status" data-status hidden><i aria-hidden="true"></i><span></span></p>
</div></div>
<section><div class="wrap info-grid">
  <div class="card"><h2 class="h3">{T(k, "So erreichst du uns", "So erreichen Sie uns")}</h2>{kontakt_liste(k)}{termin}<a class="btn btn-primary" href="{e(link)}"{extern(link)}>{icon(ic)}{e(label)}</a></div>
  <div class="card"><h2 class="h3" id="{zeit_id}">{zeiten_wort}</h2>{stunden_tabelle(k, zeit_id)}{hinweis}</div>
</div>
{karte}
</section>
""" + fuss(k)

GESELLSCHAFTEN = ("GbR", "OHG", "KG", "GmbH", "UG (haftungsbeschränkt)", "GmbH & Co. KG", "e. V.")

def seite_impressum(k):
    im = k["impressum"]
    def wert(x, platz):
        return e(x) if x else f"<mark>{platz}</mark>"
    rf = str(im.get("rechtsform") or "").strip()
    gesellschaft = rf in GESELLSCHAFTEN
    vertreten = (f"Vertreten durch: {wert(im.get('vertreter'), '[Geschäftsführer/in bzw. Gesellschafter/innen]')}" if gesellschaft
                 else f"Inhaber/in: {wert(im.get('inhaber'), '[Vor- und Nachname]')}")
    if im.get("impressumAdresse"):
        adr_html = e(im["impressumAdresse"])
    else:
        ort = k["b"].get("ort") or ""
        stadt = " ".join(x for x in [k["b"].get("plz"), "Köln" if ort.startswith("Köln") else ort] if x)
        adr_html = f"{wert(k['b'].get('strasse'), '[Straße und Hausnummer]')}<br>{wert(stadt, '[PLZ Ort]')}"
    bl = []
    if rf and rf != "Weiß ich nicht":
        bl.append(f"<h2>Rechtsform</h2><p>{e(rf)}</p>")
    if im.get("register") or rf in ("GmbH", "UG (haftungsbeschränkt)", "OHG", "KG", "GmbH & Co. KG", "e. K.", "e. V."):
        bl.append(f"<h2>Registereintrag</h2><p>{wert(im.get('register'), '[Registergericht und Nummer, z. B. Amtsgericht Köln, HRB …]')}</p>")
    if im.get("ustid"):
        bl.append(f"<h2>Umsatzsteuer-ID</h2><p>Umsatzsteuer-Identifikationsnummer gemäß § 27a UStG: {e(im['ustid'])}</p>")
    elif im.get("widnr"):
        bl.append(f"<h2>Wirtschafts-Identifikationsnummer</h2><p>{e(im['widnr'])}</p>")
    if im.get("erlaubnis"):
        bl.append(f"<h2>Zuständige Aufsichtsbehörde</h2><p>{e(im['erlaubnis'])}<br><mark>[Name und Anschrift der Behörde prüfen]</mark></p>")
    if im.get("reglementiert") == "Ja" or im.get("kammer") or im.get("berufsbez"):
        bl.append("<h2>Berufsbezeichnung und berufsrechtliche Regelungen</h2>"
                  f"<p>Berufsbezeichnung: {wert(im.get('berufsbez'), '[z. B. Friseurmeister/in]')}, verliehen in Deutschland<br>"
                  f"Zuständige Kammer: {wert(im.get('kammer'), '[Kammer mit Anschrift]')}<br>"
                  "Es gelten folgende berufsrechtliche Regelungen: <mark>[z. B. Handwerksordnung (HwO), einsehbar unter gesetze-im-internet.de/hwo]</mark></p>")
    try:
        anzahl = int(im.get("beschaeftigte") or 0)
    except (TypeError, ValueError):
        anzahl = 0
    if anzahl > 10:
        bl.append("<h2>Verbraucherstreitbeilegung</h2><p><mark>[Pflichtangabe nach § 36 VSBG: Teilnahmebereitschaft ja/nein, ggf. zuständige Stelle. Text aus dem Generator übernehmen.]</mark></p>")
    else:
        bl.append("<h2>Verbraucherstreitbeilegung</h2><p>Wir sind nicht bereit und nicht verpflichtet, an Streitbeilegungsverfahren vor einer Verbraucherschlichtungsstelle teilzunehmen.</p>")
    if k["demo"]:
        hinweis = '<p class="placeholder"><b>Demo:</b> Dieser Betrieb ist erfunden, alle Angaben sind Beispiele. Verantwortlich für diese Demo ist der Ersteller des Website-Baukastens: <mark>[Link zum eigenen Impressum]</mark>.</p>'
    else:
        hinweis = '<p class="placeholder"><b>Vor dem Livegang:</b> Angaben mit einem Impressum-Generator (z. B. eRecht24) prüfen und ergänzen. Gelb markierte Stellen fehlen noch. Keine Rechtsberatung.</p>'
    return kopf(k, "", f"Impressum · {k['name']}", f"Impressum von {k['name']}.", "impressum.html") + f"""
<div class="page-hero"><div class="wrap"><p class="breadcrumb"><a href="index.html">Start</a> <span aria-hidden="true">›</span> Impressum</p><h1>Impressum</h1></div></div>
<section><div class="wrap prose">
  {hinweis}
  <h2>Angaben gemäß § 5 DDG</h2>
  <p>{e(im.get('firma') or k['name'])}<br>{vertreten}<br>{adr_html}</p>
  <h2>Kontakt</h2>
  <p>Telefon: {wert(k['telefon'], '[Telefon]')}<br>E-Mail: {wert(k['email'], '[E-Mail]')}</p>
  {''.join(bl)}
</div></section>
""" + fuss(k)

def seite_datenschutz(k):
    im = k["impressum"]
    verantw = (f"{e(im.get('firma') or k['name'])}<br>{e(im.get('inhaber') or im.get('vertreter') or '[Inhaber/in bzw. Geschäftsführung]')}<br>"
               f"{e(im.get('impressumAdresse') or k['adresse'] or '[Adresse]')}<br>E-Mail: {e(k['email'] or '[E-Mail]')}" + (f"<br>Telefon: {e(k['telefon'])}" if k['telefon'] else ""))
    hoster = e(k["hoster"]) if k["hoster"] else "<mark>[Name und Anschrift des Hosters]</mark>"
    abschnitte = [
        ("1. Verantwortlicher", f"<p>{verantw}</p>"),
        ("2. Überblick", "<p>Diese Website setzt <b>keine Cookies</b>, nutzt <b>kein Tracking</b> und keine Analyse- oder Werbedienste und bindet keine Inhalte anderer Anbieter ein (keine Karten, Videos oder Social-Media-Plugins). Die Schriftarten werden von unserem eigenen Webspace geladen, nicht von Google.</p>"),
        ("3. Hosting und Server-Logfiles", f"<p>Die Website wird bei {hoster} gehostet. Beim Aufruf verarbeitet der Hoster automatisch technisch notwendige Daten: IP-Adresse, Datum und Uhrzeit, aufgerufene Seite, übertragene Datenmenge, Referrer-URL, Browser und Betriebssystem. Zweck ist die Auslieferung der Website sowie die Sicherheit und Stabilität des Betriebs. Rechtsgrundlage ist Art. 6 Abs. 1 lit. f DSGVO; unser berechtigtes Interesse liegt in einer sicheren, funktionsfähigen Website. <mark>[Speicherdauer der Logfiles laut Hoster]</mark> <mark>[Hinweis auf Vertrag zur Auftragsverarbeitung nach Art. 28 DSGVO]</mark> <mark>[Falls Hoster in den USA: Übermittlung auf Grundlage des EU-US Data Privacy Framework]</mark></p>"),
        ("4. Kontakt per Telefon, E-Mail oder WhatsApp", "<p>Wenn Sie uns kontaktieren, verarbeiten wir Ihre Angaben (z. B. Name, Telefonnummer, Nachricht), um Ihre Anfrage zu beantworten und Termine zu vereinbaren. Rechtsgrundlage ist Art. 6 Abs. 1 lit. b DSGVO, soweit es um einen Termin oder Auftrag geht, sonst Art. 6 Abs. 1 lit. f DSGVO. Wir löschen die Daten, wenn die Anfrage erledigt ist, sofern keine gesetzlichen Aufbewahrungspflichten bestehen.</p>"),
    ]
    nr = 5
    if k["whatsapp"]:
        abschnitte.append((f"{nr}. WhatsApp", "<p>Unsere Website enthält Links zu WhatsApp. Erst wenn Sie einen solchen Link anklicken, werden Sie zu WhatsApp weitergeleitet; dabei erhält der Anbieter WhatsApp Ireland Limited (Teil des Meta-Konzerns) Daten wie Ihre IP-Adresse. Schreiben Sie uns über WhatsApp, verarbeitet WhatsApp Ihre Telefonnummer und Metadaten; eine Übermittlung an Meta Platforms Inc. in den USA ist möglich. Nachrichteninhalte sind laut Anbieter Ende-zu-Ende-verschlüsselt. Wenn Sie das nicht möchten, erreichen Sie uns per Telefon oder E-Mail.</p>"))
        nr += 1
    links = [x for x, an in (("Google Maps", k["adresse"]), ("das Google-Unternehmensprofil", k["google"]), ("Instagram", k["instagram"])) if an]
    if links:
        abschnitte.append((f"{nr}. Links zu anderen Anbietern", f"<p>Wir verlinken auf {', '.join(links)}. Es handelt sich um einfache Links, keine eingebetteten Inhalte. Daten werden erst übertragen, wenn Sie den Link anklicken; ab dann gelten die Datenschutzbestimmungen des jeweiligen Anbieters.</p>"))
        nr += 1
    abschnitte += [
        (f"{nr}. Ihre Rechte", "<p>Sie haben das Recht auf Auskunft (Art. 15 DSGVO), Berichtigung (Art. 16), Löschung (Art. 17), Einschränkung der Verarbeitung (Art. 18) und Datenübertragbarkeit (Art. 20). <b>Sie können der Verarbeitung Ihrer Daten, die auf Art. 6 Abs. 1 lit. f DSGVO beruht, jederzeit aus Gründen, die sich aus Ihrer besonderen Situation ergeben, widersprechen (Art. 21 DSGVO).</b> Eine formlose Nachricht an die oben genannte Adresse genügt.</p>"),
        (f"{nr + 1}. Beschwerderecht", "<p>Sie können sich bei einer Datenschutz-Aufsichtsbehörde beschweren, z. B. bei der Landesbeauftragten für Datenschutz und Informationsfreiheit Nordrhein-Westfalen, <mark>[Anschrift laut www.ldi.nrw.de]</mark>.</p>"),
        (f"{nr + 2}. Pflicht zur Bereitstellung, automatisierte Entscheidungen", "<p>Sie sind nicht verpflichtet, uns Daten zu geben. Ohne die technischen Verbindungsdaten kann die Website aber nicht angezeigt werden. Eine automatisierte Entscheidungsfindung oder Profilbildung findet nicht statt.</p>"),
        ("Stand", f"<p>{date.today().strftime('%m/%Y')}</p>"),
    ]
    body = "".join(f"<h2>{t}</h2>{h}" for t, h in abschnitte)
    return kopf(k, "", f"Datenschutz · {k['name']}", f"Datenschutzerklärung von {k['name']}.", "datenschutz.html") + f"""
<div class="page-hero"><div class="wrap"><p class="breadcrumb"><a href="index.html">Start</a> <span aria-hidden="true">›</span> Datenschutz</p><h1>Datenschutz&shy;erklärung</h1></div></div>
<section><div class="wrap prose">
  <p class="placeholder"><b>Vor dem Livegang:</b> Dieses Gerüst passt zur Technik der Website. Die endgültigen Formulierungen mit einem Generator (z. B. eRecht24 oder Datenschutz-Generator.de) abgleichen. Gelb markierte Stellen fehlen noch. Keine Rechtsberatung.</p>
  {body}
</div></section>
""" + fuss(k)

def seite_404(k):
    return kopf(k, "", f"Seite nicht gefunden · {k['name']}", "Diese Seite gibt es nicht.", "404.html", fehlerseite=True) + """
<div class="page-hero" style="border:0"><div class="wrap"><p class="eyebrow">Fehler 404</p><h1>Diese Seite gibt es <em>nicht.</em></h1><p class="lead">Vielleicht hat sich ein Tippfehler eingeschlichen.</p><p><a class="btn btn-primary" href="index.html">Zur Startseite</a></p></div></div>
""" + fuss(k)

def favicon(k):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="16" fill="{k["brand"]}"/>'
            f'<text x="32" y="41" text-anchor="middle" font-family="Arial, sans-serif" font-weight="800" font-size="26" fill="{k["brand_ink"]}">{e(k["initialen"])}</text></svg>')

def baue(quelle, ziel):
    WARNUNGEN.clear()
    k = lade(quelle)
    os.makedirs(ziel, exist_ok=True)
    for alt in os.listdir(ziel):
        if alt.endswith(".html") or alt in ("sitemap.xml", "robots.txt"):
            os.remove(os.path.join(ziel, alt))
    if os.path.isdir(os.path.join(ziel, "assets")):
        shutil.rmtree(os.path.join(ziel, "assets"))
    shutil.copytree(os.path.join(HIER, "assets"), os.path.join(ziel, "assets"))
    with open(os.path.join(ziel, "assets", "favicon.svg"), "w", encoding="utf-8") as fh:
        fh.write(favicon(k))
    seiten = {"index.html": seite_start, "leistungen.html": seite_leistungen, "ueber-uns.html": seite_ueber,
              "kontakt.html": seite_kontakt, "impressum.html": seite_impressum, "datenschutz.html": seite_datenschutz, "404.html": seite_404}
    if k["galerie"]:
        seiten["galerie.html"] = seite_galerie
    luecken = 0
    for name, fn in seiten.items():
        Zaehler.n = 0
        inhalt = re.sub(r"\n\s*\n+", "\n", fn(k))
        luecken += inhalt.count("<mark>")
        with open(os.path.join(ziel, name), "w", encoding="utf-8") as fh:
            fh.write(inhalt)
    if k["domain"] and not k["demo"]:
        heute = date.today().isoformat()
        urls = "".join(f"<url><loc>https://{k['domain']}/{'' if p == 'index.html' else p}</loc><lastmod>{heute}</lastmod></url>" for p, _ in seiten_liste(k))
        with open(os.path.join(ziel, "sitemap.xml"), "w", encoding="utf-8") as fh:
            fh.write(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n')
    with open(os.path.join(ziel, "robots.txt"), "w", encoding="utf-8") as fh:
        fh.write("User-agent: *\nAllow: /\n" + (f"Sitemap: https://{k['domain']}/sitemap.xml\n" if k["domain"] and not k["demo"] else ""))
    print(f"Fertig: {len(seiten)} Seiten für {k['name']} in {ziel} (Thema: {k['thema']})")
    if luecken and not k["demo"]:
        warnung(f"{luecken} offene Platzhalter (gelb markiert) in Impressum/Datenschutz. Vor dem Livegang ausfüllen.")
    for w in WARNUNGEN:
        print("WARNUNG:", w)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    baue(sys.argv[1], sys.argv[2])
