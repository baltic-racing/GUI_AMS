import serial
import asyncio
from pathlib import Path
from sanic import Sanic, Request
from sanic.response import json, html
from typing import Optional

app = Sanic("MyHelloWorldApp")

#globale Defines
NUM_STACK = 1
NUM_CELLS_STACK = 12
NUM_CELLS = NUM_STACK * NUM_CELLS_STACK
usb_data_size = NUM_CELLS * 2 + 1

# globale Status Variablen
connected = False
connected_port = "?"
serial_connection: Optional[serial.Serial] = None

stack_voltages_max = [x for x in bytes(NUM_STACK)]
stack_temperatures_max = [x for x in bytes(NUM_STACK)]

stack_voltages_min = [x for x in bytes(NUM_STACK)]
stack_temperatures_min = [x for x in bytes(NUM_STACK)]

detailed_stack_info_voltage = [x for x in bytes(NUM_CELLS)]
detailed_stack_info_temperature = [x for x in bytes(NUM_CELLS)]

sum_voltage = [x for x in bytes(NUM_STACK)]


@app.post("/connection")
async def init_connection(request:Request):
    global serial_connection
    global connected_port
    global connected
    if connected:
        return json({"error": "Verbindung ist bereits aufgebaut"},400)
    try:
        json_data:dict = request.json
        if json_data.get("baudrate",None) is None:
            json_data["baudrate"] = 9600
        if json_data.get("bytesize",None) is None:
            json_data["bytesize"] = 8
        if json_data.get("port", None) is None:
            return json({"error":"kein Port angegeben"},400)
        serial_connection = serial.Serial(**json_data)
        #serial_connection.open()
        connected_port = json_data["port"]
    except serial.SerialException as err:
        serial_connection = None
        return json({"error": f"SerialException: {str(err)}"})
    except Exception as err:
        serial_connection = None
        return json({"error":f"{type(err)} - {str(err)}"})
    
    connected = True
    return json({"msg":"Verbindung aufgebaut"})

@app.delete("/connection")
async def destroy_connection(request:Request):
    global connected
    global serial_connection

    if not connected:
        return json({"error":"Es ist keine Verbindung aufgebaut!"})
    
    serial_connection.close()
    serial_connection = None
    connected = False
    return json({"msg":"Verbindung getrennt"})

@app.get("/connection")
async def get_connection_info(request:Request):
    global connected
    global connected_port

    return json({"connected":connected, "connected_port":connected_port})


@app.get("/styles.css")
async def style(request:Request):
    return html(Path("./beer.min.css").read_text())


@app.get("/")
async def hello_world(request):
    return html(Path("./main.html").read_text())


@app.get("/stack/count")
async def get_stack_count(request: Request):
    return json({"stacks": NUM_STACK})


@app.get("/stack/detailed/<stack_num:int>")
async def stack_info_detail(request: Request, stack_num: int):
    # print(detailed_stack_info_voltage)
    # print(detailed_stack_info_temperature)
    offset = stack_num * 12

    cell_voltages = detailed_stack_info_voltage[offset : offset + 12]
    cell_temperatures = detailed_stack_info_temperature[offset : offset + 12]

    return json({"voltages": cell_voltages, "temperatures": cell_temperatures})


@app.get("/stack/<stack_num:int>")
async def stack_info(request: Request, stack_num: int):
    # print(stack_voltages_max)
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
    # messwerte = [x for x in bytes(gelesene_bytes) if x != 0]
    messwerte = [x for x in bytes(gelesene_bytes)]
    #print(gelesene_bytes)
    return messwerte


async def data_task():
    global stack_voltages_max
    global stack_voltages_min
    global detailed_stack_info_voltage
    global detailed_stack_info_temperature
    global sum_voltage
    global connected
    global serial_connection

    while True:
        if connected:
            messwerte_future = asyncio.get_event_loop().run_in_executor(
                None, get_data, serial_connection
            )
            try:
                messwerte = await asyncio.wait_for(messwerte_future, 5)
            except asyncio.TimeoutError:
                connected = False
                serial_connection = None
                continue

            try:
                # stack_voltages_max = messwerte
                #print("wtf:", messwerte)
                detailed_stack_info_voltage = [messwerte[x] for x in range(NUM_CELLS)]
                # print("dafuq:", detailed_stack_info_voltage)
                detailed_stack_info_temperature = [
                    messwerte[x + NUM_CELLS] for x in range(NUM_CELLS)
                ]
                # print("Temp: ",detailed_stack_info_temperature)
                # stack_voltages_max =  max(detailed_stack_info_voltage[12:24])
                for i in range(0, NUM_CELLS, 12):
                    max_value_voltage = max(
                        detailed_stack_info_voltage[i : i + NUM_CELLS_STACK]
                    )
                    stack_voltages_max[i // 12] = max_value_voltage / 10

                    min_value_voltage = min(
                        detailed_stack_info_voltage[i : i + NUM_CELLS_STACK - 1]
                    )
                    stack_voltages_min[i // 12] = min_value_voltage / 10

                    max_value_temperature = max(
                        detailed_stack_info_temperature[i : i + NUM_CELLS_STACK]
                    )
                    stack_temperatures_max[i // 12] = max_value_temperature

                    min_value_temperature = min(
                        detailed_stack_info_temperature[i : i + NUM_CELLS_STACK - 1]
                    )
                    stack_temperatures_min[i // 12] = min_value_temperature

                    sum_stack_voltage = sum(
                        detailed_stack_info_voltage[i : i + NUM_CELLS_STACK]
                    )
                    sum_voltage[i // 12] = sum_stack_voltage / 10
            except Exception as exc:
                print(exc)
                connected = False
                serial_connection = None
                sum_voltage = [0 for i in range(NUM_STACK)]
                detailed_stack_info_voltage = [0 for i in range(NUM_STACK*NUM_CELLS)]
                detailed_stack_info_temperature = [0 for i in range(NUM_STACK*NUM_CELLS)]
                stack_voltages_max = [0 for x in range(NUM_STACK)]
                stack_voltages_min = [0 for x in range(NUM_STACK)]
                max_value_voltage = [0 for i in range(NUM_STACK)]
                max_value_temperature = [0 for i in range(NUM_STACK)]
        else:
            await asyncio.sleep(2)

app.add_task(data_task)

if __name__ == "__main__":
    app.run("0.0.0.0", 8080, workers=1)
