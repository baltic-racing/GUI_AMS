# from tkinter import *
# from tkinter import ttk


# test = "lol"

# root = Tk()
# frm = ttk.Frame(root, padding=200)
# frm.grid()

# ttk.Label(frm, text="Hello World!").grid(column=0, row=0)
# ttk.Button(frm, text="Quit", command=root.destroy).grid(column=1, row=0)
# ttk.Label(frm, text="Test").grid(column=1, row=1)
# root.mainloop()

from pathlib import Path
from sanic import Sanic, Request
from sanic.response import json, html

app = Sanic("MyHelloWorldApp")

stack_voltages_max = [1, 2, 3, 4, 5, 6, 7, 8]
stack_temperatures_max = [1.1, 2.2, 3.3, 4.4, 5.5, 6.6, 7.7, 8.8]

stack_voltages_min = [0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5]
stack_temperatures_min = [1, 2, 3, 4, 5, 6, 7, 8]

detailed_stack_info_voltage = [x for x in range(144)]
detailed_stack_info_temperature = [x for x in range(144)]



@app.get("/styles.css")
async def style(request):
    return html(Path("./beer.min.css").read_text())


@app.get("/")
async def hello_world(request):
    return html(Path("./main.html").read_text())


@app.get("/stack/detailed/<stack_num:int>")
async def stack_info_detail(request: Request, stack_num: int):
    offset = stack_num * 12

    cell_voltages = detailed_stack_info_voltage[offset : offset + 12]
    cell_temperatures = detailed_stack_info_temperature[offset : offset + 12]

    return json({"voltages": cell_voltages, "temperatures": cell_temperatures})


@app.get("/stack/<stack_num:int>")
async def stack_info(request: Request, stack_num: int):
    try:
        return json(
            {
                "voltage_max": stack_voltages_max[stack_num],
                "temperature_max": stack_temperatures_max[stack_num],
                "voltage_min": stack_voltages_min[stack_num],
                "temperature_min": stack_temperatures_min[stack_num],
            }
        )
    except:
        return json(
            {
                "voltage_max": "unbekannt",
                "temperature_max": "unbekannt",
                "voltage_min": "unbekannt",
                "temperature_min": "unbekannt",
            }
        )


if __name__ == "__main__":
    app.run("0.0.0.0", 8080, workers=1)
