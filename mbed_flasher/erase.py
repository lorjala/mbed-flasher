"""
mbed SDK
Copyright (c) 2011-2015 ARM Limited
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
    http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Author:
Veli-Matti Lahtela <veli-matti.lahtela@arm.com>
"""

import logging
import types
from time import sleep
from os.path import join, isfile
import subprocess
import platform

EXIT_CODE_SUCCESS = 0
EXIT_CODE_RESET_FAILED_PORT_OPEN = 11
EXIT_CODE_SERIAL_RESET_FAILED = 13
EXIT_CODE_COULD_NOT_MAP_TO_DEVICE = 21
EXIT_CODE_PYOCD_MISSING = 23
EXIT_CODE_PYOCD_ERASE_FAILED = 27
EXIT_CODE_NONSUPPORTED_METHOD_FOR_ERASE = 29
EXIT_CODE_IMPLEMENTATION_MISSING = 31
SLEEP_TIME_FOR_REMOUNT = 5
EXIT_CODE_ERASE_FAILED_NOT_SUPPORTED = 33
EXIT_CODE_TARGET_ID_MISSING = 34
EXIT_CODE_NOT_SUPPORTED_METHOD_FOR_PLATFORM = 37


class Erase(object):
    """ Erase object, which manages erasing for given devices
    """

    def __init__(self):
        self.logger = logging.getLogger('mbed-flasher')
        self.FLASHERS = self.__get_flashers()

    def get_available_device_mapping(self):
        available_devices = []
        for Flasher in self.FLASHERS:
            devices = Flasher.get_available_devices()
            available_devices.extend(devices)
        return available_devices

    @staticmethod
    def __get_flashers():
        from flashers import AvailableFlashers
        return AvailableFlashers
        
    def reset_board(self, serial_port):
        from flashers.enhancedserial import EnhancedSerial
        from serial.serialutil import SerialException
        try:
            port = EnhancedSerial(serial_port)
        except SerialException as e:
            self.logger.info("reset could not be sent")
            self.logger.error(e)
            if e.message.find('could not open port') != -1:
                print 'Reset could not be given. Close your Serial connection to device.'
            return EXIT_CODE_RESET_FAILED_PORT_OPEN
        port.baudrate = 115200
        port.timeout = 1
        port.xonxoff = False
        port.rtscts = False
        port.flushInput()
        port.flushOutput()

        if port:
            self.logger.info("sendBreak to device to reboot")
            result = port.safe_sendBreak()
            if result:
                self.logger.info("reset completed")
            else:
                self.logger.error("reset failed")
                return EXIT_CODE_SERIAL_RESET_FAILED
        port.close()
        return EXIT_CODE_SUCCESS
    
    def erase_board(self, mount_point, serial_port):
        automation_activated = False
        if isfile(join(mount_point, 'DETAILS.TXT')):
            with open(join(mount_point, 'DETAILS.TXT'), 'rb') as f:
                for lines in f:
                    if lines.find("Automation allowed: 1") != -1:
                        automation_activated = True
                    else:
                        continue
        if automation_activated:
            self.logger.warn("Experimental feature, might not do anything!")
            self.logger.info("erasing device")
            with open(join(mount_point, 'ERASE.ACT'), 'wb') as new_file:
                pass
            sleep(SLEEP_TIME_FOR_REMOUNT)
            success = self.reset_board(serial_port)
            if isfile(join(mount_point, 'ERASE.ACT')):
                success = EXIT_CODE_ERASE_FAILED_NOT_SUPPORTED
            if success != 0:
                self.logger.error("erase failed")
                return success
            self.logger.info("erase completed")
            return EXIT_CODE_SUCCESS
        else:
            print "Selected device does not support erasing through DAPLINK"
            return EXIT_CODE_IMPLEMENTATION_MISSING

    def erase(self, target_id=None, method=None):
        """Erase (mbed) device
        :param target_id: target_id
        :param method: method for erase i.e. simple, pyocd or edbg
        """
        self.logger.info("Starting erase for given target_id %s" % target_id)
        self.logger.info("method used for erase: %s" % method)
        available_devices = self.get_available_device_mapping()
        targets_to_erase = []

        if target_id is not None:
            if isinstance(target_id, types.ListType):
                if 'all' in target_id:
                    targets_to_reset = available_devices
                else:
                    for target in target_id:
                        for device in available_devices:
                            if target == device['target_id']:
                                if device not in targets_to_erase:
                                    targets_to_erase.append(device)
            else:
                if target_id == 'all':
                   targets_to_erase = available_devices
                elif len(target_id) <= 48:
                    for device in available_devices:
                        if target_id == device['target_id'] or device['target_id'].startswith(target_id):
                            if device not in targets_to_erase:
                                targets_to_erase.append(device)

            if len(targets_to_erase) > 0:
                for item in targets_to_erase:
                    if item['platform_name'] == 'K64F':
                        if method == 'simple' and 'mount_point' in item and 'serial_port' in item:
                            self.erase_board(item['mount_point'], item['serial_port'])
                        elif method == 'pyocd':
                            try:
                                from pyOCD.board import MbedBoard
                                from pyOCD.pyDAPAccess import DAPAccessIntf
                            except ImportError:
                                print 'pyOCD missing, install it\n'
                                return EXIT_CODE_PYOCD_MISSING
                            board = MbedBoard.chooseBoard(board_id=item["target_id"])
                            self.logger.info("erasing device")
                            ocd_target = board.target
                            flash = ocd_target.flash
                            try:
                                flash.eraseAll()
                                ocd_target.reset()
                            except DAPAccessIntf.TransferFaultError as e:
                                pass
                            self.logger.info("erase completed")
                        elif method == 'edbg':
                            return EXIT_CODE_NOT_SUPPORTED_METHOD_FOR_PLATFORM
                        else:
                            print "Selected method %s not supported by K64F" % method
                            return EXIT_CODE_NONSUPPORTED_METHOD_FOR_ERASE
                    elif item['platform_name'] == 'SAM4E':
                        from flash import Flash
                        flasher = Flash.get_flasher('atmel')
                        if method == 'simple':
                            cmd = [flasher.exe, "-t", "edbg", "-i", "SWD", "-d", "atsam4e16e", "-s", item['target_id'], "erase"]
                        elif method == 'edbg':
                            flasher.set_edbg_exe(flasher.exe, True)
                            if platform.system() == 'Windows':
                                cmd = [flasher.exe, "-t", "atmel_cm4", "-s", item['target_id'], "--erase"]
                            else:
                                cmd = ['sudo', flasher.exe, "-t", "atmel_cm4", "-s", item['target_id'], "--erase"]
                        else:
                            print "Selected method %s not supported by SAM4E" % method
                            return EXIT_CODE_NOT_SUPPORTED_METHOD_FOR_PLATFORM
                        self.logger.info("erasing device")
                        flasher.logger.debug(cmd)
                        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        stdout, stderr = proc.communicate()
                        flasher.logger.debug(stdout)
                        flasher.logger.debug(stderr)
                        self.logger.info("erase completed")
                        return proc.returncode
                    else:
                        print "Only mbed devices supported"
                        return EXIT_CODE_IMPLEMENTATION_MISSING
            else:
                print "Could not map given target_id(s) to available devices"
                return EXIT_CODE_COULD_NOT_MAP_TO_DEVICE

            return EXIT_CODE_SUCCESS
        else:
            return EXIT_CODE_TARGET_ID_MISSING