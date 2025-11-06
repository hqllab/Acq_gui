# gui/tabs/analysis_tab.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTextEdit, QLabel
)
from hdf5storage import loadmat
import numpy as np
import matplotlib
matplotlib.use('TkAgg')  # 使用 agg 后端，避免启动 GUI

import matplotlib.pyplot as plt
from core.AcqFunc.AcqFunc import showHist
import io
import contextlib
import traceback


class AnalysisTab(QWidget):
    """交互式绘图脚本执行区 (支持 plt.show 弹窗)"""

    def __init__(self):
        super().__init__()
        self._setup_ui()

    # ------------------------------------------------------------
    def _setup_ui(self):
        layout = QVBoxLayout()

        # 顶部栏
        top = QHBoxLayout()
        self.run_btn = QPushButton("运行代码")
        top.addWidget(QLabel("在此编写 Python 绘图代码："))
        top.addStretch()
        top.addWidget(self.run_btn)
        layout.addLayout(top)

        # 代码编辑区
        self.code_edit = QTextEdit()
        self.code_edit.setPlaceholderText(
            "在这里编写代码，例如：\n"
            "data_save = loadmat(r'D:\\vxhd\\Acq1106\\test17_666mmps_1650_1950_40kV_7.5mA.mat')\n"
            "data = {\n"
            "    'data': np.transpose(data_save['d']['data'], (2, 1, 0)),\n"
            "    'pos0h': data_save['d']['pos'][:, None]\n"
            "}\n"
            "data['data'] = data['data'][:, 254:255, :]\n"
            "plt.figure(); plt.plot(data['data'].sum(axis=0).T)\n"
            "plt.show()\n"
            "showHist(data, pos_en=True, pos_step=0.0375, cal_sel=(350,400), rate=680/500)"
        )
        layout.addWidget(self.code_edit)

        # 输出日志
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        layout.addWidget(QLabel("执行输出："))
        layout.addWidget(self.log_box)

        self.setLayout(layout)
        self.run_btn.clicked.connect(self.run_code)

    # ------------------------------------------------------------
    def run_code(self):
        """执行用户代码"""
        code = self.code_edit.toPlainText().strip()
        if not code:
            self.log_box.append("[ERROR] 没有输入任何代码。")
            return

        buf = io.StringIO()
        env = {
            "np": np,
            "plt": plt,
            "loadmat": loadmat,
            "showHist": showHist,
        }

        try:
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                exec(code, env)
            out = buf.getvalue()
            if out.strip():
                self.log_box.append(f"[OUTPUT]\n{out.strip()}")
            else:
                self.log_box.append("[DONE] 代码执行完成。")
        except Exception:
            self.log_box.append(f"[ERROR]\n{traceback.format_exc()}")
