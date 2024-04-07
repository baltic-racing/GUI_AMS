import serial
var = serial.Serial()
var.port = "/dev/ttyACM0"
var.open()
while(1):
    print(var.readline())

