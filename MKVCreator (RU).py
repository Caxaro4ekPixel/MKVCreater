import sys
from PyQt6.QtWidgets import QApplication
from app.ui import MKVCreatorApp

if __name__ == "__main__":
    app = QApplication([])
    win = MKVCreatorApp()
    win.show()
    sys.exit(app.exec())
