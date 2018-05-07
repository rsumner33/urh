#!/usr/bin/env python2
##################################################
# GNU Radio Python Flow Graph
# Title: Top Block
# Generated: Fri Aug 21 15:50:34 2015
##################################################

from optparse import OptionParser

from gnuradio import gr
from gnuradio import uhd
from gnuradio.eng_option import eng_option
from grc_gnuradio import blks2 as grc_blks2


class top_block(gr.top_block):
    def __init__(self, samp_rate, freq, gain, bw, ip, port):
        gr.top_block.__init__(self, "Top Block")

        ##################################################
        # Variables
        ##################################################
        self.samp_rate = samp_rate
        self.gain = gain
        self.freq = freq
        self.bw = bw

        ##################################################
        # Blocks
        ##################################################
        self.uhd_usrp_sink_0 = uhd.usrp_sink(
            ",".join(("addr=" + ip, "")),
            uhd.stream_args(
                cpu_format="fc32",
                channels=range(1),
            ),
        )
        self.uhd_usrp_sink_0.set_samp_rate(samp_rate)
        self.uhd_usrp_sink_0.set_center_freq(freq, 0)
        self.uhd_usrp_sink_0.set_gain(gain, 0)
        self.uhd_usrp_sink_0.set_bandwidth(bw, 0)
        self.blks2_tcp_source_0 = grc_blks2.tcp_source(
            itemsize=gr.sizeof_gr_complex * 1,
            addr="",  # Vorher 127.0.0.1
            port=port,
            server=False,
        )

        ##################################################
        # Connections
        ##################################################
        self.connect((self.blks2_tcp_source_0, 0), (self.uhd_usrp_sink_0, 0))

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.uhd_usrp_sink_0.set_samp_rate(self.samp_rate)

    def get_gain(self):
        return self.gain

    def set_gain(self, gain):
        self.gain = gain
        self.uhd_usrp_sink_0.set_gain(self.gain, 0)

    def get_freq(self):
        return self.freq

    def set_freq(self, freq):
        self.freq = freq
        self.uhd_usrp_sink_0.set_center_freq(self.freq, 0)

    def get_bw(self):
        return self.bw

    def set_bw(self, bw):
        self.bw = bw
        self.uhd_usrp_sink_0.set_bandwidth(self.bw, 0)


if __name__ == '__main__':
    parser = OptionParser(option_class=eng_option, usage="%prog: [options]")
    parser.add_option("-s", "--samplerate", dest="samplerate", help="Sample Rate", default=100000)
    parser.add_option("-f", "--freq", dest="freq", help="Frequency", default=433000)
    parser.add_option("-g", "--gain", dest="gain", help="Gain", default=30)
    parser.add_option("-b", "--bandwidth", dest="bw", help="Bandwidth", default=200000)
    parser.add_option("-i", "--ip", dest="ip", help="IP", default="192.168.10.2")
    parser.add_option("-p", "--port", dest="port", help="Port", default=1337)
    (options, args) = parser.parse_args()
    tb = top_block(float(options.samplerate), float(options.freq), int(options.gain),
                   float(options.bw), str(options.ip), int(options.port))
    tb.start()
    tb.wait()
