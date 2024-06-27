import logging
import time

import serial

from pyallsky.abstract_camera import AbstractCamera

BAUD_RATE = {9600: 'B0',
             19200: 'B1',
             38400: 'B2',
             57600: 'B3',
             115200: 'B4',
             230400: 'B5',
             460800: 'B6'}


class SerialCameraException:
    pass


class SerialCamera(AbstractCamera):
    '''
    Class to interact with the SBIG AllSky 340/340C camera, encapsulating the
    serial communication protocol, and providing a pythonic api to access the
    device.

    Automatically determines the baud rate necessary for communication.
    '''

    def __init__(self, device):
        ser = serial.Serial(device)

        # defaults taken from the manual
        ser.setBaudrate(9600)
        ser.bytesize = serial.EIGHTBITS
        ser.parity = serial.PARITY_NONE
        ser.stopbits = serial.STOPBITS_ONE

        # set a short timeout for reads during baud rate detection
        ser.timeout = 0.1

        # Camera baud rate is initially unknown, so find it
        if not self.autobaud(count=3):
            logging.debug('Autodetect baud rate failed')
            raise SerialCameraException('Autodetect baud rate failed')

        self.serial_connection = ser

    def camera_tx(self, data):
        self.serial_connection.write(data)

    def camera_rx(self, nbytes, timeout=0.5):
        tstart = time.time()
        data = ''

        while True:
            # timeout has passed, break out of the loop
            tcurrent = time.time()
            tdiff = tcurrent - tstart
            if tdiff > timeout:
                break

            # we have all the bytes, break out of the loop
            remain = nbytes - len(data)
            if remain == 0:
                break

            # append more bytes as they come in
            data += self.serial_connection.read(remain)

    def camera_rx_until(self, terminator, timeout=5.0):
        tstart = time.time()
        data = ''

        while True:
            # timeout has passed, break out of the loop
            tcurrent = time.time()
            tdiff = tcurrent - tstart
            if tdiff > timeout:
                break

            c = self.serial_connection.read(1)
            if c == terminator:
                break

            # terminator was not found, append the current byte
            data += c

        return data

    def camera_timeout_calc(self, nbytes):
        # (bits_per_second / number_of_bits) * overhead_fudge_factor
        return (self.serial_connection.getBaudrate() / (nbytes * 8)) * 1.5

    def autobaud(self, count=3):
        '''
        Automatic Baud Rate Detection

        The manual specifies an algorithm where each possible baud rate is
        attempted once, and the successful one is the winner. This is insufficient,
        since the previous attempts may leave some junk in the serial port buffer
        on the receiving side.

        To work around the problem, we set the attempted baud rate, then
        check the communications several times to clear out any leftover junk.
        This method has been found to be extremely reliable.

        ser -- the serial.Serial() to receive from
        count -- the maximum number of attempts to communicate at each baud rate

        return -- True on success, False otherwise
        '''
        found = False
        for rate in sorted(BAUD_RATE, key=BAUD_RATE.get)[:-2]:
            logging.debug('Testing baud rate %s', rate)
            self.serial_connection.setBaudrate(rate)
            found = self.check_communications(count)
            if found:
                logging.info('Autodetect baud rate successful %d', rate)
                break

        return found
