from PyQt5.QtGui import QContextMenuEvent
from PyQt5.QtWidgets import QTreeView, QInputDialog, QMessageBox, QMenu


class DirectoryTreeView(QTreeView):
    def __init__(self, parent=None):
        super().__init__(parent)

    def create_directory(self):
        index = self.currentIndex()
        """:type: QModelIndex """

        if not index.isValid():
            return

        dir_name, ok = QInputDialog.getText(self, self.tr("Create Directory"), self.tr("Directory name"))

        if ok and len(dir_name) > 0:
            if not self.model().mkdir(index, dir_name).isValid():
                QMessageBox.information(self, self.tr("Create Directoy"), self.tr("Failed to create the directory"))

    def remove(self):
        index = self.model().mapToSource(self.currentIndex())
        if not index.isValid():
            return

        model = self.model().sourceModel()
        if model.fileInfo(index).isDir():
            ok = model.rmdir(index)
        else:
            ok = model.remove(index)

        if not ok:
            QMessageBox.information(self, self.tr("Remove"),
                                    self.tr("Failed to remove {0}".format(model.fileName(index))))

    def contextMenuEvent(self, event: QContextMenuEvent):
        menu = QMenu(self)
        newdirAction = menu.addAction("New Directory")
        delAction = menu.addAction("Delete")

        action = menu.exec_(self.mapToGlobal(event.pos()))

        if action == newdirAction:
            self.create_directory()

        elif action == delAction:
            self.remove()
