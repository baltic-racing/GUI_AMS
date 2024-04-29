import serial

NUM_STACK = 2
NUM_CELLS_STACK = 12
NUM_CELLS = NUM_STACK * NUM_CELLS_STACK
usb_data_size = NUM_CELLS * 2 + 1

#from fuck import gruesse
var = serial.Serial()
#var.port = "/dev/ttyACM0"
var.port = "COM3"
var.open()

#async def read_data():
    #await asyncio.sleep(5)

while(1):
    #gelesene_bytes = var.read_until(b"\0")
    gelesene_bytes = var.read_until(b"\xff")
    print(bytes(gelesene_bytes))
    if len(gelesene_bytes) != usb_data_size:
        print("Katastrophe")
        continue

    messwerte = [x for x in bytes(gelesene_bytes) if x != 0]
    print(messwerte)

    neue_messwerte = []
    for zahl in gelesene_bytes:
        #print(zahl)
        if zahl != 0:
            neue_messwerte.append(zahl)

    #print(neue_messwerte)
    #gruesse()

    #print("Hello World")

    #for i in range(size):
        #print("Test ", i, ": ", var.readline())



