import socket
import time

from pyallsky.abstract_camera import AbstractCamera

FIXED_TCP_IMAGE_READ_TIMEOUT_SECONDS = 30


class TcpCamera(AbstractCamera):
    '''
    Class to interact with the SBIG AllSky 340/340C camera via a Moxa NPort 5150A
    serial to network convertor via tcp protocol, and providing a pythonic
    api to access the device.

    '''
    def __init__(self, host, port):
        super().__init__()
        self.host = host
        self.port = port
        self.connect(host, port)


    def connect(self, host, port):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.socket.connect((host, int(port)))
        except socket.error as e:
            print('Error connecting to camera: %s' % e)

    def camera_tx(self, data):
        for char in data:
            if isinstance(char, str):
                self.socket.send(char.encode())
            elif isinstance(char, int):
                self.socket.send(bytes([char]))
            else:
                self.socket.send(char)

    def camera_rx(self, nbytes, timeout=FIXED_TCP_IMAGE_READ_TIMEOUT_SECONDS):
        tstart = time.time()
        self.socket.settimeout(timeout)
        data = b''

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
            data += self.socket.recv(remain)

        return data

    def camera_rx_until(self, terminator, timeout=5.0):
        data = b''
        start_time = time.time()
        log_time = start_time + 1
        while True:
            if time.time() - start_time > timeout:
                break
            if time.time() > log_time:
                log_time = time.time() + 1
            chunk = self.socket.recv(1)
            if chunk == terminator.encode():
                break
            if chunk == b'':
                break
            data += chunk
        return data

    def camera_timeout_calc(self, nbytes):
        return FIXED_TCP_IMAGE_READ_TIMEOUT_SECONDS
