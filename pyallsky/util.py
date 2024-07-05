#!/usr/bin/env python

import sys
import logging

def setup_logging(level=logging.INFO, stream=sys.stdout):
    # get the default logger instance
    logger = logging.getLogger()

    # set the default output level
    logger.setLevel(level)

    # connect the logger to the requested stream
    ch = logging.StreamHandler(stream)

    # set the output format
    fmt = '%(asctime)s.%(msecs).03d %(levelname)7s: %(message)s'
    formatter = logging.Formatter(fmt, datefmt='%Y-%m-%d %H:%M:%S')

    # and hook it all together
    ch.setFormatter(formatter)
    logger.addHandler(ch)


def is_network_device(device):
    # a network device is identified by having a host followed by a colon followed by an integer port
    if ':' in device:
        host, port = device.split(':')
        return bool(host and port.isdigit())
    return False
