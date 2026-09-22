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
        return json({'error': 'Verbindung ist bereits aufgebaut'}, status=409)
    data = request.json
    if not isinstance(data, dict) or not isinstance(data.get('port'), str) or not data['port'].strip():
        return json({'error': 'Bitte einen COM-Port angeben.'}, status=400)
    try:
        connection = serial.Serial(port=data['port'].strip(),
                                   baudrate=int(data.get('baudrate', 115200)), timeout=0)
    except (serial.SerialException, OSError, ValueError, TypeError) as exc:
        connection_error = str(exc)
        return json({'error': connection_error}, status=400)
    telemetry.reset()
    decoder.reset()
    connection_error = None
    return json({'msg': 'Verbindung aufgebaut'})


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

@app.delete('/connection')
async def destroy_connection(request):
    close_connection()
    return json({'msg': 'Verbindung getrennt'})

@app.get('/connection')
async def get_connection_info(request):
    age = None if telemetry.last_received is None else time.monotonic() - telemetry.last_received
    return json(dict(connected=connection is not None,
                     connected_port=connection.port if connection else None,
                     receiving=age is not None and age < 5,
                     last_data_age_s=age, error=connection_error,
                     frames=decoder.frames, checksum_errors=decoder.checksum_errors))

@app.get('/ports')
async def get_ports(request):
    return json({'ports': [dict(port=p.device, description=p.description) for p in list_ports.comports()]})

@app.get('/stack/count')
async def get_stack_count(request):
    return json({'stacks': NUM_STACK})

@app.get('/stack/detailed/<stack_num:int>', name='stack_detail')
@app.get('/stack/<stack_num:int>', name='stack_summary')
async def stack_info(request, stack_num):
    if not 0 <= stack_num < NUM_STACK:
        return json({'error': 'Unbekannter Stack'}, status=404)
    return json(telemetry.stack(stack_num))

@app.get('/charging_current', name='charging_current')
@app.get('/cell_temperature_max', name='cell_temperature_max')
@app.get('/cell_temperature_min', name='cell_temperature_min')
@app.get('/cell_voltage_max', name='cell_voltage_max')
@app.get('/cell_voltage_min', name='cell_voltage_min')
@app.get('/ts_voltage', name='ts_voltage')
async def measurement(request):
    name = request.path.strip('/')
    return json({name: telemetry.summary()[name]})

@app.get('/')
async def index(request):
    return await file(BASE / 'main.html')

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
