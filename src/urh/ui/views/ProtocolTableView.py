from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QHeaderView, QAction, QMenu, QActionGroup
from PyQt5.QtGui import QKeySequence, QDropEvent
import numpy

from urh import constants
from urh.signalprocessing.ProtocoLabel import ProtocolLabel
from urh.models.ProtocolTableModel import ProtocolTableModel
from urh.ui.views.TableView import TableView


class ProtocolTableView(TableView):
    show_interpretation_clicked = pyqtSignal(int, int, int, int)
    selection_changed = pyqtSignal()
    protocol_view_change_clicked = pyqtSignal(int)
    row_visibilty_changed = pyqtSignal()
    writeable_changed = pyqtSignal(bool)
    crop_sync_clicked = pyqtSignal()
    revert_sync_cropping_wanted = pyqtSignal()
    edit_label_clicked = pyqtSignal(ProtocolLabel)
    files_dropped = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)

        self.ref_block_action = QAction("Mark as reference block", self)
        self.ref_block_action.setShortcut(QKeySequence("R"))
        self.ref_block_action.setShortcutContext(Qt.WidgetWithChildrenShortcut)
        self.ref_block_action.triggered.connect(self.set_ref_block)

        self.hide_row_action = QAction("Hide selected Rows", self)
        self.hide_row_action.setShortcut(QKeySequence("H"))
        self.hide_row_action.setShortcutContext(Qt.WidgetWithChildrenShortcut)
        self.hide_row_action.triggered.connect(self.hide_row)

        self.addAction(self.ref_block_action)
        self.addAction(self.hide_row_action)

    def model(self) -> ProtocolTableModel:
        return super().model()

    def selectionChanged(self, QItemSelection, QItemSelection_1):
        self.selection_changed.emit()
        super().selectionChanged(QItemSelection, QItemSelection_1)

    def dragMoveEvent(self, event):
        event.accept()

    def dragEnterEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        if len(event.mimeData().urls()) > 0:
            self.files_dropped.emit(event.mimeData().urls())

    def set_ref_block(self, *args, y=None):
        if self.model().refindex == -1:
            return

        if y is None:
            max_row = numpy.max([index.row() for index in self.selectedIndexes()])
            self.model().refindex = max_row
        else:
            self.model().refindex = self.rowAt(y)

    def hide_row(self, *args, y=None):
        if y is None:
            rows = [index.row() for index in self.selectionModel().selectedIndexes()]
        else:
            rows = [self.rowAt(y)]

        refindex = self.model().refindex
        for row in rows:
            if row == refindex:
                refindex += 1
            self.hideRow(row)
            self.model().hidden_rows.add(row)
        if refindex < self.model().row_count:
            self.model().refindex = refindex
        self.model().update()
        self.row_visibilty_changed.emit()

    def contextMenuEvent(self, event):
        menu = QMenu()

        viewgroup = QActionGroup(self)
        viewmenu = menu.addMenu("View")
        bitAction = viewmenu.addAction("Bits")
        bitAction.setCheckable(True)
        hexAction = viewmenu.addAction("Hex")
        hexAction.setCheckable(True)
        asciiAction = viewmenu.addAction("ASCII")
        asciiAction.setCheckable(True)
        bitAction.setActionGroup(viewgroup)
        hexAction.setActionGroup(viewgroup)
        asciiAction.setActionGroup(viewgroup)

        if self.model().proto_view == 0:
            bitAction.setChecked(True)
        elif self.model().proto_view == 1:
            hexAction.setChecked(True)
        elif self.model().proto_view == 2:
            asciiAction.setChecked(True)

        menu.addSeparator()
        row = self.rowAt(event.pos().y())
        cols = [index.column() for index in self.selectionModel().selectedIndexes() if index.row() == row]
        cols.sort()
        try:
            selected_label = self.controller.get_labels_from_selection(row, row, cols[0],
                                                                      cols[-1])[0]
            editLabelAction = menu.addAction(self.tr("Edit Label ") + selected_label.name)

        except IndexError:
            editLabelAction = 42
            selected_label = None

        try:
            data = self.model().display_data[row]
            if len(cols) <= 10:
                val_string = data[cols[0]:cols[-1] + 1]
            else:
                val_string = data[cols[0]:cols[0] + 5] + " ... " + data[cols[-1] - 4:cols[-1] + 1]
            labelMenu = menu.addMenu(self.tr("Add Protocol Label"))
            restrictiveLabelAction = labelMenu.addAction(self.tr("Match exactly " + val_string))
            unrestrictiveLabelAction = labelMenu.addAction(
            self.tr("Match range {0:d}-{1:d} only".format(cols[0] + 1, cols[-1] + 1)))
        except (IndexError, TypeError):
            labelMenu = 42
            restrictiveLabelAction = 42
            unrestrictiveLabelAction = 42

        if not self.model().is_writeable:
            showInterpretationAction = menu.addAction(self.tr("Show in Interpretation"))
        else:
            showInterpretationAction = 42

        menu.addSeparator()
        menu.addAction(self.hide_row_action)
        hidden_rows = self.model().hidden_rows
        showRowAction = 42
        if len(hidden_rows) > 0:
            showRowAction = menu.addAction(self.tr("Show all rows (reset {0:d} hidden)".format(len(hidden_rows))))

        alignmentAction = 42
        removeAlignment = 1337
        # Code für Alignment. Deaktiviert.
        # if self.model().proto_view == 0:
        # menu.addSeparator()
        # alignmentAction = menu.addAction(self.tr("Align Hex from this column on"))
        # if self.columnAt(event.pos().x()) in self.model().protocol.bit_alignment_positions:
        #    removeAlignment = menu.addAction(self.tr("Remove this Alignment"))

        if self.model().refindex != -1:
            menu.addAction(self.ref_block_action)

        menu.addSeparator()
        if self.model().is_writeable:
            writeAbleAction = menu.addAction(self.tr("Writeable"))
            writeAbleAction.setCheckable(True)
            writeAbleAction.setChecked(True)
        else:
            writeAbleAction = menu.addAction(self.tr("Writeable (decouples from signal)"))
            writeAbleAction.setCheckable(True)
            writeAbleAction.setChecked(False)

        pos = event.pos()
        row = self.rowAt(pos.y())
        min_row, max_row, start, end = self.selection_range()
        menu.addSeparator()
        undo_stack = self.model().undo_stack
        view = self.model().proto_view

        for plugin in self.controller.plugin_manager.protocol_plugins:
            if plugin.enabled:
                act = plugin.get_action(self, undo_stack, self.selection_range(),
                                        self.controller.proto_analyzer, view)
                if act is not None:
                    menu.addAction(act)

        action = menu.exec_(self.mapToGlobal(pos))
        if action == self.ref_block_action:
            self.set_ref_block(y=pos.y())
        elif action == editLabelAction:
            self.edit_label_clicked.emit(selected_label)
        elif action == restrictiveLabelAction:
            self.model().addProtoLabel(start, end - 1, row, True)
        elif action == unrestrictiveLabelAction:
            self.model().addProtoLabel(start, end - 1, row, False)
        elif action == showInterpretationAction:
            self.show_interpretation_clicked.emit(min_row, start, max_row, end - 1)
        elif action == showRowAction:
            for i in hidden_rows:
                self.showRow(i)
            self.model().hidden_rows.clear()
            self.model().update()
            self.row_visibilty_changed.emit()
        elif action == alignmentAction:
            col = self.columnAt(pos.x())
            self.model().protocol.add_bit_alignment(col)
            #self.model().protocol.bit_alignment_positions.append(col)
            self.model().update()
        elif action == removeAlignment:
            col = self.columnAt(pos.x())
            self.model().protocol.remove_bit_alignment(col)
            #self.model().protocol.bit_alignment_positions.remove(col)
            self.model().update()
        elif action == bitAction:
            self.protocol_view_change_clicked.emit(0)
        elif action == hexAction:
            self.protocol_view_change_clicked.emit(1)
        elif action == asciiAction:
            self.protocol_view_change_clicked.emit(2)
        elif action == writeAbleAction:
            self.writeable_changed.emit(writeAbleAction.isChecked())
