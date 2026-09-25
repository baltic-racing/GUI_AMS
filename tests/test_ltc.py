import struct
import unittest
from unittest.mock import patch

from main import FrameDecoder, Telemetry
from Telemetrie_identifier import (
    Device_AMS, ID_LTC_Temperature, ID_LTC_All_Stacks, ID_TS_Stack_Detail,
)


class LTCTests(unittest.TestCase):
    def test_fragmented_frame_and_signed_single_temperature(self):
        frame = bytearray([2, 0, 3, Device_AMS, ID_LTC_Temperature])
        frame.extend(struct.pack('>h', -125))
        checksum = 0
        for byte in frame:
            checksum ^= byte
        frame.append(checksum)
        decoder = FrameDecoder()
        self.assertEqual(decoder.feed(frame[:4]), [])
        packets = decoder.feed(frame[4:])
        self.assertEqual(len(packets), 1)
        telemetry = Telemetry()
        self.assertTrue(telemetry.apply(*packets[0]))
        self.assertEqual(telemetry.summary()['ltc_temperature'], -12.5)
        self.assertTrue(all(s['ltc_temperature'] is None for s in telemetry.stacks))

    def test_invalid_values_lengths_expiry_and_reset(self):
        telemetry = Telemetry()
        with patch('main.time.monotonic', return_value=100):
            self.assertTrue(telemetry.apply(ID_LTC_Temperature, b'\x01\x90'))
            self.assertEqual(telemetry.summary()['ltc_temperature'], 40)
            for payload in (b'', b'\x01', b'\x01\x02\x03'):
                self.assertFalse(telemetry.apply(ID_LTC_Temperature, payload))
                self.assertEqual(telemetry.summary()['ltc_temperature'], 40)
        with patch('main.time.monotonic', return_value=106):
            self.assertIsNone(telemetry.summary()['ltc_temperature'])
        for raw in (-1, -2, 0x7FFF):
            telemetry.apply(ID_LTC_Temperature, struct.pack('>h', raw))
            self.assertIsNone(telemetry.summary()['ltc_temperature'])
        telemetry.reset()
        self.assertIsNone(telemetry.summary()['ltc_temperature'])

    def test_stack_sources_and_independent_freshness(self):
        telemetry = Telemetry()
        stack_payload = bytes([0]) + struct.pack('>24H', *([37000] * 12 + [25000] * 12))
        with patch('main.time.monotonic', return_value=100):
            self.assertTrue(telemetry.apply(ID_LTC_All_Stacks, struct.pack('>12h', *range(200, 212))))
            self.assertEqual(telemetry.stack(11)['ltc_temperature'], 21.1)
            self.assertTrue(telemetry.apply(ID_TS_Stack_Detail, stack_payload + struct.pack('>h', 350)))
            self.assertEqual(telemetry.stack(0)['ltc_temperature'], 35)
        with patch('main.time.monotonic', return_value=104):
            telemetry.apply(ID_TS_Stack_Detail, stack_payload)
            self.assertEqual(telemetry.stack(0)['ltc_temperature'], 35)
        with patch('main.time.monotonic', return_value=106):
            self.assertIsNone(telemetry.stack(0)['ltc_temperature'])
            self.assertFalse(telemetry.stack(0)['stale'])


if __name__ == '__main__':
    unittest.main()
