# Meine Website – Sidehustle

Hier liegt der Code für meinen Website-Sidehustle: meine eigene Website und Vorlagen für Kundenprojekte.

## Aufbau

| Ordner | Inhalt |
|---|---|
| `eigene-website/` | Meine eigene Website (Visitenkarte und Referenz für Kunden) |
| `vorlagen/` | Wiederverwendbare Bausteine für Kunden-Websites |
| `baukasten/` | Website-Baukasten: macht aus den Fragebogen-Antworten eine fertige Website mit Unterseiten |
| `beispiele/` | Drei Demo-Websites (fiktive Betriebe) zum Zeigen im Laden |
| `fragebogen/` | Fragebogen für Kunden: Sie füllen ihn auf dem Handy aus und schicken die Antworten per WhatsApp |

Jede Kunden-Website bekommt später ein **eigenes Repository**, damit Projekte sauber getrennt bleiben.

## Website ansehen

`eigene-website/index.html` im Browser öffnen. Es wird nichts installiert, die Seite ist reines HTML und CSS.

## Online stellen

Am einfachsten mit **GitHub Pages**: Repository → Settings → Pages → Branch `main`, Ordner `/ (root)` auswählen. Danach ist die Seite unter
`https://demirmelih2005-hash.github.io/Meine-Website-Sidehustle/eigene-website/` erreichbar.

## Fragebogen für Kunden

Nach dem Einschalten von GitHub Pages erreichbar unter
`https://demirmelih2005-hash.github.io/Meine-Website-Sidehustle/fragebogen/`

Vorher ausfüllen: oben im Skript in `fragebogen/index.html` die Einstellungen (`[Dein Name]`, WhatsApp-Nummer, E-Mail) und die Platzhalter in `fragebogen/impressum.html` und `fragebogen/datenschutz.html`. **Ohne vollständiges Impressum nicht öffentlich nutzen.**
Die Antworten werden nirgends gespeichert. Der Kunde schickt sie selbst per WhatsApp. Ganz unten steckt ein Datenblock, aus dem Claude die Website baut.

## Demo-Websites

Nach dem Einschalten von GitHub Pages:
- `…/beispiele/veedel-cut/` (Barbershop, Thema nacht)
- `…/beispiele/kaffeekiesel/` (Café, Thema edel)
- `…/beispiele/maler-brueck/` (Handwerk, Thema hell)

## Wichtig

Dieses Repository ist **öffentlich**. Hier gehören keine Kundendaten, Passwörter, Verträge oder Preise hinein, die nicht jeder sehen soll.
