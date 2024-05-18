import serial
import asyncio

NUM_STACK = 12



NUM_CELLS_STACK = 12
NUM_CELLS = NUM_STACK * NUM_CELLS_STACK
usb_data_size = NUM_CELLS * 2 + 1

from pathlib import Path
from sanic import Sanic, Request
from sanic.response import json, html


app = Sanic("MyHelloWorldApp")

#stack_voltages_max = [1, 2, 3, 4, 5, 6, 7, 8]
#stack_temperatures_max = [1.1, 2.2, 3.3, 4.4, 5.5, 6.6, 7.7, 8.8]

#stack_voltages_min = [0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5]
#stack_temperatures_min = [1, 2, 3, 4, 5, 6, 7, 8]

#detailed_stack_info_voltage = [x for x in range(144)]
#detailed_stack_info_temperature = [x for x in range(144)]

stack_voltages_max = [x for x in bytes(NUM_STACK)]
stack_temperatures_max = [x for x in bytes(NUM_STACK)]

stack_voltages_min = [x for x in bytes(NUM_STACK)]
stack_temperatures_min = [x for x in bytes(NUM_STACK)]

detailed_stack_info_voltage = [x for x in bytes(NUM_CELLS)]
detailed_stack_info_temperature = [x for x in bytes(NUM_CELLS)]

sum_voltage = [x for x in bytes(NUM_STACK)]

@app.get("/styles.css")
async def style(request):
    return html(Path("./beer.min.css").read_text())


@app.get("/")
async def hello_world(request):
    return html(Path("./main.html").read_text())


@app.get("/stack/detailed/<stack_num:int>")
async def stack_info_detail(request: Request, stack_num: int):
    #print(detailed_stack_info_voltage)
    #print(detailed_stack_info_temperature)
    offset = stack_num * 12

    cell_voltages = detailed_stack_info_voltage[offset : offset + 12]
    cell_temperatures = detailed_stack_info_temperature[offset : offset + 12]

    return json({"voltages": cell_voltages, "temperatures": cell_temperatures})


@app.get("/stack/<stack_num:int>")
async def stack_info(request: Request, stack_num: int):
    #print(stack_voltages_max)
    try:
        return json(
            {
                "voltage_max": stack_voltages_max[stack_num],
                "temperature_max": stack_temperatures_max[stack_num],
                "voltage_min": stack_voltages_min[stack_num],
                "temperature_min": stack_temperatures_min[stack_num],
                "sum_voltage": sum_voltage[stack_num],
            }
        )
    except:
        return json(
            {
                "voltage_max": "unbekannt",
                "temperature_max": "unbekannt",
                "voltage_min": "unbekannt",
                "temperature_min": "unbekannt",
                "sum_voltage": "unbekannt",
            }
        )


def get_data(serial_interface):
    gelesene_bytes = serial_interface.read_until(b"\xff")
    #messwerte = [x for x in bytes(gelesene_bytes) if x != 0]
    messwerte = [x for x in bytes(gelesene_bytes)]
    return messwerte

async def data_task():
    #global stack_voltages_max
    global detailed_stack_info_voltage
    global detailed_stack_info_temperature
    global sum_voltage

    # test = "lol"
    var = serial.Serial()
    #var.port = "/dev/ttyACM0"
    var.port = "COM3"
    var.open()
    while True:
        messwerte = await asyncio.get_event_loop().run_in_executor(None, get_data, var)
        #stack_voltages_max = messwerte
        #print("wtf:", messwerte)
        detailed_stack_info_voltage = [messwerte[x] for x in range(NUM_CELLS)]
        #print("dafuq:", detailed_stack_info_voltage)
        detailed_stack_info_temperature = [messwerte[x + NUM_CELLS] for x in range(NUM_CELLS)]
        #print("Temp: ",detailed_stack_info_temperature)
        #stack_voltages_max =  max(detailed_stack_info_voltage[12:24])
        for i in range(0 , NUM_CELLS, 12):
            max_value_voltage = max(detailed_stack_info_voltage[i:i + NUM_CELLS_STACK])
            stack_voltages_max[i // 12] = max_value_voltage/10

            min_value_voltage = min(detailed_stack_info_voltage[i:i + NUM_CELLS_STACK - 1])
            stack_voltages_min[i // 12] = min_value_voltage/10

            max_value_temperature = max(detailed_stack_info_temperature[i:i + NUM_CELLS_STACK])
            stack_temperatures_max[i // 12] = max_value_temperature

            min_value_temperature = min(detailed_stack_info_temperature[i:i + NUM_CELLS_STACK - 1])
            stack_temperatures_min[i // 12] = min_value_temperature

            sum_stack_voltage = sum(detailed_stack_info_voltage[i:i + NUM_CELLS_STACK])
            sum_voltage[i // 12] = sum_stack_voltage/10

        #print("max :", stack_voltages_max)
        #print("min :", stack_voltages_min)
        #print("test: ", sum_voltage)


app.add_task(data_task)

if __name__ == "__main__":
    app.run("0.0.0.0", 8080, workers=1)
