import copy
import unittest

from urh.dev.PCAP import PCAP
from urh.signalprocessing.ProtocolAnalyzer import ProtocolAnalyzer
from urh.signalprocessing.Signal import Signal


class TestPCAP(unittest.TestCase):
    def test_write(self):
        signal = Signal("./data/ask.complex", "ASK-Test")
        signal.modulation_type = 0
        signal.bit_len = 295
        signal.qad_center = -0.1667
        self.assertEqual(signal.num_samples, 13710)

        proto_analyzer = ProtocolAnalyzer(signal)
        proto_analyzer.get_protocol_from_signal()
        self.assertEqual(proto_analyzer.decoded_hex_str[0], "b25b6db6c80")

        proto_analyzer.blocks.append(copy.deepcopy(proto_analyzer.blocks[0]))
        proto_analyzer.blocks.append(copy.deepcopy(proto_analyzer.blocks[0]))
        proto_analyzer.blocks.append(copy.deepcopy(proto_analyzer.blocks[0]))


        pcap = PCAP()
        pcap.write_packets(proto_analyzer.blocks, "/tmp/test.pcap", 1e6)