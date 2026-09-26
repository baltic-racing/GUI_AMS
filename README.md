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
- `0x2D`: einzelne LTC-Temperatur (int16 Big Endian /10 °C), ohne Stackzuordnung.
- `0x90`: LTC-Temperaturen aller 12 Stacks (je int16 Big Endian /10 °C).
- `0x40` mit 51 Byte: Die aktuelle Firmware sendet nach den Grunddaten
  `cfg[stack][4]` und `cfg[stack][5]` als Balancing-Bits. LTC kommt separat über `0x90`.
  Nur für ältere Firmware mit LTC-Anhang muss `STACK_DETAIL_51_FORMAT` in
  `main.py` auf `'ltc'` gesetzt werden. Die beiden Formate sind nicht automatisch unterscheidbar.
- `0x40`: nach dem LTC-Anhang optional 2 Balancing-Bytes (53 Byte Nutzdaten insgesamt):
  Byte 51 = `cfg[stack][4]` (DCC 1–8), Byte 52 = `cfg[stack][5]`
  (untere 4 Bits: DCC 9–12; obere 4 Bits werden ignoriert).

Aktives Balancing färbt die zugehörige Zellkarte orange und zeigt „BALANCING“.
Die bestehende Zellnummerierung bleibt nullbasiert: DCC 1 gehört zur Anzeige
„Zelle 0“. Ohne Balancing-Anhang, nach 5 Sekunden ohne Stackdaten oder nach
Zurücksetzen der Verbindung werden die Markierungen entfernt. Blau allein
bestätigt deshalb keinen ausgeschalteten Balancing-Zustand.

Die Zellkarte unterscheidet ausdrücklich `BALANCING`, `Balancing: aus` und
`Balancing: unbekannt`. Der Stackhinweis meldet bei Paketen ohne Balancing-Anhang
`nicht übertragen` und verweist auf die erforderliche Firmware-Erweiterung.
Die API liefert dafür `balancing_available` (nur bei frischen Paketen mit Balancing-Anhang
wahr) und `stack_payload_bytes` (Länge des letzten akzeptierten Stackpakets).
Nach Änderungen den Python-Server neu starten, erneut verbinden und die
Browserseite mit Strg+F5 neu laden.

### Optionale Firmware-Erweiterung für LTC und Balancing im selben Paket

Für die aktuelle 51-Byte-Firmware ist keine Änderung erforderlich. Die GUI
liest deren Balancing-Bits direkt. Das folgende 53-Byte-Format ermöglicht
zusätzlich die LTC-Temperatur im selben Paket.

Die STM32-Quellen sind nicht in diesem Repository enthalten. In
`USB_Send_StackDetail()` muss der Payload-Puffer 53 Byte groß sein. Nach den
12 Spannungen und 12 Temperaturen (bisher 49 Byte inklusive Stackindex)
werden zuerst die LTC-Temperatur und dann die DCC-Bytes angehängt:

```c
/* Puffer: uint8_t payload[1 + 12 * 2 + 12 * 2 + 2 + 2]; */
/* Hier ist idx == 49. Vorhandenen LTC-Anhang nicht doppelt schreiben. */
uint16_t ltc = (uint16_t)ltcTemps_c10[stack];
payload[idx++] = (uint8_t)(ltc >> 8);
payload[idx++] = (uint8_t)(ltc & 0xFF);
payload[idx++] = cfg[stack][4];
payload[idx++] = cfg[stack][5];
USB_transmit(0x40, payload, idx);
```

Die Variablen müssen aus der Firmware eingebunden werden; bei fehlendem
LTC-Messwert kann `0x7FFF` als ungültige Temperatur übertragen werden.
49- und 51-Byte-Pakete bleiben kompatibel; die Bedeutung der 51-Byte-Pakete
wird explizit mit `STACK_DETAIL_51_FORMAT` festgelegt (Standard: `'balancing'`).

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
Nach einem USB-Fehler wird der gewählte Port jede Sekunde erneut geöffnet.
Manuelles Trennen beendet diese Wiederverbindungsversuche.
Das Lesen läuft mit 100 ms Timeout in einem Hintergrundthread; die API bleibt
währenddessen ansprechbar. Teilpakete werden über mehrere Lesevorgänge gepuffert,
mehrere Pakete in einem USB-Leseblock einzeln geprüft und verarbeitet.
Große Leseblöcke werden nicht als ungeprüfte Stack-Rohdaten interpretiert:
Die Firmware sendet STM-Pakete mit jeweils maximal 64 Byte.
Mit der Umgebungsvariable `TELEMETRY_RAW_DEBUG=1` lassen sich empfangene Bytes
zur Diagnose im Terminal ausgeben. Oberfläche und API-Datenformat bleiben gleich.

Die separate LTC-Temperatur aus `0x2D` steht unter `/ltc_temperature` und oberhalb der Diagramme. Die stackweisen LTC-Werte aus `0x90` und `0x40` erscheinen in den Stackkarten und Stackdetails. Fehlerwerte -1, -2 und 0x7FFF sowie Werte ohne Aktualisierung seit 5 Sekunden erscheinen als --. Ein Stackpaket ohne LTC-Anhang aktualisiert den LTC-Zeitstempel nicht.
