import struct
import unittest
from unittest.mock import patch

from main import FrameDecoder, Telemetry
from Telemetrie_identifier import (
    Device_AMS, ID_LTC_Temperature, ID_LTC_All_Stacks, ID_TS_Stack_Detail,
)


class LTCTests(unittest.TestCase):
    def test_balancing_channels_and_ltc_in_extended_frame(self):
        base = bytes([2]) + struct.pack('>24H', *([37000]*12 + [25000]*12))
        telemetry = Telemetry()
        for channel in range(12):
            mask = 1 << channel
            payload = base + struct.pack('>h', -125) + bytes([mask & 255, (mask >> 8) | 0xF0])
            frame = bytearray([2, 0, len(payload) + 1, Device_AMS, ID_TS_Stack_Detail]) + payload
            checksum = 0
            for byte in frame:
                checksum ^= byte
            frame.append(checksum)
            packets = FrameDecoder().feed(frame)
            self.assertEqual(len(packets), 1)
            self.assertTrue(telemetry.apply(*packets[0]))
            self.assertEqual(telemetry.stack(2)['balancing'], [i == channel for i in range(12)])
            self.assertEqual(telemetry.stack(2)['ltc_temperature'], -12.5)
            self.assertTrue(telemetry.stack(2)['balancing_available'])
            self.assertEqual(telemetry.stack(2)['stack_payload_bytes'], 53)
            self.assertFalse(any(telemetry.stack(0)['balancing']))

    def test_balancing_clears_on_legacy_packets_expiry_and_reset(self):
        base = bytes([0]) + struct.pack('>24H', *([37000]*12 + [25000]*12))
        active = base + struct.pack('>h', 350) + b'\xff\x0f'
        telemetry = Telemetry()
        with patch('main.time.monotonic', return_value=100):
            for legacy in (base,):
                telemetry.apply(ID_TS_Stack_Detail, active)
                self.assertTrue(all(telemetry.stack(0)['balancing']))
                telemetry.apply(ID_TS_Stack_Detail, legacy)
                self.assertFalse(any(telemetry.stack(0)['balancing']))
                self.assertFalse(telemetry.stack(0)['balancing_available'])
                self.assertEqual(telemetry.stack(0)['stack_payload_bytes'], len(legacy))
            telemetry.apply(ID_TS_Stack_Detail, active)
            self.assertFalse(telemetry.apply(ID_TS_Stack_Detail, active[:-1]))
            self.assertTrue(all(telemetry.stack(0)['balancing']))
        with patch('main.time.monotonic', return_value=105):
            self.assertFalse(any(telemetry.stack(0)['balancing']))
            self.assertFalse(telemetry.stack(0)['balancing_available'])
        telemetry.reset()
        self.assertFalse(any(telemetry.stack(0)['balancing']))
        self.assertFalse(telemetry.stack(0)['balancing_available'])
        self.assertIsNone(telemetry.stack(0)['stack_payload_bytes'])

    def test_received_zero_mask_is_known_inactive(self):
        telemetry = Telemetry()
        payload = bytes([0]) + struct.pack('>24H', *([37000]*12 + [25000]*12))
        telemetry.apply(ID_TS_Stack_Detail, payload + b'\x01\x90\x00\xf0')
        self.assertTrue(telemetry.stack(0)['balancing_available'])
        self.assertFalse(any(telemetry.stack(0)['balancing']))

    def test_current_firmware_51_byte_balancing_keeps_separate_ltc(self):
        telemetry = Telemetry()
        telemetry.apply(ID_LTC_All_Stacks, struct.pack('>12h', *([350]*12)))
        base = bytes([0]) + struct.pack('>24H', *([37000]*12 + [25000]*12))
        telemetry.apply(ID_TS_Stack_Detail, base + b'\x0a\xf5')
        self.assertEqual(telemetry.stack(0)['balancing'], [i in (1, 3, 8, 10) for i in range(12)])
        self.assertTrue(telemetry.stack(0)['balancing_available'])
        self.assertEqual(telemetry.stack(0)['ltc_temperature'], 35)
        telemetry.apply(ID_TS_Stack_Detail, base + b'\x00\x00')
        self.assertFalse(any(telemetry.stack(0)['balancing']))

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

    @patch('main.STACK_DETAIL_51_FORMAT', 'ltc')
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
