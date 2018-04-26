import os
import unittest

from PyQt5.QtCore import QDir
from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest

import tests.startApp
from urh.controller.MainController import MainController

app = tests.startApp.app


class TestGenerator(unittest.TestCase):
    def setUp(self):
        self.form = MainController()

    def test_generation(self):
        """
        Complex test including much functionality
        1) Load a Signal
        2) Set Decoding in Compareframe
        3) Move with encoding to Generator
        4) Generate datafile
        5) Read datafile and compare with original signal

        """
        # Load a Signal
        self.form.add_signalfile("./data/ask.complex")
        QTest.qWait(10)
        sframe = self.form.signal_tab_controller.signal_frames[0]
        sframe.ui.cbSignalView.setCurrentIndex(1) # ASK
        sframe.ui.spinBoxInfoLen.setValue(295)
        sframe.ui.spinBoxCenterOffset.setValue(-0.1667)
        sframe.refresh()
        QTest.qWait(10)

        proto = "1011001001011011011011011011011011001000000"
        self.assertTrue(sframe.ui.txtEdProto.toPlainText().startswith(proto))

        # Set Decoding
        self.form.ui.tabWidget.setCurrentIndex(1)
        cfc = self.form.compare_frame_controller
        cfc.ui.cbDecoding.setCurrentIndex(1) # NRZ-I
        QTest.qWait(10)
        proto_inv = cfc.proto_analyzer.decoded_proto_bits_str[0]
        self.assertTrue(self.__is_inv_proto(proto, proto_inv))

        # Move with encoding to generator
        gframe = self.form.generator_tab_controller
        item = gframe.tree_model.rootItem.children[0].children[0]
        index = gframe.tree_model.createIndex(0, 0, item)
        rect = gframe.ui.treeProtocols.visualRect(index)
        QTest.mousePress(gframe.ui.treeProtocols.viewport(), Qt.LeftButton, pos = rect.center())
        self.assertEqual(gframe.ui.treeProtocols.selectedIndexes()[0], index)
        mimedata = gframe.tree_model.mimeData(gframe.ui.treeProtocols.selectedIndexes())
        gframe.table_model.dropMimeData(mimedata, 1, -1, -1, gframe.table_model.createIndex(0, 0))
        self.assertEqual(proto_inv, gframe.table_model.display_data[0])
        self.assertNotEqual(proto, gframe.table_model.display_data[0])

        # Generate Datafile
        modulator = gframe.modulators[0]
        modulator.modulation_type = 0
        modulator.samples_per_bit = 295
        modulated_data = gframe.modulate_data()
        filename = os.path.join(QDir.tempPath(), "generator_test.complex")
        modulated_data.tofile(filename)
        QTest.qWait(10)

        # Reload datafile and see if bits match
        self.form.add_signalfile(filename)
        QTest.qWait(10)
        sframe = self.form.signal_tab_controller.signal_frames[1]
        self.assertEqual(sframe.ui.lineEditSignalName.text(), "generator_test")
        sframe.ui.cbSignalView.setCurrentIndex(1)  # ASK
        sframe.ui.spinBoxInfoLen.setValue(295)
        sframe.ui.spinBoxInfoLen.editingFinished.emit()
        sframe.ui.spinBoxCenterOffset.setValue(0.1)
        sframe.ui.spinBoxCenterOffset.editingFinished.emit()
        sframe.refresh()
        QTest.qWait(10)

        gen_proto = sframe.ui.txtEdProto.toPlainText()
        gen_proto = gen_proto[:gen_proto.index(" ")]
        self.assertTrue(proto.startswith(gen_proto))

    def __is_inv_proto(self, proto1: str, proto2: str):
        if len(proto1) != len(proto2):
            return False

        for c1, c2 in zip(proto1, proto2):
            if not self.__is_inv_bits(c1, c2):
                return False

        return True

    def __is_inv_bits(self, a: str, b: str):
        # We only check bits here
        if a not in ("0", "1") or b not in ("0", "1"):
            return True

        if a == "0" and b == "1":
            return True
        if a == "1" and b == "0":
            return True
        return False
