from PyQt5.QtCore import QRectF, pyqtSignal
from PyQt5.QtGui import QWheelEvent
from PyQt5.QtWidgets import QGraphicsView


class LiveGraphicView(QGraphicsView):
    zoomed = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.min_width = 100
        self.max_width = "auto"
        self.capturing_data = True

    def wheelEvent(self, event: QWheelEvent):
        if self.capturing_data:
            return

        delta = event.angleDelta().y()
        zoom_factor = 1.001 ** delta
        p0scene = self.mapToScene(event.pos())
        w = self.view_rect().width()
        zooming_in = zoom_factor > 1
        if zooming_in and w / zoom_factor < self.min_width:
            return

        max_width = self.max_width
        if self.max_width == "auto":
            max_width = self.sceneRect().width()
        if not zooming_in and w / zoom_factor > max_width:
            self.update()
            return

        self.scale(zoom_factor, 1)
        p1mouse = self.mapFromScene(p0scene)
        move = p1mouse - event.pos()
        self.horizontalScrollBar().setValue(move.x() + self.horizontalScrollBar().value())
        self.zoomed.emit(zoom_factor)

    def update(self, *__args):
        super().update(*__args)

        yscale = self.transform().m22()
        self.resetTransform()
        self.fitInView(self.sceneRect())
        if yscale != 1.0:
            self.scale(1, yscale / self.transform().m22())  # Restore YScale

        self.horizontalScrollBar().blockSignals(False)

    def view_rect(self) -> QRectF:
        return self.mapToScene(self.rect()).boundingRect()
