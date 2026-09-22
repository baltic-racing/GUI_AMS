# GUI_AMS
<<<<<<< Updated upstream

Bestehende BRT-Oberfläche mit USB-CDC-Empfang für die STM32-AMS-Firmware.

## Start

Python 3.12 oder neuer:

```powershell
python -m pip install "sanic>=23.12,<26" "pyserial>=3.5,<4"
python main.py
```

Im Browser http://127.0.0.1:8081 öffnen, den COM-Port des STM32 auswählen/eintragen
und Connect drücken. Danach Accumulator öffnen. Der Port bleibt beim Seitenwechsel
verbunden. Standard: 115200 Baud, 8N1. Portvorschläge erscheinen im Eingabefeld.
Nach Abziehen des USB-Kabels erneut verbinden.

Layout, Farben, Stack-/Zellboxen und Diagramme bleiben erhalten. Chart.js wird wie
bisher vom CDN geladen und benötigt Internet; die Messwertboxen funktionieren auch
bei fehlendem Chart.js. Fehlende, ungültige oder seit 5 Sekunden nicht aktualisierte
Messwerte erscheinen als --; Diagramme erhalten dafür null (Lücken).

## Protokoll

Referenz: usb_control.c, usb_measurements.c und bms.c der bereitgestellten Firmware.
Format: `[02][00][LEN][A1][MESSAGE_ID][DATA...][XOR]`.
LEN zählt MESSAGE_ID + DATA, die Prüfsumme XOR umfasst alle vorangehenden Bytes.
Der Stream-Parser verarbeitet fragmentierte und zusammengefasste Pakete.

- 0x40: Stackindex 0–11, 12 uint16-Zellspannungen /10000 V,
  12 uint16-Temperaturen /1000 °C, jeweils Big Endian.
- Optional werden zwei angehängte LTC-Bytes (int16 /10 °C) unterstützt.
- 0x90: 12 LTC-Temperaturen (int16 /10 °C).
- 0x21: TS-Spannung uint16 /100 V; 0x22: Strom uint16 /10 A.
- 0x28: minimale Zelltemperatur uint16 /1000 °C.

Zelltemperaturen sind entsprechend der Firmware unsigned: z.B. 40000 = +40 °C.
0xFFFF/0xFFFE sind Temperaturfehler. Zellspannungen 0/0xFFFF sind ungültig.
Die bestehende GUI zeigt 11 Zellen pro Stack. Kanal 12 wird wie in der Firmware
von Zellstatistiken ausgeschlossen; Temperaturkanal 10 ebenfalls von Extrema.
Alle 12 Rohkanäle werden dekodiert. Die Stacksumme umfasst die 11 angezeigten
Zellen und wird nur bei vollständigen Spannungswerten angezeigt.

Die vorliegende Firmware ruft USB_Send_LTC_AllStacks nicht im Sendezyklus auf
und sendet Stackpakete ohne LTC-Anhang. Deshalb bleibt LTC intern zunächst --.
Der Python-Empfang ist für beide LTC-Varianten vorbereitet.
Die Firmware überträgt beim Strom bereits einen Betrag; das Vorzeichen lässt
sich in Python nicht rekonstruieren. Negative Zelltemperaturen sind im uint16-
Milligradformat der Firmware nicht eindeutig darstellbar.

USB-Empfang und Auswertung sind direkt in main.py enthalten. Alternativ zur
Installation per pip können die Abhängigkeiten über das Pipfile installiert werden.
=======
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
>>>>>>> Stashed changes
