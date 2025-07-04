import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFileDialog, QListWidget, QLineEdit, QMessageBox, QSpinBox, QListWidgetItem
)
from PyQt5.QtCore import Qt, QSize, QSettings
from PyQt5.QtGui import QDragEnterEvent, QDropEvent, QPixmap, QIcon
from PIL import Image

# 可拖拽的图片列表，支持缩略图
class DraggableListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setIconSize(QSize(72, 72))
        self.setViewMode(QListWidget.IconMode)
        self.setResizeMode(QListWidget.Adjust)
        self.setSpacing(8)
        self.setMovement(QListWidget.Static)
        self.setSelectionMode(QListWidget.ExtendedSelection)
        self.setStyleSheet("QListWidget { border: 2px dashed #888; border-radius: 8px; background: #222; }")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dragLeaveEvent(self, event):
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            paths = [url.toLocalFile() for url in event.mimeData().urls()]
            self.parent().add_images_from_paths(paths)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

class DraggableLineEdit(QLineEdit):
    def __init__(self, parent=None, dir_only=False):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.dir_only = dir_only

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            path = event.mimeData().urls()[0].toLocalFile()
            if self.dir_only and not os.path.isdir(path):
                return
            self.setText(path)
            event.acceptProposedAction()
        else:
            event.ignore()

class BatchImageResizer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("批量图片尺寸修改器")
        self.resize(700, 500)
        self.image_paths = []  # 用列表保证顺序
        self.setAcceptDrops(True)  # 支持主窗口拖拽
        self.settings = QSettings("gbox", "batch_image_resizer")
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        layout = QVBoxLayout()

        # 图片列表及下方按钮和宽高
        layout.addWidget(QLabel("图片列表（可多选添加/拖拽图片或目录）:"))
        self.list_widget = DraggableListWidget(self)
        layout.addWidget(self.list_widget, 1)
        h2 = QHBoxLayout()
        # 左侧：添加、删除、清空图片
        btn_add = QPushButton("添加")
        btn_add.setStyleSheet("QPushButton { background-color: #4ADE80; color: #222; border-radius: 8px; padding: 4px 18px; font-size: 14px; }")
        btn_add.clicked.connect(self.add_images)
        btn_delete = QPushButton("删除")
        btn_delete.setStyleSheet("QPushButton { background-color: #F87171; color: #222; border-radius: 8px; padding: 4px 18px; font-size: 14px; }")
        btn_delete.clicked.connect(self.delete_selected_images)
        btn_clear = QPushButton("清空")
        btn_clear.setStyleSheet("QPushButton { background-color: #64748B; color: #fff; border-radius: 8px; padding: 4px 18px; font-size: 14px; }")
        btn_clear.clicked.connect(self.clear_images)
        h2.addWidget(btn_add)
        h2.addWidget(btn_delete)
        h2.addWidget(btn_clear)
        h2.addStretch(1)
        # 右侧：宽高
        h2.addWidget(QLabel("宽(px):"))
        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 10000)
        self.width_spin.setValue(512)
        h2.addWidget(self.width_spin)
        h2.addWidget(QLabel("高(px):"))
        self.height_spin = QSpinBox()
        self.height_spin.setRange(1, 10000)
        self.height_spin.setValue(512)
        h2.addWidget(self.height_spin)
        layout.addLayout(h2)

        # 输出目录
        h4 = QHBoxLayout()
        self.output_dir_edit = DraggableLineEdit(self, dir_only=True)
        self.output_dir_edit.setPlaceholderText("可手动输入或拖拽输出目录")
        btn_output = QPushButton("选择输出目录")
        btn_output.setStyleSheet("QPushButton { background-color: #3B82F6; color: #fff; border-radius: 8px; padding: 4px 18px; font-size: 14px; }")
        btn_output.clicked.connect(self.select_output_dir)
        h4.addWidget(QLabel("输出目录:"))
        h4.addWidget(self.output_dir_edit)
        h4.addWidget(btn_output)
        layout.addLayout(h4)

        # 执行按钮
        btn_resize = QPushButton("批量修改尺寸")
        btn_resize.setStyleSheet("QPushButton { background-color: #3B82F6; color: #fff; border-radius: 8px; padding: 8px 32px; font-weight: bold; font-size: 16px; }")
        btn_resize.clicked.connect(self.resize_images)
        layout.addWidget(btn_resize)

        self.setLayout(layout)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            paths = [url.toLocalFile() for url in event.mimeData().urls()]
            self.add_images_from_paths(paths)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

    def select_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if dir_path:
            self.output_dir_edit.setText(dir_path)
            self.save_settings()

    def add_images(self):
        files, _ = QFileDialog.getOpenFileNames(self, "选择图片", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp)")
        self.add_images_from_paths(files)
        self.save_settings()

    def clear_images(self):
        self.image_paths = []
        self.refresh_list()
        self.save_settings()

    def add_images_from_paths(self, paths):
        exts = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp')
        new_paths = []
        for path in paths:
            if os.path.isdir(path):
                for root, _, files in os.walk(path):
                    for file in files:
                        if file.lower().endswith(exts):
                            img_path = os.path.join(root, file)
                            if img_path not in self.image_paths and img_path not in new_paths:
                                new_paths.append(img_path)
            elif path.lower().endswith(exts):
                if os.path.isfile(path) and path not in self.image_paths and path not in new_paths:
                    new_paths.append(path)
        self.image_paths.extend(new_paths)
        self.refresh_list()
        self.save_settings()

    def delete_selected_images(self):
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            return
        selected_paths = set()
        for item in selected_items:
            idx = self.list_widget.row(item)
            if 0 <= idx < len(self.image_paths):
                selected_paths.add(self.image_paths[idx])
        self.image_paths = [p for p in self.image_paths if p not in selected_paths]
        self.refresh_list()
        self.save_settings()

    def refresh_list(self):
        self.list_widget.clear()
        for path in self.image_paths:
            item = QListWidgetItem()
            # 生成缩略图
            try:
                pixmap = QPixmap(path)
                if not pixmap.isNull():
                    icon = QIcon(pixmap.scaled(72, 72, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                    item.setIcon(icon)
            except Exception:
                pass
            item.setToolTip(path)
            self.list_widget.addItem(item)

    def resize_images(self):
        if not self.image_paths:
            QMessageBox.warning(self, "警告", "请先选择或添加图片")
            return
        width = self.width_spin.value()
        height = self.height_spin.value()
        output_dir = self.output_dir_edit.text()
        if not output_dir:
            QMessageBox.warning(self, "警告", "请选择输出目录")
            return
        count = 0
        for img_path in self.image_paths:
            try:
                img = Image.open(img_path)
                img = img.resize((width, height), Image.LANCZOS)
                base = os.path.basename(img_path)
                out_path = os.path.join(output_dir, base)
                img.save(out_path)
                count += 1
            except Exception as e:
                print(f"处理失败: {img_path}, 错误: {e}")
        QMessageBox.information(self, "完成", f"已处理 {count} 张图片")

    def save_settings(self):
        self.settings.setValue("output_dir", self.output_dir_edit.text())
        self.settings.setValue("width", self.width_spin.value())
        self.settings.setValue("height", self.height_spin.value())

    def load_settings(self):
        output_dir = self.settings.value("output_dir", "")
        width = int(self.settings.value("width", 512))
        height = int(self.settings.value("height", 512))
        self.output_dir_edit.setText(output_dir)
        self.width_spin.setValue(width)
        self.height_spin.setValue(height)
        self.image_paths = []
        self.refresh_list()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = BatchImageResizer()
    win.show()
    sys.exit(app.exec_())