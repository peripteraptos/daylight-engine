# Daylight Engine

Tageslicht-folgende Lichtsteuerung für Home Assistant – Nachfolger-Idee zu Adaptive Lighting
mit globalem Sleep-Modus, Kalibrierprofilen pro Lampe und gemischten RGB/CCT-Dimmkurven.

**Status: Phase 2 – lauffähige Integration.** Kalibrier-Oberfläche (Phase 3) und Proxy-Lichter (Phase 4) folgen.

## Installation

HACS → *Benutzerdefinierte Repositories* → dieses Repo als *Integration* hinzufügen, oder den Ordner
`custom_components/daylight_engine` nach `config/custom_components/` kopieren. Danach Home Assistant neu starten
und unter *Einstellungen → Geräte & Dienste* „Daylight Engine“ hinzufügen.

## Einrichtung

- **Lampen:** im Integrationseintrag über *Lampe hinzufügen*. Mehrere Lampen mit gleichen Einstellungen dürfen
  in einen Eintrag. Pro Eintrag: Verhalten im Sleep-Modus, unter *Erweitert* Übergänge und Erkennung manueller Änderungen.
- **Tageslichtkurve:** über *Konfigurieren*, aufgeteilt in Farbtemperatur, Helligkeit, Sleep-Modus,
  Aktualisierung und manuelle Änderungen (alle außer Farbtemperatur standardmäßig eingeklappt).
- **Lampentyp:** wird automatisch aus den Home-Assistant-Attributen erkannt (Farbmodi, Kelvin-Bereich, Übergänge) –
  egal ob Zigbee2MQTT, WLED, ESPHome oder anderes.

## Entitäten

| Entität | Zweck |
|---|---|
| `switch.…_automatik` | Automatik für alle Lampen an/aus. Attribute: verwaltete Lampen, Lampen unter manueller Steuerung |
| `switch.…_sleep_modus` | **Ein** Sleep-Schalter für alle Lampen |
| `sensor.…_ziel_helligkeit` / `…_ziel_farbtemperatur` | Aktueller globaler Zielwert |
| `sensor.…_sonnenhohe` | Diagnose, standardmäßig deaktiviert |

Dienste: `daylight_engine.apply` (Zielwert sofort senden) und `daylight_engine.reset_manual`.

## Verhalten

- Aktualisiert nur **eingeschaltete** Lampen und schaltet nie eine Lampe selbst ein.
- Wird eine Lampe außerhalb der Integration eingeschaltet (Dashboard, Wandschalter, App), korrigiert sie sie sofort.
  Ein kurzes Aufblitzen ist ohne Proxy-Lichter (Phase 4) nicht vermeidbar.
- Kleine Zieländerungen unterhalb der Mindeständerung werden nicht gesendet; gleiche Befehle werden für mehrere
  Lampen gebündelt.
- **Manuelle Änderungen:** Ändert jemand Helligkeit/Farbe einer eingeschalteten Lampe, pausiert sie bis zum
  nächsten Aus/An (oder Timeout). Eigene Befehle werden über den HA-Kontext erkannt; späte Zwischenmeldungen
  während eines Übergangs und Meldungen, die dem gesendeten Wert entsprechen, zählen nicht als manuell.
- **Sleep pro Lampe:** folgen / minimal / aus / unverändert. Wird eine „aus“-Lampe im Sleep-Modus bewusst
  eingeschaltet, wird sie auf Minimum gedimmt statt wieder ausgeschaltet.
- **An/Aus-Lampen** werden nur vom Sleep-Modus („aus“) geschaltet, sonst nicht angefasst.
- Kalibrierprofile liegen in `.storage/daylight_engine.profiles`; ohne Profil gilt ein lineares Standardprofil.

## Aufbau

```
custom_components/daylight_engine/
  engine/              # reines Python, keine HA-Abhängigkeit
    sun.py             # Sonnenstand (NOAA), Morgen/Abend-Erkennung
    target.py          # globaler Zielwert: Helligkeit % + Kelvin aus Sonnenhöhe, Sleep-Override
    profile.py         # Lampenprofile: logische Helligkeit -> Gerätebefehl (CCT/RGB/On-Off)
    color.py           # Kelvin -> RGB, Kanal-Gains
    detect.py          # Fähigkeiten aus HA-Attributen + Standardprofil
    lamp.py            # Zielwert + Modus + Profil -> Befehl (inkl. Sleep-Verhalten pro Lampe)
tests/                 # pytest, inkl. Abgleich des Sonnenstands mit astral
scripts/simulate_day.py
```

## Konzepte

**Zielwert** – geräteunabhängig: *logische* Helligkeit (0–100 %, so wie man sie wahrnimmt) und Kelvin.
Beide folgen der Sonnenhöhe mit getrennten Rampen für Morgen und Abend (`Ramp(low, high, shape)`).
Kelvin wird in Mired interpoliert, damit der Verlauf gleichmäßig wirkt.

**Lampenprofil** – übersetzt logische Helligkeit in Gerätewerte über aufeinanderfolgende Segmente,
die zusammen (0, 100] abdecken:

- `CctSegment`: Stützpunkte logisch → Geräte-Helligkeit; Kelvin wird auf den Lampenbereich begrenzt
  (ohne Kelvin-Bereich = reiner Dimmer).
- `RgbSegment`: zusätzlich Kanal-Gains pro Stützpunkt, um nicht-lineare RGB-Kanäle zu korrigieren;
  Kelvin wird per RGB nachgebildet und auf `min_kelvin`/`max_kelvin` begrenzt.
- `OnOffProfile`: Schwellwert mit Hysterese.

An Segmentgrenzen verhindert eine Hysterese ständiges Umschalten zwischen RGB und CCT.
Profile lassen sich mit `profile_to_dict` / `profile_from_dict` als JSON speichern.

**Sleep pro Lampe** – `follow` (globaler Sleep-Zielwert), `minimum` (erster Kalibrierpunkt),
`off`, `unchanged`.

## Entwickeln

```bash
pip install -e ".[test]"   # bringt Home Assistant + Test-Harness mit
pytest
python scripts/simulate_day.py --lat 52.52 --lon 13.405 --step 30
python scripts/simulate_day.py --profile mein_profil.json      # mit Gerätebefehlen
```

Die Skripte und `engine/` kommen ohne Home Assistant aus.

## Vorschau der Engine

![Tagesverlauf](docs/01_tagesverlauf_heute.png)
![Jahreszeiten](docs/02_jahreszeiten.png)
![Lampenprofil](docs/03_lampenprofil.png)

Neu erzeugen: `python scripts/render_docs.py` (benötigt matplotlib).
