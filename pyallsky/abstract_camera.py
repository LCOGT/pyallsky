import array
import datetime
import logging
import struct
import time
from abc import ABC, abstractmethod

class AllSkyException(Exception):
    '''Exception class for errors from this code'''
    pass

# Test Commands
COM_TEST = 'E'

# Shutter Commands
OPEN_SHUTTER = 'O'
CLOSE_SHUTTER = 'C'
DE_ENERGIZE = 'K'

# Heater Commands
HEATER_ON = 'g\x01'
HEATER_OFF = 'g\x00'

# Setup Commands
GET_FVERSION = 'V'
GET_SERIAL = 'r'

# Imaging Commands
TAKE_IMAGE = 'T'
ABORT_IMAGE = 'A'
XFER_IMAGE = 'X'

CSUM_OK = 'K'
CSUM_ERROR = 'R'
STOP_XFER = 'S'

EXPOSURE_IN_PROGRESS = 'E'
READOUT_IN_PROGRESS = 'R'
EXPOSURE_DONE = 'D'
MAX_EXPOSURE = 0x63FFFF

# Guiding Commands
CALIBRATE_GUIDER = 'H'
AUTO_GUIDE = 'I'
TERMINATOR = chr(0x1A)

# Binning Types
BIN_SUBFRAME = chr(0xFF)
BIN_2X2 = chr(0x02)
BIN_1X1_CROPPED = chr(0x01)
BIN_1X1_FULL = chr(0x00)

# Exposure Types
EXP_LIGHT_AUTO_DARK = chr(0x02)
EXP_LIGHT_ONLY = chr(0x01)
EXP_DARK_ONLY = chr(0x00)

# Other Constants
PIXEL_SIZE = 2


class AbstractCamera(ABC):

    def __init__(self):
        # set log level to debug
        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger("all_sky_camera")

    @abstractmethod
    def camera_tx(self, data):
        '''
        Write data to the camera.

        data -- the data to send
        '''
        pass

    @abstractmethod
    def camera_rx(self, nbytes, timeout=0.5):
        '''
        Receive data from camerat with a timeout

        nbytes -- the maximum number of bytes to receive
        timeout -- the maximum number of seconds to wait for data
        '''
        pass

    @abstractmethod
    def camera_rx_until(self, terminator, timeout=5.0):
        '''
        Receive data from a camera until a certain terminator character is received

        terminator -- the single character which terminates the receive operation
        timeout -- the maximum amount of time to wait

        Returns all the data read up to (but not including) the terminator
        '''
        pass

    @abstractmethod
    def camera_timeout_calc(self, nbytes):
        '''
        Calculate the required timeout to transmit a certain number of bytes
        based on the particular implementation of the camera device.

        nbytes -- the number of bytes that will be transmitted

        return -- the time required to transmit in seconds
        '''
        pass

    def firmware_version(self):
        '''
        Request firmware version information from the camera and
        return it in the string format described in the manual.

        Example: R1.30 - "Release v1.30"
        Example: T1.16 - "Test v1.16"
        '''
        self.send_command(GET_FVERSION)
        data = self.camera_rx(2)

        version_type = (data[0] & 0x80) and 'T' or 'R'
        version_major = (data[0] & 0x7f)
        version_minor = (data[1])

        return '%s%d.%d' % (version_type, version_major, version_minor)

    def serial_number(self):
        '''
        Returns the camera's serial number (9 byte string)
        '''
        self.send_command(GET_SERIAL)
        data = self.camera_rx(9)
        return data

    def open_shutter(self):
        '''
        Open the camera shutter, then de-energize the shutter motor.
        '''
        self.send_command(OPEN_SHUTTER)
        time.sleep(0.2)
        self.send_command(DE_ENERGIZE)

    def close_shutter(self):
        '''
        Close the camera shutter, then de-energize the shutter motor.
        '''
        self.send_command(CLOSE_SHUTTER)
        time.sleep(0.2)
        self.send_command(DE_ENERGIZE)

    def activate_heater(self):
        '''
        Activate the built in heater
        '''
        self.send_command(HEATER_ON)

    def deactivate_heater(self):
        '''
        Deactivate the built in heater
        '''
        self.send_command(HEATER_OFF)

    def calibrate_guider(self):
        '''
        Request the camera to automatically calibrate the guider.
        return -- the string of calibration data sent back from camera
        '''
        self.send_command(CALIBRATE_GUIDER)
        return self.camera_rx_until(TERMINATOR, 240.0)

    def autonomous_guide(self):
        '''
        Begin autonomous guiding process
        return -- Data sent back from camera
        '''
        self.send_command(AUTO_GUIDE)
        return self.camera_rx_until(TERMINATOR, 240.0)

    def take_image(self, exposure=1.0, dark=False):
        '''
        Run an exposure of the CCD.
        exposure -- exposure time in seconds
        dark -- take a dark current exposure
        return -- the timestamp that the exposure was taken in ISO format
        '''
        # Camera exposure time works in 100us units, with a maximum value
        exptime = min(exposure / 100e-6, MAX_EXPOSURE)

        # choose between light/dark exposure type
        exptype = EXP_DARK_ONLY if dark else EXP_LIGHT_ONLY

        exp = struct.pack('I', int(exptime))[:3]
        com = (TAKE_IMAGE.encode() + exp[::-1] + BIN_1X1_FULL.encode() + exptype.encode())

        timestamp = datetime.datetime.utcnow()

        self.logger.debug('Exposure begin: command %s', self.hexify(com))
        self.send_command(com)

        # wait until the exposure is finished, with plenty of timing slack to
        # handle hardware latency on very short exposures (measurements show
        # that the camera has ~1 second of hardware latency)
        timeout = exposure + 15.0
        self.camera_rx_until(EXPOSURE_DONE, timeout)
        self.logger.debug('Exposure complete')

        return timestamp

    def __xfer_image_block(self, expected=4096, ignore_csum=False, tries=10):
        '''
        Get one 'block' of image data. At full frame the camera returns image
        data in chunks of 4096 pixels. For different imaging modes this value
        will change, but the caller can simply change the value of expected.

        This routine will automatically retry if a communication error occurs,
        up to the maximum number of retries specified.

        expected -- Number of pixels to retrieve
        ignore_csum -- Always pass checksum without checking (for debug only)
        tries -- The maximum number of tries before aborting transfer

        return -- the raw pixel data from the camera as a Python array of unsigned bytes
        '''
        for i in range(tries):
            self.logger.debug('Get Image Block: try %d', i)

            # not the first try, transmit checksum error so the camera will try again
            if i > 0:
                self.camera_tx(CSUM_ERROR)

            # calculate number of bytes and expected transfer time
            nbytes = expected * PIXEL_SIZE
            timeout = self.camera_timeout_calc(nbytes)

            # read the data and checksum
            self.logger.debug('Get Image Block: attempt to read %d bytes in %s seconds', nbytes, timeout)
            data = self.camera_rx(nbytes, timeout)
            csum_byte = self.camera_rx(1)
            self.logger.debug('Get Image Block: finished reading data')

            # not enough bytes, therefore transfer failed
            if len(data) != nbytes:
                self.logger.debug('Not enough data returned before timeout')
                continue

            # calculate XOR-based checksum, convert data to ints, then xor
            # Python has some weird sign extension thing, hence the extra bitwise ands
            data = array.array('B', data)
            csum = 0
            for byte in data:
                csum ^= (byte & 0xff)
                csum &= 0xff

            # convert csum_byte to an integer
            csum_byte = ord(csum_byte)

            self.logger.debug('Checksum from camera: %.2x', csum_byte)
            self.logger.debug('Checksum calculated: %.2x', csum)

            # enough bytes and csum valid, exit the loop
            if ignore_csum or csum == csum_byte:
                self.logger.debug('Checksum OK, successfully received block')
                self.camera_tx(CSUM_OK)
                return data

            # enough bytes and csum invalid, try again
            self.logger.debug('Checksum ERROR')

        # too many retries passed, abort
        self.logger.debug('Get Image Block: retries exhausted, abort transfer')
        self.camera_tx(STOP_XFER)
        raise AllSkyException('Too many errors during image sub-block transfer')



    def xfer_image(self, progress_callback=None):
        '''
        Fetch an image from the camera

        progress_callback -- Function to be called after each block downloaded

        return -- the raw pixel data from the camera as a Python array of unsigned bytes
        '''
        # Calculate number of sub-blocks expected
        blocks_expected = 75 # (640 * 480) / 4096

        # Download Image
        self.send_command(XFER_IMAGE)

        data = array.array('B')
        blocks_complete = 0
        for _ in range(blocks_expected):
            data += self.__xfer_image_block(ignore_csum=True)
            blocks_complete += 1
            self.logger.debug('Received block %d', blocks_complete)
            if progress_callback is not None:
                progress_callback(float(blocks_complete) / blocks_expected * 100)

        self.logger.debug('Image download complete')
        return data


    def send_command(self, command):
        '''
        Send a command to the camera and read back and check the checksum

        command -- the command to send

        return -- True on success, False otherwise
        '''

        csum = self.checksum(command)
        data = command + csum

        self.camera_tx(data)
        data = self.camera_rx(1)

        if data != csum:
            self.logger.error('command %s csum %s rxcsum %s', self.bufdump(command), self.bufdump(csum), self.bufdump(data))

        return data == csum

    def checksum(self, command):
        '''
        Return the checksum of an arbitrary command

        command -- command string to checksum

        The checksum is simply calculated by complementing the byte, clearing the
        most significant bit and XOR with the current checksum, going through each byte
        in the command. For each individual command the checksum starts as 0
        '''
        cs = 0
        for b in command:
            csb = ~b & 0x7F
            cs = cs ^ csb
        return chr(cs)

    def hexify(self, s, join_char=':'):
        '''
        Print a string as hex values
        '''
        s = str(s)
        return join_char.join(hex(ord(c))[2:] for c in s)

    def bufdump(self, buf):
        '''
        Print a byte buffer in the convenient format of a hex-ified string and
        the total length
        '''
        return '"%s" (%d bytes)' % (self.hexify(buf), len(buf))