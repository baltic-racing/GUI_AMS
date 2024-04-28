import serial

from fuck import gruesse
var = serial.Serial()
#var.port = "/dev/ttyACM0"
var.port = "COM3"
var.open()

size = 18

while(1):
    gelesene_bytes = var.read_until(b"\0")
    print(bytes(gelesene_bytes))
    if len(gelesene_bytes) != 12:
        print("Katastrophe")
        continue

    messwerte = [x for x in bytes(gelesene_bytes) if x != 0]
    print(messwerte)

    neue_messwerte = []
    for zahl in gelesene_bytes:
        #print(zahl)
        if zahl != 0:
            neue_messwerte.append(zahl)

    print(neue_messwerte)
    gruesse()

    #print("Hello World")

    #for i in range(size):
        #print("Test ", i, ": ", var.readline())

