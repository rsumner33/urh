import unittest

from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest

import tests.startApp
from urh import constants
from urh.controller.MainController import MainController

app = tests.startApp.app


class TestLabels(unittest.TestCase):
    def setUp(self):
        self.old_sym_len = constants.SETTINGS.value('rel_symbol_length', type=int)
        constants.SETTINGS.setValue('rel_symbol_length', 0) # Disable Symbols for this Test

        QTest.qWait(100)

        self.form = MainController()
        self.form.add_signalfile("./data/esaver.complex")
        QTest.qWait(100)

        self.sframe = self.form.signal_tab_controller.signal_frames[0]
        self.cframe = self.form.compare_frame_controller
        self.gframe = self.form.generator_tab_controller

        # Create two labels on Compare Frame
        self.form.ui.tabWidget.setCurrentIndex(1)
        self.cframe.add_protocol_label(0, 40, 1, 0, True, edit_label_name = False)  # Sync
        self.cframe.add_protocol_label(43, 43, 2, 0, True, edit_label_name = False)  # FuzzBit

    def tearDown(self):
        constants.SETTINGS.setValue('rel_symbol_length', self.old_sym_len) # Restore Symbol Length

    def test_show_labels_only(self):
        self.cframe.ui.chkBoxOnlyShowLabelsInProtocol.setChecked(True)
        QTest.qWait(10)
        for i in range(0, 40):
            self.assertFalse(self.cframe.ui.tblViewProtocol.isColumnHidden(i), msg = "Bit " + str(i))
        self.assertFalse(self.cframe.ui.tblViewProtocol.isColumnHidden(43), msg = "Bit 43")
        for i in range(44, self.cframe.protocol_model.col_count):
            self.assertTrue(self.cframe.ui.tblViewProtocol.isColumnHidden(i), msg = "Bit " + str(i))

        self.cframe.ui.cbProtoView.setCurrentIndex(1)  # Hex View
        QTest.qWait(10)
        for i in range(0, 10):
            self.assertFalse(self.cframe.ui.tblViewProtocol.isColumnHidden(i), msg = "Hex " + str(i))
        for i in range(13, self.cframe.protocol_model.col_count):
            self.assertTrue(self.cframe.ui.tblViewProtocol.isColumnHidden(i), msg = "Hex " + str(i))


    def test_generator_label(self):

        labels = self.cframe.groups[0].labels
        self.assertEqual(len(labels), 2)
        self.assertEqual(labels[0].reference_bits, "10101010101010101010101010101010101010101")
        self.assertEqual(labels[1].reference_bits, "1")
        self.assertEqual(len(labels[0].block_numbers), 3)
        self.assertEqual(labels[0].refblock, 1)
        self.assertEqual(labels[1].refblock, 2)

        # Open Protocol in Generator
        self.form.ui.tabWidget.setCurrentIndex(2)
        item = self.gframe.tree_model.rootItem.children[0].children[0]
        index = self.gframe.tree_model.createIndex(0, 0, item)
        rect = self.gframe.ui.treeProtocols.visualRect(index)
        self.assertEqual(len(self.gframe.ui.treeProtocols.selectedIndexes()), 0)
        QTest.mousePress(self.gframe.ui.treeProtocols.viewport(), Qt.LeftButton, pos=rect.center())
        self.assertEqual(self.gframe.ui.treeProtocols.selectedIndexes()[0], index)
        mimedata = self.gframe.tree_model.mimeData(self.gframe.ui.treeProtocols.selectedIndexes())
        self.gframe.table_model.dropMimeData(mimedata, 1, -1, -1, self.gframe.table_model.createIndex(0, 0))
        self.assertEqual(self.gframe.table_model.row_count, 3)

        # Check Label in Generator
        labels = self.gframe.table_model.protocol.protocol_labels
        self.assertEqual(len(labels), 2)
        self.assertEqual(labels[0].reference_bits, "10101010101010101010101010101010101010101")
        self.assertEqual(labels[1].reference_bits, "1")
        self.assertEqual(len(labels[0].block_numbers), 3)
        self.assertEqual(labels[0].refblock, 1)

        # Fuzz Label
        lbl = labels[1]
        lbl.fuzz_values.append("1")
        lbl.add_fuzz_value()
        lbl.add_fuzz_value()
        lbl.add_fuzz_value()
        lbl.add_fuzz_value()
        lbl.fuzz_me = Qt.Checked
        self.assertEqual(len(lbl.fuzz_values), 5)
        self.gframe.refresh_label_list()
        self.gframe.refresh_table()
        self.gframe.ui.btnFuzz.setEnabled(True)
        self.gframe.ui.btnFuzz.click()
        self.assertEqual(self.gframe.table_model.row_count, 4 + 3)
        self.assertEqual(lbl.refblock, 2)

        # Check if Background for fuzzed labels is drawn correctly
        self.__check_background_is_drawn(lbl, 43, 43)

        # Delete a line
        old_row_count = self.gframe.table_model.row_count
        self.gframe.ui.tableBlocks.selectRow(2)
        QTest.keyClick(self.gframe.ui.tableBlocks, Qt.Key_Delete)
        self.assertEqual(self.gframe.table_model.row_count, old_row_count - 1)

        self.__check_background_is_drawn(lbl, 43, 43)

        # Remove everything
        for i in range(old_row_count):
            self.gframe.ui.tableBlocks.selectRow(0)
            QTest.keyClick(self.gframe.ui.tableBlocks, Qt.Key_Delete)

        self.assertEqual(self.gframe.table_model.row_count, 0)

    def __check_background_is_drawn(self, lbl, lbl_start, lbl_end):
        pac = self.gframe.table_model.protocol
        for i in range(self.gframe.table_model.row_count):
            labels_for_block = pac.blocks[i].fuzz_labels
            self.assertIn(lbl, labels_for_block)
            start, end = pac.get_label_range(lbl, self.gframe.table_model.proto_view, False)
            self.assertEqual(start, lbl_start)
            self.assertEqual(end, lbl_end + 1)
