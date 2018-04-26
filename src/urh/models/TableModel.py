from collections import defaultdict

import numpy
from PyQt5.QtCore import QAbstractTableModel, QModelIndex, Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QUndoStack, QMessageBox

from urh import constants
from urh.cythonext.signalFunctions import Symbol


class TableModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.controller = None
        """:type: CompareFrameController or GeneratorTabController """
        self.protocol = None # Reimplement in Child classes
        """:type: ProtocolAnalyzer """

        self.col_count = 0
        self.row_count = 0
        self.display_data = None
        """:type: list[str] """

        self.search_results = []
        self.search_value = ""
        self._proto_view = 0
        self._refindex = -1

        self.first_blocks = []
        self.hidden_rows = set()

        self.is_writeable = False
        self.locked = False
        self.decode = True  # False for Generator

        self.symbols = {}
        """:type: dict[str, Symbol] """

        self.background_colors = defaultdict(lambda: None)
        self.bold_fonts = defaultdict(lambda: False)
        self.text_colors = defaultdict(lambda: None)
        self.tooltips = defaultdict(lambda: None)

        self._diffs = defaultdict(set)
        """:type: dict[int, set[int]] """

        self.undo_stack = QUndoStack()

    @property
    def proto_view(self):
        return self._proto_view

    @proto_view.setter
    def proto_view(self, value):
        self._proto_view = value
        if self._refindex >= 0:
            self._diffs = self.protocol.find_differences(self._refindex, self._proto_view)
        self.update()

    def update(self):
        self.locked = True

        self.symbols.clear()
        self.symbols = {symbol.name: symbol for symbol in self.protocol.used_symbols}

        if self.protocol.num_blocks > 0:
            if self.decode:
                if self.proto_view == 0:
                    self.display_data = self.protocol.decoded_proto_bits_str
                elif self.proto_view == 1:
                    self.display_data = self.protocol.decoded_hex_str
                elif self.proto_view == 2:
                    self.display_data = self.protocol.decoded_ascii_str
            else:
                #
                # Generator Model
                if self.proto_view == 0:
                    self.display_data = self.protocol.plain_bits_str
                elif self.proto_view == 1:
                    self.display_data = self.protocol.plain_hex_str
                else:
                    self.display_data = self.protocol.plain_ascii_str

            visible_blocks = [block for i, block in enumerate(self.display_data) if i not in self.hidden_rows]
            if len(visible_blocks) == 0:
                self.col_count = 0
            else:
                self.col_count = numpy.max([len(block) for block in visible_blocks])

            if self._refindex >= 0:
                self._diffs = self.protocol.find_differences(self._refindex, self.proto_view)
            else:
                self._diffs.clear()

            self.row_count = self.protocol.num_blocks
            self.find_protocol_value(self.search_value)
        else:
            self.col_count = 0
            self.row_count = 0
            self.display_data = None

        # Cache background colors for performance
        self.refresh_bgcolors_and_tooltips()
        self.refresh_fonts()  # Will be overriden

        self.layoutChanged.emit()
        self.locked = False

    def columnCount(self, QModelIndex_parent=None, *args, **kwargs):
        return self.col_count

    def rowCount(self, QModelIndex_parent=None, *args, **kwargs):
        return self.row_count

    def refresh_bgcolors_and_tooltips(self):
        self.background_colors.clear()
        self.tooltips.clear()
        label_colors = constants.LABEL_COLORS

        offset = 0
        for group in self.controller.groups:
            if group in self.controller.active_groups:
                for lbl in group.labels:
                    bg_color = label_colors[lbl.color_index]
                    for i in lbl.block_numbers:
                        start, end = group.get_label_range(lbl, self.proto_view, self.decode)
                        for j in range(start, end):
                            self.background_colors[i+offset, j] = bg_color
                            self.tooltips[i+offset, j] = lbl.name
            offset += group.num_blocks

    def refresh_fonts(self):
        """
        Will be overriden

        :return:
        """
        pass

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        i = index.row()
        j = index.column()
        if role == Qt.DisplayRole and self.display_data:
            try:
                return self.display_data[i][j]
            except IndexError:
                return None

        elif role == Qt.TextAlignmentRole:
            if i in self.first_blocks:
                return Qt.AlignHCenter + Qt.AlignBottom
            else:
                return Qt.AlignCenter

        elif role == Qt.BackgroundColorRole:
            return self.background_colors[i, j]

        elif role == Qt.FontRole and self.bold_fonts[i, j]:
            font = QFont()
            font.setBold(True)
            return font

        elif role == Qt.TextColorRole:
            return self.text_colors[i, j]

        elif role == Qt.ToolTipRole:
            return self.tooltips[i, j]

        else:
            return None

    def setData(self, index: QModelIndex, value, role=Qt.DisplayRole):
        if role == Qt.EditRole:
            i = index.row()
            j = index.column()
            hex_chars = ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "a", "b", "c", "d", "e", "f")

            if self.proto_view == 0:
                if value in ("0", "1"):
                    self.protocol.blocks[i][j] = bool(int(value))
                    self.controller.refresh_protocol_labels()
                    self.update()
                elif value in self.symbols.keys():
                    self.protocol.blocks[i][j] = self.symbols[value]
                    self.controller.refresh_protocol_labels()
                    self.update()
            elif self.proto_view == 1:
                if value in hex_chars:
                    index = self.protocol.convert_index(j, 1, 0, True, block_indx=i)[0]
                    bits = "{0:04b}".format(int(value, 16))
                    for k in range(4):
                        try:
                            if type(self.protocol.blocks[i][index + k]) != Symbol:
                                self.protocol.blocks[i][index + k] = bool(int(bits[k]))
                            else:
                                break
                        except IndexError:
                            break
                    self.controller.refresh_protocol_labels()
                    self.update()
                elif value in self.symbols.keys():
                    QMessageBox.information(None, "Setting symbol", "You can only set custom bit symbols in bit view!")
            elif self.proto_view == 2 and len(value) == 1:
                if value in self.symbols.keys():
                    QMessageBox.information(None, "Setting symbol", "You can only set custom bit symbols in bit view!")

                index = self.protocol.convert_index(j, 2, 0, True, block_indx=i)[0]
                bits = "{0:08b}".format(ord(value))
                for k in range(8):
                    try:
                        if type(self.protocol.blocks[i][index + k]) != Symbol:
                            self.protocol.blocks[i][index + k] = bool(int(bits[k]))
                        else:
                            break
                    except IndexError:
                        break

                self.controller.refresh_protocol_labels()
                self.update()
        return True

    def find_protocol_value(self, value):
        self.search_results[:] = []
        self.search_value = value

        if len(value) == 0:
            return 0

        for i, block in enumerate(self.display_data):
            if i in self.hidden_rows:
                continue

            j = block.find(value)
            while j != -1:
                self.search_results.append((i, j))
                j = block.find(value, j + 1)

        return len(self.search_results)
