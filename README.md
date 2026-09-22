# GUI_AMS
User Interface for Accumulator Managment System

## Start unter Windows

1. Python 3.12 installieren (Option **Add python.exe to PATH** aktivieren).
2. Den gesamten Projektordner kopieren und `start.bat` doppelklicken.
   Das Skript erstellt eine lokale `.venv` und installiert Sanic und pyserial.
   Beim ersten Start werden Internetzugang und Zugriff auf PyPI benötigt.
3. Im Browser http://localhost:8081 öffnen, den passenden COM-Port und
   die Baudrate des Geräts auswählen und verbinden. Das Terminal offen lassen.

Die `.venv` nicht zwischen Laptops kopieren; sie wird pro Rechner erstellt.
Falls VS Code weiterhin fehlende Imports meldet: **Python: Select Interpreter**
aufrufen und `.venv\Scripts\python.exe` auswählen. Das Paket für `import serial`
heißt **pyserial**, nicht `serial`.

Unter Linux/macOS: `python3 -m venv .venv`, anschließend
`.venv/bin/python -m pip install -r requirements.txt` und
`.venv/bin/python main.py` ausführen. Serielle Zugriffsrechte müssen vorhanden sein.
Je nach USB-Adapter ist auf dem jeweiligen Rechner zusätzlich ein Treiber nötig.

## USB-Empfang

Der Decoder entspricht `usb_control.c` und `usb_measurements.c`:
`[02][00][LEN][A1][ID][DATA...][XOR]`. LEN umfasst ID und DATA.
Teilpakete werden gepuffert, Prüfsummen kontrolliert und beschädigte Pakete verworfen.

- `0x40`: Stackindex, 12 Zellspannungen (uint16 Big Endian /10000 V),
  12 Zelltemperaturen (uint16 Big Endian /1000 °C).
- `0x21`: TS-Spannung /100 V; `0x22`: Strombetrag /10 A.
- `0x28`: minimale Zelltemperatur /1000 °C.
- `0x90`: optionale LTC-Temperaturen (int16 Big Endian /10 °C).

Temperaturen 0xFFFF/0xFFFE sowie Spannungen 0/0xFFFF gelten als ungültig.
Temperaturen werden entsprechend der Firmware unsigned gelesen, damit z.B.
40000 korrekt als +40 °C erscheint. Negative Temperaturen sind im uint16-
Milligradformat der Firmware nicht eindeutig darstellbar.

Die Oberfläche zeigt weiterhin 11 Zellen pro Stack. Kanal 12 wird wie in der
Firmware von Zellstatistiken ausgeschlossen, Temperaturkanal 10 zusätzlich von
Temperatur-Minimum/Maximum. Die Stacksumme umfasst die 11 angezeigten Zellen und
erscheint nur, wenn alle 11 Spannungen gültig sind. Alle 12 Kanäle werden empfangen.

Ohne Messdaten und nach 5 Sekunden ohne Aktualisierung erscheint --; Diagramme
zeigen Lücken. Es gibt keine Beispielwerte. Empfangspausen schließen den Port nicht.
Nach einem USB-Fehler wird er geschlossen und kann erneut verbunden werden.

Die bereitgestellte Firmware sendet im aktiven Sendezyklus keine LTC-Temperaturen.
Daher bleibt LTC intern --, bis 0x90 oder ein Stackpaket mit LTC-Anhang gesendet wird.
