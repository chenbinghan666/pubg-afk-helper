# PUBG AFK Helper

[简体中文](https://github.com/chenbinghan666/pubg-afk-helper/blob/main/README.md) · [English](https://github.com/chenbinghan666/pubg-afk-helper/blob/main/docs/locales/README.en.md) · [日本語](https://github.com/chenbinghan666/pubg-afk-helper/blob/main/docs/locales/README.ja.md) · **Deutsch** · [Français](https://github.com/chenbinghan666/pubg-afk-helper/blob/main/docs/locales/README.fr.md) · [Español](https://github.com/chenbinghan666/pubg-afk-helper/blob/main/docs/locales/README.es.md) · [Português](https://github.com/chenbinghan666/pubg-afk-helper/blob/main/docs/locales/README.pt.md)

Erkennt PUBG-Bildschirme mit OpenCV, zeigt den Erkennungsstatus an und führt unter Windows konfigurierbare Abläufe aus. Enthält eine Vorschau ohne Eingaben und Offline-Regressionstests.

Python · OpenCV · Windows

[![Windows tests](https://github.com/chenbinghan666/pubg-afk-helper/actions/workflows/tests.yml/badge.svg)](https://github.com/chenbinghan666/pubg-afk-helper/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](../../LICENSE)
![Platform: Windows](https://img.shields.io/badge/platform-Windows-0078D6)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB)

Automatisches PUBG-Prozesstool basierend auf **OpenCV-Bildschirmerkennung, Windows-Simulationseingabe und Minimap-Änderungserkennung**.
Identifizieren Sie die Lobby- und Kassenschnittstelle, führen Sie konfigurierbare Matching-, Sprung-, Bewegungs-, Abhol- und Fluchtprozesse durch und zeigen Sie den aktuellen Schritt über das Overhead-Statusfenster an.

## Funktion

- Die **-Schnittstelle erkennt**: Lobby, Rückkehr zur Lobby, Bestätigung des Verlassens, Charakterabrechnung und Belohnungsseite; Kontinuierliche Erkennungsbestätigung und Begrenzung wiederholter Vorgänge.
- **relative Positionierung**: Skalieren Sie die Vorlage und die Koordinaten entsprechend der Bildschirmgröße und unterstützen Sie die randausgerichtete Suche für einige Breitbild-Layouts.
- **Spielablauf**: Zeitsprung, nachdem die Halle verschwunden ist, einmal rechts abbiegen, W+Linke Umschalttaste, um weiter vorwärts zu gehen, F drücken, um aufzuheben, nachdem man nach unten geschaut hat.
- **Mini-Karten-Antihaftwand**: Vergleichen Sie nur das Kartengelände in der unteren rechten Ecke und blockieren Sie die zentrale Zeichenmarkierung; Versuchen Sie es zuerst mit Umschalt+C, gehen Sie dann zurück und bewegen Sie sich entsprechend den Erkennungsergebnissen nach links und rechts.
- **Top-Statusfenster**: Zeigt Countdown, Aktionen, Pausengründe und Minikartenerkennungsindikatoren an; Das Eindringen der Maus raubt dem Spiel nicht den Fokus.
- **konfigurierbar und testbar**: JSON-Konfiguration, Vorlagenaufzeichnungstool, Offline-Regressionstests, Windows CI.

Das Programm verarbeitet Screenshots und normale Betriebssystemeingaben, liest keinen Spielspeicher und injiziert keine Spielprozesse.
Das Projekt befindet sich noch in einem frühen Stadium; Festgelegte Zeiten und Änderungen auf der Minikarte sind ungefähre Angaben und können nicht das Flugzeug, die tatsächliche Landung, den Abholerfolg oder den Erhalt der Prämie bestätigen.
Bitte bestätigen Sie die Spielregeln und Kontorisiken vor der Nutzung selbst; Dieses Projekt bietet keine Anti-Cheating-Bypass-Funktionen.

## Schnellstart

Erfordert **Windows 10/11, Python 3.11+**, das Spiel verwendet den randlosen Fenstermodus des Hauptmonitors.

1. Laden Sie `PUBG-helper.zip` in der neuesten Version](https://github.com/chenbinghan666/pubg-afk-helper/releases/latest) von [ herunter oder klonen Sie dieses Repository.
2. Installieren Sie Python und aktivieren Sie **Python zu PATH hinzufügen**.
3. Doppelklicken Sie auf `install.cmd` und warten Sie, bis die Abhängigkeitsinstallation abgeschlossen ist.
4. Wenn Sie es zum ersten Mal verwenden, doppelklicken Sie auf **`preview.cmd`**, wechseln Sie zurück zum Spiel und überprüfen Sie das Erkennungsprotokoll. In diesem Modus werden keine Eingaben gesendet.
5. Nachdem Sie bestätigt haben, dass die Erkennung korrekt ist, schließen Sie die Vorschau und doppelklicken Sie auf **`launch.cmd`**, um den automatischen Betrieb zu aktivieren.

```powershell
git clone https://github.com/chenbinghan666/pubg-afk-helper.git
cd pubg-afk-helper
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe bot.py             # Nur erkennen
.\.venv\Scripts\python.exe bot.py --live      # Eingabe aktivieren
```

Git-Klone lesen standardmäßig `config.example.json`. Kopieren Sie es vor der Anpassung nach `config.json`. Die lokale Konfiguration wird dann nicht an Git übermittelt:

```powershell
Copy-Item config.example.json config.json
```

Das Warehouse verfügt über eine Reihe von Vorlagen zum Zuschneiden von Schaltflächen für die Benutzeroberfläche für traditionelles Chinesisch. Wenn die Sprache, die Spielversion, der HUD-Maßstab oder das Layout unterschiedlich sind, muss die Vorlage neu aufgezeichnet werden und es kann nicht garantiert werden, dass sie direkt auf allen Computern anwendbar ist.

## Standardprozess

```text
Identifizieren Sie die Halle → F beginnt mit dem Matching
  → Das Verschwinden in der Lobby wurde dreimal hintereinander festgestellt → 120 Sekunden warten
  → F Versuchen Sie Fallschirmspringen → biegen Sie einmal rechts ab → W + linke Umschalttaste
  → 30 Sekunden nach dem Fallschirmsprung: Blick auf den Boden → Tippen Sie alle 0,5 Sekunden auf F
  → Die Minikarte ist etwa 1 Sekunde lang stabil: Versuchen Sie, sie zu überqueren, ggf. rückwärts/überqueren
  → Tod/Begleichung: Taste loslassen → Zurück zur Lobby → nächste Runde
```

Das Verschwinden der Lobby kann auch ein Ladebildschirm sein, der nicht beweist, dass Sie den Raum betreten haben. Alle Zeiten sind einstellbar.
Die Standardverschiebung für Rechtskurve **4050** und die Aufwärtsverschiebung **5000** sind nur Referenzparameter; Der tatsächliche Winkel hängt von der Spielempfindlichkeit und den Mauseinstellungen ab.
Sprinten und Umschalt+C-Sprünge müssen mit den Einstellungen für Spieltaste und Halten/Umschalten übereinstimmen.

## Bedientasten

| Knopf | Funktion |
| --- | --- |
| **F8** | Nur pausieren, vom Skript gehaltene Tasten loslassen |
| **F7** | Fahren Sie einfach fort |
| **F9** | Verlassen Sie den Raum und lassen Sie die Taste los |
| **Ctrl+C** | Stoppen Sie das Programm im Terminal |

Die Eingabe wird beim Verlassen des Spiels pausiert und nach dem Zurückschalten automatisch wieder aufgenommen; Der gestartete Countdown wird weiterhin auf Basis der tatsächlich verstrichenen Zeit berechnet.
Die Pause in der Mausecke ist standardmäßig deaktiviert, um einen automatischen Schutz vor Übersehen des Auslösers zu vermeiden, und kann individuell mit `mouse_corner_pause` aktiviert werden.
Die Reinigung per Tastendruck kann nicht durchgeführt werden, wenn der Vorgang zwangsweise beendet wird oder der Computer ausgeschaltet ist.

## Konfiguration und Fehlerbehebung

Vollständige Parameter, Vorlagenaufzeichnungsbefehle, relative Minimap-Fläche und Empfindlichkeitskalibrierungsmethode finden Sie im [-Konfigurations- und Nutzungshandbuch](../../docs/CONFIGURATION.md).

| Frage | Vorrangige Prüfung |
| --- | --- |
| Keine Anerkennung oder Aktion | Ob im oberen Fenster Pause angezeigt wird, ob sich das Spiel im Vordergrund befindet und ob der Fenstertitel `PUBG` enthält |
| Die Start- oder Abrechnungserkennung ist fehlgeschlagen | Ob die Sprache der Benutzeroberfläche, die Auflösung und der HUD-Maßstab mit der Vorlage übereinstimmen |
| Fallschirmsprung zu früh / zu spät | `movement.jump_delay_seconds` |
| Zu früh aufstehen/in die falsche Richtung nach unten schauen | `pickup_delay_after_jump_seconds`-, `look_down_pixels`- und Y-Achsen-Umkehreinstellungen |
| Falscher Rechtsabbiegewinkel | Kalibrieren Sie entsprechend dem tatsächlichen Drehwinkel `turn_right_pixels` |
| Sprinten oder Springen haben keine Wirkung | Tastenbelegung, Haltemodus, Laufberechtigungen und ob das Spiel analoge Eingaben akzeptiert |
| Fehleinschätzung/fehlende Anti-Jamming-Wand | Stabile Maßstabsanzeigen für Minikartenbereich, Zoom, Rotationseinstellungen und Overhead-Fenster |

Das Protokoll wird in das lokale `bot.log` geschrieben. Bitte entfernen Sie Konto, Chat, privaten Pfad und andere Informationen, bevor Sie Feedback geben.

## entwickeln

```powershell
.\.venv\Scripts\python.exe -m unittest -v
.\.venv\Scripts\python.exe package.py
```

Der Test simuliert Tastatur- und Mauseingaben, ohne das Spiel zu bedienen. Die öffentliche Version generiert automatisch synthetische Bilder zum Testen; wenn es lokal existiert
`reference_screens/` können Sie die entsprechenden persönlichen Referenz-Screenshots für zusätzliche Regressionen verwenden. Dieses Verzeichnis ist nicht im Warehouse- oder Distributionspaket enthalten.
CI führt Tests unter Windows mit Python 3.11 und 3.12 durch.
Offline-Tests können die Überprüfung eines echten Spiels unter unterschiedlicher Hardware, Spielversion und Empfindlichkeit nicht ersetzen.

Hauptdateien: `bot.py` ist die Zustandsmaschine, Erkennung und Eingabeimplementierung, `status_overlay.py` ist das Statusfenster,
`prepare_templates.py` ist ein Tool zur Generierung von Vorlagen mit fünf Schnittstellen, und `package.py` ist ein Skript zum Erstellen von Distributionspaketen.

Gerne können Sie reproduzierbare Probleme über [Issues](https://github.com/chenbinghan666/pubg-afk-helper/issues) melden.
Bitte lesen Sie die Beitragsanweisungen[](../../CONTRIBUTING.md), bevor Sie Änderungen einreichen. Versionsdatensätze finden Sie unter [CHANGELOG](../../CHANGELOG.md).

## Lizenz

Originalcode und Dokumentation sind unter der [MIT-Lizenz](../../LICENSE) lizenziert. Der Ausschnitt der Spieloberfläche, der Name und das Warenzeichen gehören weiterhin den jeweiligen Rechteinhabern. Weitere Informationen finden Sie in der Erklärung des Drittanbieters [](../../NOTICE.md). Dieses Projekt hat keine Zugehörigkeit oder offizielle Partnerschaft mit KRAFTON / PUBG.
