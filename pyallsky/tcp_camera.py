import socket
import time

from pyallsky.abstract_camera import AbstractCamera

FIXED_TCP_IMAGE_READ_TIMEOUT_SECONDS = 30


class TcpCamera(AbstractCamera):
    def __init__(self, host, port):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((host, port))

    def camera_tx(self, data):
        self.socket.sendall(data.encode())

    def camera_rx(self, nbytes, timeout=0.5):
        self.socket.settimeout(timeout)
        try:
            data = self.socket.recv(nbytes)
        except socket.timeout:
            data = ''
        return data

    def camera_rx_until(self, terminator, timeout=5.0):
        data = ''
        start_time = time.time()
        while True:
            if time.time() - start_time > timeout:
                break
            chunk = self.socket.recv(1)
            if chunk == terminator:
                break
            if chunk == b'':
                break
            data += chunk
        return data

    def camera_timeout_calc(self, nbytes):
        return FIXED_TCP_IMAGE_READ_TIMEOUT_SECONDS