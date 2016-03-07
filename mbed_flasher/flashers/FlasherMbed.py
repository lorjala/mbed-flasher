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
Jussi Vatjus-Anttila <jussi.vatjus-anttila@arm.com>
"""

import json
import logging
import sys
import six
from os.path import join, abspath, dirname, isfile
from shutil import copy
import os
import platform
from time import sleep
from threading import Thread
from enhancedserial import EnhancedSerial
from uuid import uuid1


class FlasherMbed(object):
    name = "Mbed"

    def __init__(self):
        self.logger = logging.getLogger('mbed-flasher')

    @staticmethod
    def get_supported_targets():
        """Load target mapping information
        """
        libpath = dirname(abspath(sys.modules[__name__].__file__))
        return json.loads(open( join(libpath, "FlasherMbed.target_info.json"), "rb").read())

    @staticmethod
    def get_available_devices():
        import mbed_lstools
        mbeds = mbed_lstools.create()
        return mbeds.list_mbeds()
       
    def runner(self, drive):
        while True:
            if platform.system() == 'Windows':
                out = os.popen('dir %s' %drive).read()
            else:
                out = os.popen('ls %s 2> /dev/null' %drive).read()
            if out.find('MBED.HTM') != -1:
                break
                

    def flash(self, source, target):
        """copy file to the destination
        :param binary_data: binary data to be flashed
        :param target: target
        """

        mount_point = target['mount_point']+'/'
        binary_type = target['properties']['binary_type']
        destination=abspath(join(mount_point, str(uuid1())+binary_type))

        if isinstance(source, six.string_types):
            try:
                if platform.system() == 'Windows':
                    self.logger.debug("copying file: %s to %s" % (source, destination))
                    copy(source, destination)
                else:
                    self.logger.debug('read source file')
                    source = open(source, 'rb').read()
                    self.logger.debug("writing binary: %s (size=%i bytes)", destination, len(source))
                    new_file = os.open(destination, os.O_CREAT | os.O_DIRECT | os.O_TRUNC | os.O_RDWR )
                    os.write(new_file, source)
                    os.close(new_file)
                sleep(3)
                t = Thread(target=self.runner, args=(target['mount_point'],))
                t.start()
                while True:
                    if not t.is_alive():
                        break
                self.port = False
                if 'serial_port' in target:
                    self.port = EnhancedSerial(target["serial_port"])
                    self.port.baudrate = 115200
                    self.port.timeout = 0.01
                    self.port.xonxoff = False
                    self.port.rtscts = False
                    self.port.flushInput()
                    self.port.flushOutput()

                    if self.port:
                        self.logger.info("sendBreak to device to reboot")
                        result = self.port.safe_sendBreak()
                        if result:
                            self.logger.info("reset completed")
                        else:
                            self.logger.info("reset failed")

                #verify flashing went as planned
                if 'mount_point' in target:
                    if isfile(join(target['mount_point'], 'FAIL.TXT')):
                        with open(join(target['mount_point'], 'FAIL.TXT'), 'r') as fault:
                            fault = fault.read().strip()
                        self.logger.error("Flashing failed: %s. tid=%s" % (fault, target["target_id"]))
                        return -4
                self.logger.debug("ready")
                return 0
            except IOError as err:
                self.logger.error(err)
                raise err
