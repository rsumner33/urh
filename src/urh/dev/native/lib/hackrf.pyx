cimport chackrf
from libc.stdlib cimport malloc
from libc.string cimport memcpy
import time
cdef object f
from cpython cimport PyBytes_GET_SIZE

cdef int _c_callback_recv(chackrf.hackrf_transfer* transfer)  with gil:
    global f
    (<object>f)(transfer.buffer[0:transfer.valid_length])
    return 0

cdef int _c_callback_send(chackrf.hackrf_transfer* transfer)  with gil:
    global f
    cdef bytes bytebuf = (<object>f)(transfer.valid_length)
    memcpy(transfer.buffer, <void*> bytebuf, PyBytes_GET_SIZE(bytebuf))
    return 0

cdef chackrf.hackrf_device* _c_device
cdef int hackrf_success = chackrf.HACKRF_SUCCESS


cpdef setup():
    chackrf.hackrf_init()
    return open()

cpdef exit():
    return chackrf.hackrf_exit()

cpdef reopen():
    close()
    return open()

cpdef open():
    return chackrf.hackrf_open(&_c_device)

cpdef close():
    time.sleep(0.1)
    return chackrf.hackrf_close(_c_device)

cpdef start_rx_mode(callback):
    global f
    f  = callback
    return chackrf.hackrf_start_rx(_c_device, _c_callback_recv, <void*>_c_callback_recv)

cpdef stop_rx_mode():
    return chackrf.hackrf_stop_rx(_c_device)

cpdef start_tx_mode(callback):
    global f
    f = callback
    return chackrf.hackrf_start_tx(_c_device, _c_callback_send, <void *>_c_callback_send)

cpdef stop_tx_mode():
    return chackrf.hackrf_stop_tx(_c_device)

cpdef board_id_read():
    cdef unsigned char value
    ret = chackrf.hackrf_board_id_read(_c_device, &value)
    if ret == hackrf_success:
        return value
    else:
        return ""

cpdef version_string_read():
    cdef char* version = <char *>malloc(20 * sizeof(char))
    cdef unsigned char length = 20
    ret = chackrf.hackrf_version_string_read(_c_device, version, length)
    if ret == hackrf_success:
        return version.decode('UTF-8')
    else:
        return ""

cpdef set_freq(freq_hz):
    return chackrf.hackrf_set_freq(_c_device, freq_hz)

cpdef is_streaming():
    ret = chackrf.hackrf_is_streaming(_c_device)
    if ret == 1:
        return True
    else:
        return False

cpdef set_lna_gain( value):
    ''' Sets the LNA gain, in 8Db steps, maximum value of 40 '''
    return chackrf.hackrf_set_lna_gain(_c_device, value)

cpdef set_vga_gain( value):
    ''' Sets the vga gain, in 2db steps, maximum value of 62 '''
    return chackrf.hackrf_set_vga_gain(_c_device, value)

cpdef set_txvga_gain( value):
    ''' Sets the txvga gain, in 1db steps, maximum value of 47 '''
    return chackrf.hackrf_set_txvga_gain(_c_device, value)

cpdef set_antenna_enable( value):
    cdef bint val = 1 if value else 0
    return chackrf.hackrf_set_antenna_enable(_c_device, val)

cpdef set_sample_rate( sample_rate):
    return chackrf.hackrf_set_sample_rate(_c_device, sample_rate)


cpdef set_amp_enable( value):
    cdef bint val = 1 if value else 0
    return chackrf.hackrf_set_amp_enable(_c_device, val)

cpdef set_baseband_filter_bandwidth(bandwidth_hz):
    return chackrf.hackrf_set_baseband_filter_bandwidth(_c_device, bandwidth_hz)