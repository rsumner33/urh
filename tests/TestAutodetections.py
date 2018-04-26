import unittest

from urh.signalprocessing.Signal import Signal


class TestAutodetections(unittest.TestCase):
    # Testmethode muss immer mit Präfix test_* starten
    def test_auto_detect_esaver(self):
        signal = Signal("./data/esaver.complex", "ESaver")
        signal.modulation_type = 1
        signal.qad_center = signal.estimate_qad_center()
        self.assertTrue(0.24 < signal.qad_center < 0.5)
        signal.bit_len = signal.estimate_bitlen()
        self.assertTrue(80 <= signal.bit_len <= 120)

    def test_auto_detect_elektromaten(self):
        signal = Signal("./data/elektromaten.complex", "Elektromaten")
        signal.modulation_type = 0
        signal.qad_center = signal.estimate_qad_center()
        self.assertTrue(0.0015 < signal.qad_center < 0.0140)
        signal.bit_len = signal.estimate_bitlen()
        self.assertTrue(270 <= signal.bit_len <= 330)

    def test_auto_detect_fsk(self):
        signal = Signal("./data/fsk.complex", "FSK")
        signal.modulation_type = 1
        signal.qad_center = signal.estimate_qad_center()
        self.assertTrue(-0.1 <= signal.qad_center <= 0)
        signal.bit_len = signal.estimate_bitlen()
        self.assertTrue(90 <= signal.bit_len <= 110)

    def test_auto_detect_ask(self):
        signal = Signal("./data/ask.complex", "ASK")
        signal.modulation_type = 0
        signal.qad_center = signal.estimate_qad_center()
        self.assertTrue(0 <= signal.qad_center <= 0.0036)
        signal.bit_len = signal.estimate_bitlen()
        self.assertTrue(270 <= signal.bit_len <= 330)

    def test_qad_stays_the_same(self):
        signal = Signal("./data/esaver.complex", "ESaver")
        signal.modulation_type = 1
        signal.qad_center = signal.estimate_qad_center()
        qad_center = signal.qad_center
        for i in range(10):
            self.assertEqual(qad_center, signal.estimate_qad_center())

if __name__ == '__main__':
    unittest.main()
