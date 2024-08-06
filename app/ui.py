import sys
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QLineEdit, QFileDialog, QCheckBox, \
    QTextEdit, QProgressBar
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from app.media_processor import create_enhanced_mkv
import threading


class Stream:
    def __init__(self, emit):
        self.emit = emit
        self.buffer = ''

    def write(self, message):
        self.buffer += message
        if '\n' in message:
            self.flush()

    def flush(self):
        self.emit(self.buffer.strip())
        self.buffer = ''


class FramelessWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)

        self.initUI()
        self.oldPos = self.pos()

    def initUI(self):
        self.setWindowTitle('MKV Creator')
        self.setFixedSize(800, 600)

        layout = QVBoxLayout()
        titleBar = self.createTitleBar("MKV Creator")

        layout.addWidget(titleBar)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(0)

        self.contentWidget = MKVCreatorApp(self)
        layout.addWidget(self.contentWidget)

        self.setLayout(layout)
        self.setStyleSheet("background-color: #2F2F2F;")

    def createTitleBar(self, title):
        titleBarWidget = QWidget()
        titleBarWidget.setObjectName("TitleBar")
        titleBarLayout = QHBoxLayout(titleBarWidget)

        titleLabel = QLabel(title)
        titleLabel.setObjectName("TitleLabel")
        titleLabel.setStyleSheet("color: white; font-weight: bold;")

        minButton = QPushButton("_")
        minButton.clicked.connect(self.showMinimized)
        closeButton = QPushButton("X")
        closeButton.clicked.connect(self.close)

        titleBarLayout.addWidget(titleLabel)
        titleBarLayout.addStretch()
        titleBarLayout.addWidget(minButton)
        titleBarLayout.addWidget(closeButton)

        titleBarWidget.setStyleSheet("""
            #TitleBar {
                background-color: #2F2F2F;
            }
            #TitleLabel {
                color: white;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton {
                background-color: #2F2F2F; 
                color: white;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover {
                background-color: #3F3F3F;
            }
        """)

        titleBarLayout.setContentsMargins(0, 0, 0, 0)
        titleBarLayout.setSpacing(0)
        titleLabel.setFixedHeight(30)
        minButton.setFixedSize(30, 30)
        closeButton.setFixedSize(30, 30)
        titleBarWidget.setFixedHeight(30)

        return titleBarWidget

    def mousePressEvent(self, event):
        self.oldPos = event.globalPosition().toPoint()
        self._drag_pos = event.globalPosition().toPoint() - self.pos()
        event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            diff = (event.globalPosition().toPoint() - self._drag_pos) - self.pos()
            newpos = self.pos() + diff
            self.move(newpos)
        event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        event.accept()


class InputField(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            url = event.mimeData().urls()[0]
            filePath = url.toLocalFile()
            self.setText(filePath)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)


class SignalHandler(QObject):
    update_progress = pyqtSignal(int)
    log_message = pyqtSignal(str)
    toggle_buttons = pyqtSignal(bool)


class MKVCreatorApp(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.signal_handler = SignalHandler()
        self.initUI()
        self.connect_signals()

    def initUI(self):
        layout = QVBoxLayout()

        self.setStyleSheet("""
                            QWidget {
                                color: #DDDDDD;
                                background-color: #333333;
                            }
                            QLineEdit, QPushButton, QLabel, QCheckBox {
                                border: 2px solid #555555;
                                border-radius: 5px;
                                padding: 5px;
                            }
                            QPushButton:hover {
                                background-color: #555555;
                            }
                            QPushButton:pressed {
                                background-color: #777777;
                            }
                        """)

        self.videoEntry = InputField()
        self.audioEntry = InputField()
        self.subtitleSignsEntry = InputField()
        self.subtitleFullEntry = InputField()
        self.fontsEntry = InputField()
        self.outputEntry = InputField()

        self.setupComponent("Видеофайл:", self.videoEntry, self.browseFile, layout)
        self.setupComponent("Аудиофайл AL:", self.audioEntry, self.browseFile, layout)
        self.setupComponent("Надписи:", self.subtitleSignsEntry, self.browseFile, layout)
        self.setupComponent("Субтитры:", self.subtitleFullEntry, self.browseFile, layout)
        self.setupComponent("Шрифты:", self.fontsEntry, self.browseFolder, layout, isFolder=True)
        self.setupComponent("Выходной файл MKV:", self.outputEntry, self.saveFile, layout)

        self.removeDelayCheckBox = QCheckBox("Удалить задержку?")
        self.removeDelayCheckBox.setChecked(True)
        layout.addWidget(self.removeDelayCheckBox)

        self.convertAudioCheckBox = QCheckBox("Конверировать аудио?")
        self.convertAudioCheckBox.setChecked(True)
        layout.addWidget(self.convertAudioCheckBox)

        self.createButton = QPushButton("Создать MKV")
        self.createButton.clicked.connect(self.createMKV)
        layout.addWidget(self.createButton)

        self.progressBar = QProgressBar()
        self.progressBar.setVisible(False)
        layout.addWidget(self.progressBar)

        self.logConsole = QTextEdit()
        self.logConsole.setReadOnly(True)
        layout.addWidget(self.logConsole)

        sys.stdout = Stream(self.logMessage)
        sys.stderr = Stream(self.logMessage)

        self.setLayout(layout)
        self.resize(800, 600)

    def logMessage(self, message):
        self.logConsole.append(message)

    def setupComponent(self, labelText, entryWidget, browseFunction, layout, isFolder=False, isDelay=False):
        componentLayout = QHBoxLayout()
        label = QLabel(labelText)
        componentLayout.addWidget(label)
        componentLayout.addWidget(entryWidget)

        if browseFunction:
            browseButton = QPushButton("Обзор" if not isFolder else "Выбрать")
            browseButton.clicked.connect(lambda: browseFunction(entryWidget))
            componentLayout.addWidget(browseButton)

        layout.addLayout(componentLayout)

    def browseFile(self, entry):
        file, _ = QFileDialog.getOpenFileName(self, "Выберите файл")
        if file:
            entry.setText(file)

    def browseFolder(self, entry):
        folder = QFileDialog.getExistingDirectory(self, "Выберите каталог")
        if folder:
            entry.setText(folder)

    def saveFile(self, entry):
        file, _ = QFileDialog.getSaveFileName(self, "Сохранить файл", "", "MKV-файлы (*.mkv);;Все файлы (*)")
        if file:
            entry.setText(file)

    def connect_signals(self):
        self.signal_handler.update_progress.connect(self.updateProgressBar)
        self.signal_handler.log_message.connect(self.logConsole.append)
        self.signal_handler.toggle_buttons.connect(self.toggleCreateButtonVisibility)

    def toggleCreateButtonVisibility(self, visible):
        self.createButton.setVisible(visible)
        self.progressBar.setVisible(not visible)

    def createMKV(self):
        video_file = self.videoEntry.text()
        audio_file = self.audioEntry.text()
        subtitle_signs_file = self.subtitleSignsEntry.text()
        subtitle_full_file = self.subtitleFullEntry.text()
        fonts_dir = self.fontsEntry.text().strip()
        output_file = self.outputEntry.text()
        is_remove_delay = self.removeDelayCheckBox.isChecked()
        is_convert_audio = self.convertAudioCheckBox.isChecked()

        if not all([video_file, audio_file, subtitle_signs_file, subtitle_full_file, output_file]):
            self.signal_handler.log_message.emit("Все поля, кроме «Каталог шрифтов», обязательны для заполнения!")
            return

        def create_mkv_thread(audio_file):
            self.signal_handler.toggle_buttons.emit(False)
            self.signal_handler.update_progress.emit(0)
            self.createButton.setVisible(False)
            self.progressBar.setVisible(True)
            self.progressBar.setValue(0)

            try:
                create_enhanced_mkv(
                    input_file=video_file,
                    additional_audio=audio_file,
                    subtitle_signs=subtitle_signs_file,
                    subtitle_full=subtitle_full_file,
                    font_directory=fonts_dir,
                    output_file=output_file,
                    is_remove_delay=is_remove_delay,
                    is_convert_audio=is_convert_audio,
                    progress_callback=self.signal_handler.update_progress.emit,
                    signal_handler=self.signal_handler
                )
                self.signal_handler.log_message.emit("MKV-файл создан!")
            except Exception as e:
                self.signal_handler.log_message.emit(f"Не удалось создать файл MKV: {e}")
            finally:
                self.signal_handler.toggle_buttons.emit(True)

        thread = threading.Thread(target=create_mkv_thread, args=(audio_file,))
        thread.start()

    def updateProgressBar(self, progress):
        self.progressBar.setValue(progress)
