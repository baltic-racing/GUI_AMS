import serial
var = serial.Serial()
var.port = "ttyACM0"
var.open()
while(1):
    print(var.read(10))

