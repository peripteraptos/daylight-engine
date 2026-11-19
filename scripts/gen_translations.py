"""Generate strings.json and translations/*.json (run from repo root)."""

import json


def curve(lang, value_label):
    de = lang == "de"
    return {
        "night": f"{value_label} {'nachts' if de else 'at night'}",
        "day": f"{value_label} {'tagsüber' if de else 'during the day'}",
        "morning_low": "Morgens: Beginn bei Sonnenhöhe" if de else "Morning: start at sun elevation",
        "morning_high": "Morgens: Tageswert erreicht bei" if de else "Morning: day value reached at",
        "morning_shape": "Morgens: Kurvenform" if de else "Morning: curve shape",
        "evening_low": "Abends: Nachtwert erreicht bei" if de else "Evening: night value reached at",
        "evening_high": "Abends: Beginn bei Sonnenhöhe" if de else "Evening: start at sun elevation",
        "evening_shape": "Abends: Kurvenform" if de else "Evening: curve shape",
    }


def curve_desc(lang):
    de = lang == "de"
    shape = (
        "1 = gleichmäßig, größer = bleibt länger beim Nachtwert, kleiner = früher beim Tageswert"
        if de
        else "1 = even, higher = stays near the night value longer, lower = reaches day value earlier"
    )
    return {
        "morning_shape": shape,
        "evening_shape": shape,
        "morning_low": "Grad über (+) bzw. unter (−) dem Horizont"
        if de
        else "Degrees above (+) or below (−) the horizon",
        "evening_low": "Grad über (+) bzw. unter (−) dem Horizont"
        if de
        else "Degrees above (+) or below (−) the horizon",
    }


def build(lang):
    de = lang == "de"
    lamp_data = {
        "name": "Name",
        "lights": "Lampen" if de else "Lights",
        "sleep_action": "Verhalten im Sleep-Modus" if de else "Behaviour in sleep mode",
    }
    lamp_desc = {
        "lights": (
            "Mehrere Lampen nur zusammenfassen, wenn sie dieselben Einstellungen haben. Die Kalibrierung erfolgt trotzdem pro Lampe."
            if de
            else "Only group lights that share the same settings. Calibration is still per light."
        ),
    }
    advanced = {
        "name": "Erweitert" if de else "Advanced",
        "data": {
            "transition_mode": "Übergänge" if de else "Transitions",
            "detect_manual": "Manuelle Änderungen erkennen" if de else "Detect manual changes",
            "proxy": "Proxy-Licht anlegen" if de else "Create proxy light",
        },
        "data_description": {
            "transition_mode": (
                "Automatisch = nur wenn die Lampe Übergänge meldet. Viele WLAN-Lampen springen trotzdem – dann 'Nie' wählen."
                if de
                else "Automatic = only if the light reports transition support. Many Wi-Fi lights jump anyway – choose 'never' then."
            ),
            "detect_manual": (
                "Ändert jemand Helligkeit oder Farbe, pausiert die Lampe bis zum nächsten Aus/An."
                if de
                else "If someone changes brightness or colour, the light pauses until it is switched off/on."
            ),
            "proxy": (
                "Legt zusätzlich „<Name> Daylight“ an: schaltet ohne Aufblitzen ein, und sein Helligkeitsregler nutzt die Kalibrierung. In Dashboards und Automationen statt der Originallampe verwenden."
                if de
                else "Also creates “<name> Daylight”: switches on without flashing, and its brightness slider uses the calibration. Use it in dashboards and automations instead of the original light."
            ),
        },
    }
    lamp_step = lambda title: {
        "title": title,
        "data": lamp_data,
        "data_description": lamp_desc,
        "sections": {"advanced": advanced},
    }
    return {
        "config": {
            "step": {
                "user": {
                    "title": "Daylight Engine",
                    "description": (
                        "Lampen fügst du danach über „Lampe hinzufügen“ hinzu, die Tageslichtkurve stellst du unter „Konfigurieren“ ein."
                        if de
                        else "Add lights afterwards with “Add light”; adjust the daylight curve under “Configure”."
                    ),
                    "data": {"name": "Name"},
                }
            },
            "abort": {
                "single_instance_allowed": "Daylight Engine ist bereits eingerichtet."
                if de
                else "Daylight Engine is already set up."
            },
        },
        "options": {
            "step": {
                "init": {
                    "title": "Tageslichtkurve" if de else "Daylight curve",
                    "description": (
                        "Alle Werte gelten für alle Lampen. Die Lampen-Kalibrierung übersetzt sie pro Lampe."
                        if de
                        else "These values apply to all lights; each light's calibration translates them."
                    ),
                    "sections": {
                        "kelvin": {
                            "name": "Farbtemperatur" if de else "Colour temperature",
                            "data": curve(lang, "Farbtemperatur" if de else "Colour temperature"),
                            "data_description": curve_desc(lang),
                        },
                        "brightness": {
                            "name": "Helligkeit" if de else "Brightness",
                            "data": curve(lang, "Helligkeit" if de else "Brightness"),
                            "data_description": curve_desc(lang),
                        },
                        "sleep": {
                            "name": "Sleep-Modus" if de else "Sleep mode",
                            "data": {
                                "brightness": "Helligkeit" if de else "Brightness",
                                "kelvin": "Farbtemperatur" if de else "Colour temperature",
                            },
                        },
                        "bright": {
                            "name": "Volle Helligkeit" if de else "Full brightness",
                            "description": (
                                "Modus z. B. zum Suchen: alle Lampen hell und neutral."
                                if de
                                else "Mode e.g. for searching: all lights bright and neutral."
                            ),
                            "data": {
                                "brightness": "Helligkeit" if de else "Brightness",
                                "kelvin": "Farbtemperatur" if de else "Colour temperature",
                                "timeout": "Automatisch beenden nach"
                                if de
                                else "Switch off automatically after",
                                "turn_on": "Ausgeschaltete Lampen einschalten"
                                if de
                                else "Switch on lights that are off",
                            },
                            "data_description": {
                                "timeout": "0 = nie" if de else "0 = never",
                                "turn_on": (
                                    "Beim Beenden werden genau diese Lampen wieder ausgeschaltet."
                                    if de
                                    else "When the mode ends, exactly these lights are switched off again."
                                ),
                            },
                        },
                        "updates": {
                            "name": "Aktualisierung" if de else "Updates",
                            "data": {
                                "interval": "Intervall" if de else "Interval",
                                "transition": "Übergangszeit" if de else "Transition",
                                "turn_on_transition": "Übergang beim Einschalten"
                                if de
                                else "Transition when switched on",
                                "min_brightness_change": "Mindeständerung Helligkeit"
                                if de
                                else "Minimum brightness change",
                                "min_kelvin_change": "Mindeständerung Farbtemperatur"
                                if de
                                else "Minimum colour temperature change",
                            },
                            "data_description": {
                                "min_brightness_change": (
                                    "Kleinere Änderungen werden nicht gesendet – schont das Zigbee-Netz."
                                    if de
                                    else "Smaller changes are not sent, which keeps Zigbee traffic low."
                                ),
                                "turn_on_transition": (
                                    "0 = sofort korrigieren, wenn eine Lampe außerhalb von Home Assistant eingeschaltet wurde."
                                    if de
                                    else "0 = correct immediately when a light was switched on outside Home Assistant."
                                ),
                            },
                        },
                        "manual": {
                            "name": "Manuelle Änderungen" if de else "Manual changes",
                            "data": {
                                "detect": "Erkennen" if de else "Detect",
                                "reset_on_off": "Beim Ausschalten zurücksetzen"
                                if de
                                else "Reset when switched off",
                                "timeout": "Automatisch zurücksetzen nach"
                                if de
                                else "Reset automatically after",
                            },
                            "data_description": {"timeout": "0 = nie" if de else "0 = never"},
                        },
                    },
                }
            },
            "error": {
                "invalid_curve": (
                    "Ungültige Kurve: der Beginn muss unter dem Ende liegen und alle Werte im gültigen Bereich."
                    if de
                    else "Invalid curve: start elevation must be below end elevation and values in range."
                )
            },
        },
        "config_subentries": {
            "lamp": {
                "entry_type": "Lampe" if de else "Light",
                "initiate_flow": {"user": "Lampe hinzufügen" if de else "Add light"},
                "step": {
                    "user": lamp_step("Lampe hinzufügen" if de else "Add light"),
                    "reconfigure": lamp_step("Lampe bearbeiten" if de else "Edit light"),
                },
                "error": {
                    "no_lights": "Bitte mindestens eine Lampe wählen."
                    if de
                    else "Select at least one light.",
                    "light_in_use": (
                        "Eine der Lampen ist bereits in einem anderen Eintrag."
                        if de
                        else "One of the lights is already used in another entry."
                    ),
                    "proxy_not_allowed": (
                        "Proxy-Lichter von Daylight Engine können nicht selbst gesteuert werden – wähle die Originallampe."
                        if de
                        else "Daylight Engine proxy lights cannot be managed themselves – select the original light."
                    ),
                },
                "abort": {"reconfigure_successful": "Gespeichert." if de else "Saved."},
            }
        },
        "selector": {
            "sleep_action": {
                "options": {
                    "follow": "Sleep-Zielwert folgen" if de else "Follow sleep target",
                    "minimum": "Minimale Helligkeit" if de else "Minimum brightness",
                    "off": "Ausschalten" if de else "Turn off",
                    "unchanged": "Nicht verändern" if de else "Leave unchanged",
                }
            },
            "transition_mode": {
                "options": {
                    "auto": "Automatisch" if de else "Automatic",
                    "always": "Immer" if de else "Always",
                    "never": "Nie" if de else "Never",
                }
            },
        },
        "entity": {
            "switch": {
                "enabled": {"name": "Automatik" if de else "Automatic control"},
                "sleep": {"name": "Sleep-Modus" if de else "Sleep mode"},
                "bright": {"name": "Volle Helligkeit" if de else "Full brightness"},
            },
            "sensor": {
                "target_brightness": {"name": "Ziel-Helligkeit" if de else "Target brightness"},
                "target_kelvin": {"name": "Ziel-Farbtemperatur" if de else "Target colour temperature"},
                "sun_elevation": {"name": "Sonnenhöhe" if de else "Sun elevation"},
            },
        },
        "services": {
            "reset_manual": {
                "name": "Manuelle Steuerung aufheben" if de else "Reset manual control",
                "description": (
                    "Lampen wieder automatisch steuern. Ohne Auswahl gilt es für alle."
                    if de
                    else "Resume automatic control. Applies to all lights if none are selected."
                ),
                "fields": {"entity_id": {"name": "Lampen" if de else "Lights", "description": "Optional"}},
            },
            "apply": {
                "name": "Jetzt anwenden" if de else "Apply now",
                "description": (
                    "Aktuellen Zielwert sofort an die eingeschalteten Lampen senden."
                    if de
                    else "Send the current target to all lights that are on right now."
                ),
                "fields": {
                    "entity_id": {"name": "Lampen" if de else "Lights", "description": "Optional"},
                    "transition": {
                        "name": "Übergang" if de else "Transition",
                        "description": "Sekunden" if de else "Seconds",
                    },
                },
            },
        },
        "exceptions": {
            "not_loaded": {
                "message": "Daylight Engine ist nicht geladen." if de else "Daylight Engine is not loaded."
            }
        },
    }


BASE = "custom_components/daylight_engine/"
for lang, path in (("en", "strings.json"), ("en", "translations/en.json"), ("de", "translations/de.json")):
    with open(BASE + path, "w", encoding="utf-8") as f:
        json.dump(build(lang), f, ensure_ascii=False, indent=2)
        f.write("\n")
