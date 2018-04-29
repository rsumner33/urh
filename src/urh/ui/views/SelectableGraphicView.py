from PyQt5.QtCore import QRectF, pyqtSignal, Qt, QPoint
from PyQt5.QtGui import QMouseEvent, QKeyEvent
from PyQt5.QtWidgets import QGraphicsView

from urh import constants
from urh.ui.ROI import ROI
from urh.ui.ZoomableScene import ZoomableScene


class SelectableGraphicView(QGraphicsView):
    sep_area_moving = pyqtSignal(float)
    sep_area_changed = pyqtSignal(float)
    selection_width_changed = pyqtSignal(int)
    selection_height_changed = pyqtSignal(int)
    sel_area_start_end_changed = pyqtSignal(int, int)
    shift_state_changed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.scene_creator = None
        """:type: SceneManager """

        self.mouse_press_pos = None
        """:type: QPoint """

        self.mouse_pos = None
        """:type: QPoint """

        self.grab_start = None
        """:type: QPoint"""

        self.move_y_with_drag = False

        self.xmove = 0

        self.separation_area_moving = False

        self.shift_mode = False # Shift Key currently pressed?
        self.ctrl_mode = False # Ctrl Key currently pressed?

        self.select_all_action = QAction(self.tr("Select all"), self)
        self.select_all_action.setShortcut(QKeySequence.SelectAll)
        self.select_all_action.triggered.connect(self.select_all)
        self.select_all_action.setShortcutContext(Qt.WidgetWithChildrenShortcut)
        self.select_all_action.setIcon(QIcon.fromTheme("edit-select-all"))
        self.addAction(self.select_all_action)

    def scene(self) -> ZoomableScene:
        return super().scene()

    @property
    def selection_area(self) -> HorizontalSelection:
        return self.scene().selection_area

    @selection_area.setter
    def selection_area(self, value):
        self.scene().selection_area = value

    @property
    def has_horizontal_selection(self) -> bool:
        return isinstance(self.scene().selection_area, HorizontalSelection)

    @property
    def hold_shift_to_drag(self) -> bool:
        return constants.SETTINGS.value('hold_shift_to_drag', type=bool)

    def is_pos_in_separea(self, pos: QPoint):
        """
        GraphicViews can override this, if they need a seperation area.
        E.g. EpicGraphic View will do for Demodulated View

        :param pos:
        :return:
        """

        return False

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Shift:
            self.shift_mode = True
            self.shift_state_changed.emit(True)

            if self.hold_shift_to_drag:
                self.setCursor(Qt.OpenHandCursor)
            else:
                self.unsetCursor()
                self.grab_start = None

    def keyReleaseEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Shift:
            self.shift_mode = False
            self.shift_state_changed.emit(False)

            if self.hold_shift_to_drag:
                self.unsetCursor()
                self.grab_start = None
            else:
                self.setCursor(Qt.OpenHandCursor)

    def mousePressEvent(self, event: QMouseEvent):
        if self.scene() is None:
            return

        cursor = self.cursor().shape()
        has_shift_modifier = event.modifiers() == Qt.ShiftModifier
        is_in_shift_mode = (has_shift_modifier and self.hold_shift_to_drag)\
                           or (not has_shift_modifier and not self.hold_shift_to_drag) \
                              and cursor != Qt.SplitHCursor and cursor != Qt.SplitVCursor

        if event.buttons() == Qt.LeftButton and is_in_shift_mode:
            self.setCursor(Qt.ClosedHandCursor)
            self.grab_start = event.pos()
        elif event.buttons() == Qt.LeftButton:
            if self.is_pos_in_separea(self.mapToScene(event.pos())):
                self.separation_area_moving = True
                self.setCursor(Qt.SplitVCursor)

            elif self.selection_area.is_empty or self.selection_area.selected_edge is None:
                # Create new selection
                self.mouse_press_pos = event.pos()
                self.mouse_pos = event.pos()
                scene_pos = self.mapToScene(self.mouse_press_pos)
                self.__set_selection_area(x=scene_pos.x(), y=scene_pos.y(), w=0, h=0)
                self.selection_area.finished = False

            elif self.selection_area.selected_edge is not None:
                self.selection_area.resizing = True

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.scene() is None:
            return

        cursor = self.cursor().shape()

        if self.grab_start is not None:
            move_x = self.grab_start.x() - event.pos().x()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() + move_x)

            if self.move_y_with_drag:
                move_y = self.grab_start.y() - event.pos().y()
                self.verticalScrollBar().setValue(self.verticalScrollBar().value() + move_y)

            self.grab_start = event.pos()
            return

        if self.separation_area_moving:
            y_sep = self.mapToScene(event.pos()).y()
            y = self.sceneRect().y()
            h = self.sceneRect().height()
            if y < y_sep < y + h:
                self.scene().draw_sep_area(y_sep)
                self.sep_area_moving.emit(y_sep)
        elif self.is_pos_in_separea(self.mapToScene(event.pos())):
            self.setCursor(Qt.SplitVCursor)
        elif cursor == Qt.SplitVCursor and self.has_horizontal_selection:
            self.unsetCursor()

        if self.selection_area.finished and not self.selection_area.resizing:
            pos = self.mapToScene(event.pos())
            roi_edge = self.selection_area.get_selected_edge(pos, self.transform())
            if roi_edge is None:
                if (cursor == Qt.SplitHCursor and self.has_horizontal_selection) \
                        or (cursor == Qt.SplitVCursor and not self.has_horizontal_selection):
                    self.unsetCursor()
                    return
            elif roi_edge == 0 or roi_edge == 1:
                if self.has_horizontal_selection:
                    self.setCursor(Qt.SplitHCursor)
                else:
                    self.setCursor(Qt.SplitVCursor)

        if event.buttons() == Qt.LeftButton and self.selection_area.resizing:

            if self.selection_area.selected_edge == 0:
                start = self.mapToScene(event.pos())
                self.__set_selection_area(x=start.x(), y=start.y())
                if self.has_horizontal_selection:
                    self.scroll_mouse(start.x())
                return

            if self.selection_area.selected_edge == 1:
                start = QPoint(self.selection_area.x, self.selection_area.y)
                end = self.mapToScene(event.pos())

                self.__set_selection_area(w=end.x() - start.x(), h=end.y() - start.y())

                if self.has_horizontal_selection:
                    self.scroll_mouse(end.x())

                return

        if self.mouse_press_pos is None:
            return

        self.mouse_pos = event.pos()
        if event.buttons() == Qt.LeftButton and not self.selection_area.finished:
            start = self.mapToScene(self.mouse_press_pos)
            end = self.mapToScene(self.mouse_pos)
            self.__set_selection_area(w=end.x() - start.x(), h=end.y() - start.y())
            if self.has_horizontal_selection:
                self.scroll_mouse(end.x())

    def scroll_mouse(self, mouse_x: int):
        """
        Scrolls the mouse if ROI Selection reaches corner of view

        :param mouse_x:
        :return:
        """
        scrollbar = self.horizontalScrollBar()

        if mouse_x - self.view_rect().x() > self.view_rect().width():
            scrollbar.setValue(scrollbar.value() + 5)

        elif mouse_x < self.view_rect().x():
            scrollbar.setValue(scrollbar.value() - 5)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self.scene() is None:
            return

        cursor = self.cursor().shape()
        if cursor == Qt.ClosedHandCursor:
            self.grab_start = None
            self.setCursor(Qt.OpenHandCursor)

        elif self.separation_area_moving:
            y_sep = self.mapToScene(event.pos()).y()
            y = self.sceneRect().y()
            h = self.sceneRect().height()
            if y_sep < y:
                y_sep = y
            elif y_sep > y + h:
                y_sep = y + h

            self.scene().draw_sep_area(y_sep)
            self.sep_area_moving.emit(y_sep)
            self.separation_area_moving = False
            self.y_sep = y_sep
            self.sep_area_changed.emit(-y_sep)
            self.unsetCursor()

        self.selection_area.finished = True
        self.selection_area.resizing = False
        if not self.ctrl_mode:
            self.unsetCursor()
        self.emit_sel_area_width_changed()
        self.sel_area_start_end_changed.emit(self.selection_area.start, self.selection_area.end)


        self.emit_selection_size_changed()

    def set_horizontal_selection(self, x=None, w=None):
        self.selection_area.setY(self.view_rect().y())
        self.selection_area.height = self.view_rect().height()

        if x is not None:
            x = util.clip(x, self.sceneRect().x(), self.sceneRect().x() + self.sceneRect().width())
            self.selection_area.setX(x)

        if w is not None:
            x = self.selection_area.x
            if x + w < self.sceneRect().x():
                w = self.sceneRect().x() - x
            elif x + w > self.sceneRect().x() + self.sceneRect().width():
                w = (self.sceneRect().x() + self.sceneRect().width()) - x

            self.selection_area.width = w

        self.emit_selection_size_changed()

    def __set_selection_area(self, x=None, y=None, w=None, h=None):
        if self.has_horizontal_selection:
            self.set_horizontal_selection(x, w)
        else:
            self.set_vertical_selection(y, h)

    def select_all(self):
        self.__set_selection_area(*self.sceneRect().getCoords())

    def emit_selection_size_changed(self):
        if self.has_horizontal_selection:
            self.selection_width_changed.emit(int(self.selection_area.width))
        else:
            self.selection_height_changed.emit(int(self.selection_area.height))

    def emit_selection_start_end_changed(self):
        self.sel_area_start_end_changed.emit(self.selection_area.start, self.selection_area.end)

    def view_rect(self) -> QRectF:
        """
        Return the boundaries of the view in scene coordinates
        """
        topLeft = self.mapToScene(0, 0)
        bottomRight = self.mapToScene(self.viewport().width() - 1, self.viewport().height() - 1 )
        return QRectF(topLeft, bottomRight)