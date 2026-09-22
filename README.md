# GUI_AMS

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
