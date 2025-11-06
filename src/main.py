'''
Author: LiuSheng
Date: 2025-11-06 12:01:02
LastEditTime: 2025-11-06 14:47:37
Description: 
'''
# main.py
from PySide6.QtWidgets import QApplication
from gui.main_window import MainWindow
import sys

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
