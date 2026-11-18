# Website-Baukasten

Aus den Antworten des Kunden-Fragebogens wird eine fertige, professionelle Website mit Unterseiten.

## So läuft ein Kundenprojekt

1. Der Kunde füllt den [Fragebogen](../fragebogen/) aus und schickt die Antworten per WhatsApp.
2. Du leitest die Nachricht an Claude weiter. Claude legt eine Kunden-Datei an (`kunde.json`) und schreibt die Texte.
3. Claude startet den Generator. Heraus kommen alle Seiten als reines HTML.
4. Du zeigst dem Kunden den Entwurf, sammelst Korrekturen, Claude baut neu.
5. Fotos rein, Impressum und Datenschutz aus dem Generator einfügen, online stellen.

**Wichtig:** Echte Kundendaten gehören nicht in dieses öffentliche Repository. Jeder echte Kunde bekommt ein eigenes, privates Repository.

## Was der Generator baut

| Seite | Inhalt |
|---|---|
| `index.html` | Startseite mit Hero, Fakten, Leistungen, Vorteilen, Über uns, Öffnungszeiten, FAQ, Abschluss-Band |
| `leistungen.html` | Komplette Preisliste |
| `ueber-uns.html` | Geschichte und Team |
| `galerie.html` | Fotos (nur wenn im Fragebogen gewünscht) |
| `kontakt.html` | Kontaktwege, Öffnungszeiten, Anfahrt per Link |
| `impressum.html`, `datenschutz.html` | Vorlagen mit Platzhaltern, vor dem Livegang mit Generator füllen |
| `404.html`, `sitemap.xml`, `robots.txt` | Technik für Google |

Eingebaut: „Jetzt geöffnet“-Anzeige nach Kölner Uhrzeit, WhatsApp-Knopf auf dem Handy, Google-Daten (schema.org) für die lokale Suche, Du- oder Sie-Ansprache.

## Drei Design-Themen

| Thema | Wirkung | Passt zu |
|---|---|---|
| `nacht` | dunkel, laut, plakativ | Barbershops, Tattoo, Streetfood |
| `hell` | klar, freundlich, modern | Handwerk, Praxen, Dienstleister |
| `edel` | warm, elegant, mit Serifenschrift | Cafés, Kosmetik, Friseure mit Anspruch |

Wählt der Kunde im Fragebogen „Dunkel und stylisch“ oder „Frech und laut“, wird automatisch `nacht` genommen, bei „Edel“ oder „Klassisch“ `edel`, sonst `hell`.

## Datenschutz von Haus aus

- Schriften liegen im Ordner `assets/fonts`, nichts wird von Google geladen.
- Keine Cookies, kein Tracking, keine eingebettete Karte (nur ein Link zu Google Maps).
- Kein Kontaktformular, Kontakt per Telefon, E-Mail oder WhatsApp.

## Echte Fotos einbauen

Fotos kommen in einen Ordner `fotos/` neben die Seiten, jeweils in drei Breiten als WebP und JPG
(z. B. `laden-480.webp`, `laden-800.jpg`, `laden-1200.jpg`). In der Kunden-Datei:

```json
"fotos": {
  "hero":   { "datei": "laden", "alt": "Blick in den Laden mit drei Barberstühlen" },
  "ueber":  { "datei": "team",  "alt": "Kemal beim Fade-Schnitt" },
  "team":   { "Kemal": { "datei": "kemal", "alt": "Porträt von Kemal" } },
  "galerie": [ { "datei": "fade-1", "alt": "Skin Fade von der Seite", "titel": "Skin Fade" } ],
  "og": "fotos/og-1200x630.jpg"
}
```

Ohne Fotos zeigt der Baukasten ruhige Muster in den Markenfarben. Eine Galerie nur mit Mustern nicht live schalten.

## Vor dem Livegang (Checkliste)

- Generator-Warnungen lesen und abarbeiten (z. B. offene Platzhalter, unklare Öffnungszeiten).
- Impressum und Datenschutz: gelb markierte Stellen mit dem Generator füllen, `seite.hoster` eintragen.
- Echte Fotos mit Alt-Texten, Einwilligung der abgebildeten Personen.
- Domain und Hosting laufen auf den Namen des Kunden.

## Für Claude: Generator starten

```
python3 baukasten/generator.py baukasten/beispiel/veedel-cut.json beispiele/veedel-cut
```

Nur Python mit Bordmitteln, nichts muss installiert werden. Beispiele für Kunden-Dateien liegen in `beispiel/`.
