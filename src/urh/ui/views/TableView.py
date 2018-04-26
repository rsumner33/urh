from PyQt5.QtCore import Qt, QItemSelectionModel, QItemSelection
from PyQt5.QtGui import QKeySequence, QKeyEvent
from PyQt5.QtWidgets import QTableView, QApplication
import numpy


class TableView(QTableView):
    def __init__(self, parent=None):

        super().__init__(parent)

    def selectionModel(self) -> QItemSelectionModel:
        return super().selectionModel()

    def selection_range(self):
        """
        :rtype: int, int, int, int
        """
        selected = self.selectionModel().selection()
        """:type: QItemSelection """

        if selected.isEmpty():
            return -1, -1, -1, -1

        min_row = numpy.min([rng.top() for rng in selected])
        max_row = numpy.max([rng.bottom() for rng in selected])
        start = numpy.min([rng.left() for rng in selected])
        end = numpy.max([rng.right() for rng in selected]) + 1

        return min_row, max_row, start, end

    def select(self, row_1, col_1, row_2, col_2):
        sel = QItemSelection()
        startindex = self.model().index(row_1, col_1)
        endindex = self.model().index(row_2, col_2)
        sel.select(startindex, endindex)
        self.selectionModel().select(sel, QItemSelectionModel.Select)

    def resize_it(self):
        if not self.isVisible():
            return

        w = self.font().pointSize() + 2

        for i in range(10):
            self.setColumnWidth(i, 2 * w)

        QApplication.processEvents()
        for i in range(10, self.model().columnCount()):
            self.setColumnWidth(i, w * len(str(i + 1)))
            if i % 10 == 0:
                QApplication.processEvents()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Delete:
            selected = self.selectionModel().selection()
            """:type: QtGui.QItemSelection """
            if selected.isEmpty():
                return

            min_row = numpy.min([rng.top() for rng in selected])
            max_row = numpy.max([rng.bottom() for rng in selected])
            start = numpy.min([rng.left() for rng in selected])
            end = numpy.max([rng.right() for rng in selected])

            self.model().delete_range(min_row, max_row, start, end)

        if event.matches(QKeySequence.Copy):
            cells = self.selectedIndexes()
            cells.sort()
            currentRow = 0
            text = ""

            for cell in cells:
                if len(text) > 0 and cell.row() != currentRow:
                    text += "\n"
                currentRow = cell.row()
                text += str(cell.data())

            QApplication.clipboard().setText(text)
            return

        if event.key() not in (Qt.Key_Right, Qt.Key_Left, Qt.Key_Up, Qt.Key_Down) \
                or event.modifiers() == Qt.ShiftModifier:
            super().keyPressEvent(event)
            return

        sel = self.selectionModel().selectedIndexes()
        cols = [i.column() for i in sel]
        rows = [i.row() for i in sel]
        if len(cols) == 0 or len(rows) == 0:
            super().keyPressEvent(event)
            return

        mincol, maxcol = numpy.min(cols), numpy.max(cols)
        minrow, maxrow = numpy.min(rows), numpy.max(rows)
        scroll_to_start = True

        if event.key() == Qt.Key_Right and maxcol < self.model().col_count - 1:
            maxcol += 1
            mincol += 1
            scroll_to_start = False
        elif event.key() == Qt.Key_Left and mincol > 0:
            mincol -= 1
            maxcol -= 1
        elif event.key() == Qt.Key_Down and maxrow < self.model().row_count - 1:
            first_unhidden = -1
            for row in range(maxrow + 1, self.model().row_count):
                if not self.isRowHidden(row):
                    first_unhidden = row
                    break

            if first_unhidden != -1:
                sel_len = maxrow - minrow
                maxrow = first_unhidden
                minrow = maxrow - sel_len
                scroll_to_start = False
        elif event.key() == Qt.Key_Up and minrow > 0:
            first_unhidden = -1
            for row in range(minrow - 1, -1, -1):
                if not self.isRowHidden(row):
                    first_unhidden = row
                    break

            if first_unhidden != -1:
                sel_len = maxrow - minrow
                minrow = first_unhidden
                maxrow = minrow + sel_len

        start = self.model().index(minrow, mincol)
        end = self.model().index(maxrow, maxcol)

        selctn = QItemSelection()
        selctn.select(start, end)
        self.selectionModel().setCurrentIndex(end, QItemSelectionModel.ClearAndSelect)
        self.selectionModel().select(selctn, QItemSelectionModel.ClearAndSelect)
        if scroll_to_start:
            self.scrollTo(start)
        else:
            self.scrollTo(end)
