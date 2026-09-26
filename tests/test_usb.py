import asyncio
import unittest
from functools import reduce
from operator import xor
from unittest.mock import Mock, patch

import main


def frame(payload=b'\x01\x90'):
    packet = bytes([2, 0, len(payload) + 1, 0xA1, 0x2D]) + payload
    return packet + bytes([reduce(xor, packet, 0)])


class DecoderTests(unittest.TestCase):
    def test_every_split_and_multiple_packets_in_large_read(self):
        packet = frame()
        for split in range(1, len(packet)):
            decoder = main.FrameDecoder()
            self.assertEqual(decoder.feed(packet[:split]), [])
            self.assertEqual(decoder.feed(packet[split:]), [(0x2D, b'\x01\x90')])
        decoder = main.FrameDecoder()
        self.assertEqual(len(decoder.feed(packet * 100)), 100)
        self.assertEqual(decoder.buffer, b'')

    def test_noise_invalid_header_and_checksum_recovery(self):
        bad = frame()[:-1] + b'\xff'
        decoder = main.FrameDecoder()
        packets = decoder.feed(b'noise\x02\x00\xff\xa1' + bad + frame())
        self.assertEqual(packets, [(0x2D, b'\x01\x90')])
        self.assertEqual(decoder.checksum_errors, 1)

    def test_read_waits_for_one_byte_or_drains_available_data(self):
        port = Mock(in_waiting=0)
        main.read_serial(port)
        port.read.assert_called_once_with(1)
        port.in_waiting = 512
        main.read_serial(port)
        port.read.assert_called_with(512)


class ReaderTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        main.close_connection()
        main.connection_error = None
        main.retry_at = 0

    async def asyncTearDown(self):
        main.close_connection()

    async def test_usb_error_reconnects_same_port_and_resets_partial_frame(self):
        old = Mock()
        new = Mock()
        main.connection = old
        main.connection_settings = dict(port='COM7', baudrate=115200, timeout=0.1)
        main.decoder.feed(frame()[:4])
        sleeps = []

        async def worker(function, *args, **kwargs):
            if function is main.serial.Serial:
                self.assertEqual(kwargs['port'], 'COM7')
                return new
            if args[0] is old:
                raise main.serial.SerialException('USB removed')
            return frame()

        async def pause(delay):
            sleeps.append(delay)
            if len(sleeps) == 1:
                self.assertIsNone(main.connection)
                self.assertEqual(main.decoder.buffer, b'')
                main.retry_at = 0
            else:
                raise asyncio.CancelledError

        with patch('main.asyncio.to_thread', side_effect=worker), patch('main.asyncio.sleep', side_effect=pause):
            with self.assertRaises(asyncio.CancelledError):
                await main.data_task()
        old.close.assert_called_once()
        self.assertIs(main.connection, new)
        self.assertIsNone(main.connection_error)
        self.assertEqual(main.telemetry.summary()['ltc_temperature'], 40)

    async def test_disconnect_during_read_discards_old_data_and_stops_retry(self):
        main.connection = Mock()
        main.connection_settings = dict(port='COM7')

        async def worker(*args, **kwargs):
            main.close_connection()
            return frame()

        async def pause(delay):
            raise asyncio.CancelledError

        with patch('main.asyncio.to_thread', side_effect=worker), patch('main.asyncio.sleep', side_effect=pause):
            with self.assertRaises(asyncio.CancelledError):
                await main.data_task()
        self.assertIsNone(main.connection_settings)
        self.assertIsNone(main.telemetry.last_received)
