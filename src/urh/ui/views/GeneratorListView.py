from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QContextMenuEvent, QKeyEvent
from PyQt5.QtWidgets import  QListView, QMenu

from urh.models.GeneratorListModel import GeneratorListModel


class GeneratorListView(QListView):
    editActionTriggered = pyqtSignal(int)
    selection_changed = pyqtSignal()
    editAllActionTriggered = pyqtSignal()
    edit_on_item_triggered = pyqtSignal(int)

    def __init__(self, parent):
        super().__init__(parent)

    def model(self) -> GeneratorListModel:
        return super().model()

    def contextMenuEvent(self, event: QContextMenuEvent):
        menu = QMenu()
        pos = event.pos()
        index = self.indexAt(pos)
        if len(self.model().proto_container.protocol_labels) == 0:
            return

        editAction = menu.addAction("Edit Fuzzing Label...")
        delAction = 42
        if index.isValid():
            delAction = menu.addAction("Delete Fuzzing Label")
        editAllAction = menu.addAction("Edit all Fuzzing Values...")


        menu.addSeparator()
        fuzzAllAction = menu.addAction("Check all")
        unfuzzAllAction = menu.addAction("Uncheck all")

        action = menu.exec_(self.mapToGlobal(pos))
        if action == delAction:
            self.model().delete_label_at(index.row())
        elif action == editAction:
            self.editActionTriggered.emit(index.row())
        elif action == fuzzAllAction:
            self.model().fuzzAll()
        elif action == unfuzzAllAction:
            self.model().unfuzzAll()
        elif action == editAllAction:
            self.editAllActionTriggered.emit()

    def selectionChanged(self, QItemSelection, QItemSelection_1):
        self.selection_changed.emit()
        super().selectionChanged(QItemSelection, QItemSelection_1)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key_Enter, Qt.Key_Return):
            selected = [index.row() for index in self.selectedIndexes()]
            if len(selected) > 0:
                self.edit_on_item_triggered.emit(min(selected))
        else:
            super().keyPressEvent(event)

    def mouseDoubleClickEvent(self, QMouseEvent):
        selected = [index.row() for index in self.selectedIndexes()]
        if len(selected) > 0:
            self.edit_on_item_triggered.emit(min(selected))
