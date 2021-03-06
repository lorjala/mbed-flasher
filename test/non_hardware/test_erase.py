#!/usr/bin/env python
"""
Copyright 2016 ARM Limited

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
# pylint:disable=missing-docstring
# pylint:disable=invalid-name

import logging
import unittest
import mock

from mbed_flasher.common import EraseError
from mbed_flasher.erase import Erase
from mbed_flasher.return_codes import EXIT_CODE_TARGET_ID_MISSING
from mbed_flasher.return_codes import EXIT_CODE_COULD_NOT_MAP_TARGET_ID_TO_DEVICE
from mbed_flasher.return_codes import EXIT_CODE_IMPLEMENTATION_MISSING
from mbed_flasher.return_codes import EXIT_CODE_MOUNT_POINT_MISSING
from mbed_flasher.return_codes import EXIT_CODE_SERIAL_PORT_MISSING


class EraseTestCase(unittest.TestCase):
    """ Basic true asserts to see that testing is executed
    """
    def setUp(self):
        logging.disable(logging.CRITICAL)

    def test_erase_with_none(self):
        eraser = Erase()
        with self.assertRaises(EraseError) as cm:
            eraser.erase(target_id=None, method='simple')

        self.assertEqual(cm.exception.return_code, EXIT_CODE_TARGET_ID_MISSING)

    @mock.patch('mbed_flasher.common.Common.get_available_device_mapping')
    def test_erase_with_wrong_target_id(self, mock_device_mapping):
        mock_device_mapping.return_value = []
        eraser = Erase()
        with self.assertRaises(EraseError) as cm:
            eraser.erase(target_id='555', method='simple')

        self.assertEqual(cm.exception.return_code, EXIT_CODE_COULD_NOT_MAP_TARGET_ID_TO_DEVICE)

    @mock.patch('mbed_flasher.common.Common.get_available_device_mapping')
    def test_erase_with_all_no_devices(self, mock_device_mapping):
        mock_device_mapping.return_value = []
        eraser = Erase()
        with self.assertRaises(EraseError) as cm:
            eraser.erase(target_id='all', method='simple')

        self.assertEqual(cm.exception.return_code, EXIT_CODE_COULD_NOT_MAP_TARGET_ID_TO_DEVICE)

    @mock.patch('mbed_flasher.common.Common.get_available_device_mapping')
    @mock.patch("os.path.isfile", return_value=True)
    # test func name is larger than 30, but is meaningful
    # pylint: disable=invalid-name
    def test_erase_failed_non_supported_devices(self, _, mock_device_mapping):
        devices = [{"target_id": "123",
                    "platform_name": "K64F",
                    "mount_point": "/mnt/k64f",
                    "serial_port": "/dev/uart"}]
        mock_device_mapping.return_value = devices
        eraser = Erase()
        with self.assertRaises(EraseError) as cm:
            eraser.erase(target_id="123", method='simple')

        self.assertEqual(cm.exception.return_code, EXIT_CODE_IMPLEMENTATION_MISSING)

    @mock.patch('mbed_flasher.common.Common.get_available_device_mapping')
    @mock.patch("os.path.isfile", return_value=True)
    # test func name is larger than 30, but is meaningful
    # pylint: disable=invalid-name
    def test_erase_failed_mount_point_missing(self, _, mock_device_mapping):
        devices = [{"target_id": "123",
                    "platform_name": "K64F",
                    "serial_port": "/dev/uart"}]
        mock_device_mapping.return_value = devices
        eraser = Erase()
        with self.assertRaises(EraseError) as cm:
            eraser.erase(target_id="123", method='simple')

        self.assertEqual(cm.exception.return_code, EXIT_CODE_MOUNT_POINT_MISSING)

    @mock.patch('mbed_flasher.common.Common.get_available_device_mapping')
    @mock.patch("os.path.isfile", return_value=True)
    # test func name is larger than 30, but is meaningful
    # pylint: disable=invalid-name
    def test_erase_failed_serial_port_missing(self, _, mock_device_mapping):
        devices = [{"target_id": "123",
                    "platform_name": "K64F",
                    "mount_point": "/mnt/k64f"}]
        mock_device_mapping.return_value = devices
        eraser = Erase()
        with self.assertRaises(EraseError) as cm:
            eraser.erase(target_id="123", method='simple')

        self.assertEqual(cm.exception.return_code, EXIT_CODE_SERIAL_PORT_MISSING)


if __name__ == '__main__':
    unittest.main()
