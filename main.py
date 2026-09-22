<<<<<<< Updated upstream
﻿"""BRT GUI with STM32 USB CDC telemetry."""
import asyncio
import time
from pathlib import Path
import serial
from serial.tools import list_ports
from sanic import Sanic
from sanic.response import file, json
import struct
from functools import reduce
from operator import xor

NUM_STACK = 12
STALE_SECONDS = 5

class FrameDecoder:
    def __init__(self):
        self.reset()

    def reset(self):
        self.buffer = bytearray()
        self.frames = self.checksum_errors = 0

    def feed(self, data):
        self.buffer.extend(data)
        packets = []
        while self.buffer:
            if self.buffer[0] != 2:
                del self.buffer[0]
                continue
            if len(self.buffer) < 4:
                break
            length = self.buffer[2]
            if self.buffer[1] != 0 or self.buffer[3] != 0xA1 or not 1 <= length <= 59:
                del self.buffer[0]
                continue
            size = length + 5
            if len(self.buffer) < size:
                break
            frame = self.buffer[:size]
            if reduce(xor, frame, 0):
                self.checksum_errors += 1
                del self.buffer[0]
                continue
            del self.buffer[:size]
            self.frames += 1
            packets.append((frame[4], bytes(frame[5:-1])))
        return packets


def voltage(raw):
    return None if raw in (0, 0xFFFF) else raw / 10000


def temperature(raw):
    # uint16_t millidegrees in firmware: 40000 means +40 C, not negative!
    return None if raw in (0xFFFF, 0xFFFE) else raw / 1000


def ltc_temperature(data):
    raw = int.from_bytes(data, 'big', signed=True)
    return None if raw in (-1, -2, 0x7FFF) else raw / 10


class Telemetry:
    def __init__(self):
        self.reset()

    def reset(self):
        self.stacks = [dict(voltages=[None]*12, temperatures=[None]*12,
                            ltc_temperature=None, ts=None, ltc_ts=None)
                       for _ in range(NUM_STACK)]
        self.values = {}
        self.last_received = None

    def apply(self, message_id, payload):
        now = time.monotonic()
        if message_id == 0x40:
            if len(payload) not in (49, 51) or payload[0] >= NUM_STACK:
                return False
            stack = self.stacks[payload[0]]
            raw = struct.unpack('>24H', payload[1:49])
            stack.update(voltages=[voltage(v) for v in raw[:12]],
                         temperatures=[temperature(t) for t in raw[12:]], ts=now)
            if len(payload) == 51:
                stack.update(ltc_temperature=ltc_temperature(payload[49:]), ltc_ts=now)
        elif message_id == 0x90:
            if len(payload) != 24:
                return False
            for i, stack in enumerate(self.stacks):
                stack.update(ltc_temperature=ltc_temperature(payload[2*i:2*i+2]), ltc_ts=now)
        elif message_id in (0x21, 0x22, 0x28):
            if len(payload) != 2:
                return False
            raw = int.from_bytes(payload, 'big')
            name, value = {0x21: ('ts_voltage', raw / 100),
                           0x22: ('charging_current', raw / 10),
                           0x28: ('cell_temperature_min', temperature(raw))}[message_id]
            self.values[name] = (value, now)
        else:
            return False
        self.last_received = now
        return True

    def stack(self, index):
        source = self.stacks[index]
        now = time.monotonic()
        fresh = source['ts'] is not None and now - source['ts'] < STALE_SECONDS
        volts = source['voltages'][:] if fresh else [None]*12
        temps = source['temperatures'][:] if fresh else [None]*12
        # Existing GUI has 11 cells; firmware excludes channel 12, and
        # additionally temperature channel 10, from cell extrema.
        vs = [v for v in volts[:11] if v is not None]
        ts = [t for i, t in enumerate(temps[:11]) if t is not None and i != 9]
        ltc_fresh = source['ltc_ts'] is not None and now - source['ltc_ts'] < STALE_SECONDS
        return dict(voltages=volts, temperatures=temps,
                    voltage_min=min(vs, default=None), voltage_max=max(vs, default=None),
                    temperature_min=min(ts, default=None), temperature_max=max(ts, default=None),
                    sum_voltage=round(sum(vs), 4) if len(vs) == 11 else None,
                    ltc_temperature=source['ltc_temperature'] if ltc_fresh else None,
                    stale=not fresh)

    def summary(self):
        now = time.monotonic()
        result = {name: self.values[name][0] if name in self.values and
                  now - self.values[name][1] < STALE_SECONDS else None
                  for name in ('ts_voltage', 'charging_current')}
        stacks = [self.stack(i) for i in range(NUM_STACK)]
        for name in ('voltage_min', 'voltage_max', 'temperature_min', 'temperature_max'):
            values = [s[name] for s in stacks if s[name] is not None]
            result['cell_' + name] = (min(values) if name.endswith('min') else max(values)) if values else None
        if result['cell_temperature_min'] is None:
            value, ts = self.values.get('cell_temperature_min', (None, 0))
            if now - ts < STALE_SECONDS:
                result['cell_temperature_min'] = value
        return result

app = Sanic('BRT_GUI')
BASE = Path(__file__).resolve().parent
telemetry = Telemetry()
decoder = FrameDecoder()
connection = None
connection_error = None

@app.post('/connection')
async def init_connection(request):
    global connection, connection_error
    if connection is not None:
=======
﻿"""BRT GUI: USB-Protokoll aus usb_control.c und usb_measurements.c."""
import asyncio
import struct
import time
from functools import reduce
from operator import xor
from pathlib import Path

import serial
from sanic import Sanic
from sanic.log import logger
from sanic.response import file, json


app = Sanic('BRT_GUI')
BASE = Path(__file__).resolve().parent
NUM_STACK = 12
NUM_CELLS_STACK = 12
ACTIVE_CELLS = 11  # Firmware nimmt Kanal 12 von den Zellstatistiken aus.
STALE_SECONDS = 5
serial_connection = None
receive_buffer = bytearray()
connection_error = None
frames_received = 0
checksum_errors = 0
last_received = None
stacks = []
scalar_values = {}


def reset_measurements():
    global stacks, last_received, frames_received, checksum_errors
    stacks = [dict(voltages=[None]*12, temperatures=[None]*12,
                   ltc_temperature=None, updated=None, ltc_updated=None)
              for _ in range(NUM_STACK)]
    scalar_values.clear()
    receive_buffer.clear()
    last_received = None
    frames_received = checksum_errors = 0


reset_measurements()


def decode_frames(data):
    """[02][00][LEN][A1][ID][DATA...][XOR]; LEN = ID + DATA."""
    global frames_received, checksum_errors
    receive_buffer.extend(data)
    packets = []
    while receive_buffer:
        if receive_buffer[0] != 2:
            del receive_buffer[0]
            continue
        if len(receive_buffer) < 4:
            break
        length = receive_buffer[2]
        if receive_buffer[1] != 0 or receive_buffer[3] != 0xA1 or not 1 <= length <= 59:
            del receive_buffer[0]
            continue
        size = length + 5
        if len(receive_buffer) < size:
            break
        frame = receive_buffer[:size]
        if reduce(xor, frame, 0):
            checksum_errors += 1
            del receive_buffer[0]
            continue
        del receive_buffer[:size]
        frames_received += 1
        packets.append((frame[4], bytes(frame[5:-1])))
    return packets


def decode_temperature(raw):
    # uint16_t Milligrad! 40000 ist +40 Grad, nicht signed int16.
    return None if raw in (0xFFFF, 0xFFFE) else raw / 1000


def decode_ltc(payload):
    raw = int.from_bytes(payload, 'big', signed=True)
    return None if raw in (-1, -2, 0x7FFF) else raw / 10


def apply_measurement(message_id, payload):
    global last_received
    now = time.monotonic()
    if message_id == 0x40:
        if len(payload) not in (49, 51) or payload[0] >= NUM_STACK:
            return False
        values = struct.unpack('>24H', payload[1:49])
        stack = stacks[payload[0]]
        stack.update(voltages=[None if v in (0, 0xFFFF) else v / 10000 for v in values[:12]],
                     temperatures=[decode_temperature(t) for t in values[12:]], updated=now)
        if len(payload) == 51:
            stack.update(ltc_temperature=decode_ltc(payload[49:]), ltc_updated=now)
    elif message_id == 0x90:
        if len(payload) != NUM_STACK * 2:
            return False
        for i, stack in enumerate(stacks):
            stack.update(ltc_temperature=decode_ltc(payload[2*i:2*i+2]), ltc_updated=now)
    elif message_id in (0x21, 0x22, 0x28):
        if len(payload) != 2:
            return False
        raw = int.from_bytes(payload, 'big')
        name, value = {0x21: ('ts_voltage', raw / 100),
                       0x22: ('charging_current', raw / 10),
                       0x28: ('cell_temperature_min', decode_temperature(raw))}[message_id]
        scalar_values[name] = (value, now)
    else:
        return False
    last_received = now
    return True


def is_fresh(timestamp):
    return timestamp is not None and time.monotonic() - timestamp < STALE_SECONDS


def stack_snapshot(index):
    source = stacks[index]
    fresh = is_fresh(source['updated'])
    voltages = source['voltages'][:] if fresh else [None]*12
    temperatures = source['temperatures'][:] if fresh else [None]*12
    vs = [v for v in voltages[:ACTIVE_CELLS] if v is not None]
    # Wie bms.c: Temperaturkanal 10 und 12 nicht für Extrema verwenden.
    ts = [t for i, t in enumerate(temperatures[:ACTIVE_CELLS]) if t is not None and i != 9]
    return dict(voltages=voltages, temperatures=temperatures,
                voltage_min=min(vs, default=None), voltage_max=max(vs, default=None),
                temperature_min=min(ts, default=None), temperature_max=max(ts, default=None),
                sum_voltage=round(sum(vs), 4) if len(vs) == ACTIVE_CELLS else None,
                ltc_temperature=source['ltc_temperature'] if is_fresh(source['ltc_updated']) else None,
                stale=not fresh)


def scalar_value(name):
    value, timestamp = scalar_values.get(name, (None, None))
    return value if is_fresh(timestamp) else None


def measurement_value(name):
    if name in ('charging_current', 'ts_voltage'):
        return scalar_value(name)
    field = name.removeprefix('cell_')
    values = [s[field] for s in map(stack_snapshot, range(NUM_STACK)) if s[field] is not None]
    if values:
        return min(values) if name.endswith('min') else max(values)
    return scalar_value(name)


def close_connection():
    global serial_connection
    interface, serial_connection = serial_connection, None
    if interface is not None:
        try:
            interface.close()
        except (serial.SerialException, OSError) as exc:
            logger.warning('USB-Port konnte nicht geschlossen werden: %s', exc)
    reset_measurements()


@app.post('/connection')
async def init_connection(request):
    global serial_connection, connection_error
    if serial_connection is not None:
>>>>>>> Stashed changes
        return json({'error': 'Verbindung ist bereits aufgebaut'}, status=409)
    data = request.json
    if not isinstance(data, dict) or not isinstance(data.get('port'), str) or not data['port'].strip():
        return json({'error': 'Bitte einen COM-Port angeben.'}, status=400)
    try:
<<<<<<< Updated upstream
        connection = serial.Serial(port=data['port'].strip(),
                                   baudrate=int(data.get('baudrate', 115200)), timeout=0)
    except (serial.SerialException, OSError, ValueError, TypeError) as exc:
        connection_error = str(exc)
        return json({'error': connection_error}, status=400)
    telemetry.reset()
    decoder.reset()
=======
        serial_connection = serial.Serial(port=data['port'].strip(),
                                          baudrate=int(data.get('baudrate', 115200)), timeout=0)
    except (serial.SerialException, OSError, ValueError, TypeError) as exc:
        connection_error = str(exc)
        return json({'error': connection_error}, status=400)
    reset_measurements()
>>>>>>> Stashed changes
    connection_error = None
    return json({'msg': 'Verbindung aufgebaut'})


<<<<<<< Updated upstream
def close_connection():
    global connection
    previous, connection = connection, None
    if previous is not None:
        try:
            previous.close()
        except (serial.SerialException, OSError):
            pass
    decoder.reset()
    telemetry.reset()

=======
>>>>>>> Stashed changes
@app.delete('/connection')
async def destroy_connection(request):
    close_connection()
    return json({'msg': 'Verbindung getrennt'})
<<<<<<< Updated upstream

@app.get('/connection')
async def get_connection_info(request):
    age = None if telemetry.last_received is None else time.monotonic() - telemetry.last_received
    return json(dict(connected=connection is not None,
                     connected_port=connection.port if connection else None,
                     receiving=age is not None and age < 5,
                     last_data_age_s=age, error=connection_error,
                     frames=decoder.frames, checksum_errors=decoder.checksum_errors))
=======
>>>>>>> Stashed changes

@app.get('/ports')
async def get_ports(request):
    return json({'ports': [dict(port=p.device, description=p.description) for p in list_ports.comports()]})

<<<<<<< Updated upstream
@app.get('/stack/count')
async def get_stack_count(request):
    return json({'stacks': NUM_STACK})

@app.get('/stack/detailed/<stack_num:int>', name='stack_detail')
@app.get('/stack/<stack_num:int>', name='stack_summary')
async def stack_info(request, stack_num):
    if not 0 <= stack_num < NUM_STACK:
        return json({'error': 'Unbekannter Stack'}, status=404)
    return json(telemetry.stack(stack_num))
=======
@app.get('/connection')
async def get_connection_info(request):
    return json(dict(connected=serial_connection is not None,
                     connected_port=serial_connection.port if serial_connection else '--',
                     receiving=is_fresh(last_received), error=connection_error,
                     frames=frames_received, checksum_errors=checksum_errors))
>>>>>>> Stashed changes

@app.get('/charging_current', name='charging_current')
@app.get('/cell_temperature_max', name='cell_temperature_max')
@app.get('/cell_temperature_min', name='cell_temperature_min')
@app.get('/cell_voltage_max', name='cell_voltage_max')
@app.get('/cell_voltage_min', name='cell_voltage_min')
@app.get('/ts_voltage', name='ts_voltage')
async def measurement(request):
    name = request.path.strip('/')
    return json({name: telemetry.summary()[name]})

<<<<<<< Updated upstream
@app.get('/')
async def index(request):
    return await file(BASE / 'main.html')
=======
@app.get('/stack/count')
async def get_stack_count(request):
    return json({'stacks': NUM_STACK})


@app.get('/stack/detailed/<stack_num:int>', name='stack_detail')
@app.get('/stack/<stack_num:int>', name='stack_summary')
async def stack_info(request, stack_num):
    if not 0 <= stack_num < NUM_STACK:
        return json({'error': 'Unbekannter Stack'}, status=404)
    return json(stack_snapshot(stack_num))


@app.get('/charging_current', name='charging_current')
@app.get('/cell_temperature_max', name='cell_temperature_max')
@app.get('/cell_temperature_min', name='cell_temperature_min')
@app.get('/cell_voltage_max', name='cell_voltage_max')
@app.get('/cell_voltage_min', name='cell_voltage_min')
@app.get('/ts_voltage', name='ts_voltage')
async def measurement(request):
    name = request.path.strip('/')
    return json({name: measurement_value(name)})


@app.get('/')
async def index(request):
    return await file(BASE / 'main.html')


for url, filename in [('/styles.css', 'beer.min.css'),
                      ('/Accumulator.html', 'Accumulator.html'),
                      ('/Telemetrie.html', 'Telemetrie.html'),
                      ('/BRT_logo_schrift.png', 'BRT_logo_schrift.png')]:
    app.static(url, str(BASE / filename), name='asset_' + filename.replace('.', '_'))
>>>>>>> Stashed changes

# Explicit assets avoid exposing Python source and repository files.
for url, filename in [('/styles.css', 'beer.min.css'),
                      ('/Accumulator.html', 'Accumulator.html'),
                      ('/Telemetrie.html', 'Telemetrie.html'),
                      ('/connection.js', 'connection.js'),
                      ('/BRT_logo_schrift.png', 'BRT_logo_schrift.png')]:
    app.static(url, str(BASE / filename), name='asset_' + filename.replace('.', '_'))

async def data_task():
    global connection_error
    while True:
<<<<<<< Updated upstream
        if connection is not None:
            try:
                incoming = connection.read(min(connection.in_waiting, 8192))
                for message_id, payload in decoder.feed(incoming):
                    telemetry.apply(message_id, payload)
            except (serial.SerialException, OSError) as exc:
                connection_error = str(exc)
                close_connection()
        await asyncio.sleep(0.01)

@app.before_server_start
async def start_reader(app):
    app.add_task(data_task())

@app.after_server_stop
async def stop_reader(app):
    close_connection()

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8081, single_process=True)
=======
        if serial_connection is not None:
            try:
                incoming = serial_connection.read(min(serial_connection.in_waiting, 8192))
                for message_id, payload in decode_frames(incoming):
                    apply_measurement(message_id, payload)
            except (serial.SerialException, OSError) as exc:
                connection_error = str(exc)
                logger.warning('USB-Verbindung unterbrochen: %s', exc)
                close_connection()
        await asyncio.sleep(0.01)


@app.before_server_start
async def start_reader(app):
    app.add_task(data_task())


@app.after_server_stop
async def cleanup_serial(app):
    close_connection()


if __name__ == '__main__':
    app.run('0.0.0.0', 8081, single_process=True)
>>>>>>> Stashed changes
