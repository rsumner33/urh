import socket

import numpy as np
import psutil
import time
from PyQt5.QtCore import pyqtSignal

from urh.dev.gr.AbstractBaseThread import AbstractBaseThread
from urh.util.Logger import logger


class ReceiverThread(AbstractBaseThread):
    index_changed = pyqtSignal(int, int)


    def __init__(self, sample_rate, freq, gain, bandwidth, ip='127.0.0.1',
                 parent=None,  is_ringbuffer=False):
        super().__init__(sample_rate, freq, gain, bandwidth, True, ip, parent)

        self.is_ringbuffer = is_ringbuffer  # Ringbuffer for Live Sniffing
        self.data = None

    def init_recv_buffer(self):
        # Take 60% of free memory
        nsamples = int(0.6 * (psutil.virtual_memory().free / 8))
        self.data = np.zeros(nsamples, dtype=np.complex64)

    def run(self):
        if self.data is None:
            self.init_recv_buffer()

        self.initalize_process()
        self.init_recv_socket()

        recv = self.socket.recv
        rcvd = b""

        while not self.isInterruptionRequested():

            try:
                rcvd += recv(32768)  # Receive Buffer = 32768 Byte
            except ConnectionResetError:
                self.stop("Stopped receiving, because connection was reset.")
                return
            except OSError as e:   # https://github.com/jopohl/urh/issues/131
                logger.warning("Error occurred", str(e))

            if len(rcvd) < 8:
                self.stop("Stopped receiving: No data received anymore")
                return

            if len(rcvd) % 8 != 0:
                continue

            try:
                tmp = np.fromstring(rcvd, dtype=np.complex64)

                len_tmp = len(tmp)
                if self.current_index + len_tmp >= len(self.data):
                    if self.is_ringbuffer:
                        self.current_index = 0
                        if len_tmp >= len(self.data):
                            self.stop("Receiving buffer too small.")
                    else:
                        self.stop("Receiving Buffer is full.")
                        return
                self.data[self.current_index:self.current_index + len_tmp] = tmp
                self.current_index += len_tmp
                self.index_changed.emit(self.current_index - len_tmp,
                                        self.current_index)

                rcvd = b""
            except ValueError:
                self.stop("Could not receive data. Is your Hardware ok?")
