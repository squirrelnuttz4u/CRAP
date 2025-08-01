# visual_canvas.py
# © 2025 Colt McVey
# The node-based visual canvas for architectural design.

import sys
import uuid
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene,
    QGraphicsItem, QGraphicsRectItem, QGraphicsTextItem, QGraphicsPathItem,
    QToolBar, QMenu, QGraphicsSceneMouseEvent
)
from PySide6.QtCore import Qt, QPointF, QRectF, Signal
from PySide6.QtGui import QFont, QPen, QBrush, QColor, QPainterPath, QAction, QIcon, QPainter

# Import from the new ui_utils file
from ui_utils import create_icon_from_svg, SVG_ICONS

# --- Node Classes ---

class BaseNode(QGraphicsItem):
    """A customizable node in the visual canvas that links to a notebook."""
    def __init__(self, name: str, color: QColor = QColor("#34495e")):
        super().__init__()
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        
        self.node_name = name
        self.node_color = color
        self.width = 150
        self.height = 80
        
        # Each node has a unique ID that can be linked to a notebook
        self.notebook_id = str(uuid.uuid4())

        # Create input/output ports
        self.inputs = []
        self.outputs = []
        self._add_port("In", is_input=True)
        self._add_port("Out", is_input=False)

    def _add_port(self, name, is_input=True):
        port = QGraphicsRectItem(0, 0, 10, 10, self)
        port.setBrush(QBrush(QColor("#95a5a6")))
        if is_input:
            self.inputs.append(port)
        else:
            self.outputs.append(port)
        self._position_ports()

    def _position_ports(self):
        for i, port in enumerate(self.inputs):
            port.setPos(-port.rect().width(), (self.height / (len(self.inputs) + 1)) * (i + 1) - port.rect().height() / 2)
        for i, port in enumerate(self.outputs):
            port.setPos(self.width, (self.height / (len(self.outputs) + 1)) * (i + 1) - port.rect().height() / 2)

    def boundingRect(self) -> QRectF:
        return QRectF(-10, 0, self.width + 20, self.height)

    def paint(self, painter, option, widget):
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width, self.height, 10, 10)
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.setBrush(QBrush(self.node_color))
        painter.drawPath(path)

        title_rect = QRectF(0, 0, self.width, 20)
        title_path = QPainterPath()
        title_path.addRoundedRect(title_rect, 10, 10)
        painter.setBrush(QBrush(self.node_color.darker(120)))
        painter.drawPath(title_path)
        
        painter.setPen(Qt.GlobalColor.white)
        painter.setFont(QFont("Inter", 10, QFont.Weight.Bold))
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignCenter, self.node_name)

    def mouseDoubleClickEvent(self, event: QGraphicsSceneMouseEvent):
        """Emit a signal when the node is double-clicked."""
        self.scene().node_double_clicked.emit(self.notebook_id, self.node_name)
        super().mouseDoubleClickEvent(event)

# --- Custom Scene ---
class CanvasScene(QGraphicsScene):
    """A custom scene to handle node signals."""
    node_double_clicked = Signal(str, str) # notebook_id, node_name

# --- Visual Canvas Widget ---
class VisualCanvasWidget(QWidget):
    """The main widget containing the canvas and its tools."""
    open_notebook_for_node = Signal(str, str)

    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.scene = CanvasScene()
        self.scene.setSceneRect(0, 0, 5000, 5000)
        self.scene.node_double_clicked.connect(self.on_node_activated)

        toolbar = QToolBar()
        add_func_action = QAction(create_icon_from_svg(SVG_ICONS["add_code"]), "Add Function Node", self)
        add_func_action.triggered.connect(lambda: self.add_node("Function"))
        add_data_action = QAction(create_icon_from_svg(SVG_ICONS["run_tests"]), "Add Data Node", self)
        add_data_action.triggered.connect(lambda: self.add_node("Data Source"))
        toolbar.addAction(add_func_action)
        toolbar.addAction(add_data_action)

        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        
        main_layout.addWidget(toolbar)
        main_layout.addWidget(self.view)
        
        self.add_node("User Input", QPointF(100, 100))
        self.add_node("Process Data", QPointF(400, 150))

    def add_node(self, name, pos=QPointF(200, 200)):
        node = BaseNode(name)
        node.setPos(pos)
        self.scene.addItem(node)

    def on_node_activated(self, notebook_id: str, node_name: str):
        """Relay the signal from the scene to the main window."""
        self.open_notebook_for_node.emit(notebook_id, node_name)
