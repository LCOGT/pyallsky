#!/usr/bin/env python

'''
High level image capture interface to the SBIG AllSky 340/340C
'''

import array
import datetime
import logging
from collections import namedtuple

from pyallsky.serial_camera import SerialCamera
from pyallsky.tcp_camera import TcpCamera
from pyallsky.util import is_network_device

# Tuple to hold all of the data about an exposure taken by an
# SBIG AllSky 340/340C camera
AllSkyImage = namedtuple('AllSkyImage', [
    'timestamp',
    'exposure',
    'data',
])

def show_progress(pct):
    '''Method to display image transfer progress depending on logging level'''
    logging.info('Transfer progress: %.2f%%', pct)


def capture_image_device(device_config, exposure, dark=False):
    '''
    Capture an image from an SBIG AllSky 340/340C camera
    and control the heater (on or off)

    device -- the device node to use (for example, /dev/ttyUSB0)
    exposure -- the exposure time to use (in seconds)
    dark -- capture a dark current image

    Exceptions:
    serial.serialutil.SerialException -- exception raised by pyserial
    AllSkyException -- exception raised by pyallsky

    Returns an instance of AllSkyImage
    '''
    logging.info('Connecting to camera')
    if is_network_device(device_config.device):
        host, port = device_config.device.split(':')
        cam = TcpCamera(host, int(port))
    else:
        cam = SerialCamera(device_config.device)

    logging.info('Taking exposure')
    timestamp = cam.take_image(exposure=exposure, dark=dark)

    logging.info('Downloading image')
    data = cam.xfer_image(progress_callback=show_progress)

    return AllSkyImage(timestamp=timestamp, exposure=exposure, data=data)

def capture_image_file(filename, exposure, dark=False):
    '''
    Capture an image from a previously saved RAW file

    This is primarily meant to be used to debug the image postprocessing code
    without requiring the camera hardware.
    '''
    # fake timestamp data
    timestamp = datetime.datetime.utcnow()

    data = array.array('B')
    with open(filename, 'r') as f:
        data = array.array('B', f.read())

    return AllSkyImage(timestamp=timestamp, exposure=exposure, data=data)
