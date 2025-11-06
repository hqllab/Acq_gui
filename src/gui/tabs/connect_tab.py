# gui/tabs/connect_tab.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QTextEdit, QLabel, QLineEdit,
    QFormLayout, QSpinBox
)
from PySide6.QtCore import QSettings
from core.detector_controller import DetectorController


class ConnectTab(QWidget):
    """连接与参数设置界面（仅负责 UI）"""

    def __init__(self):
        super().__init__()
        self.controller = DetectorController()
        self._setup_ui()

    # ---------------------------------------------------------
    def _setup_ui(self):
        main_layout = QVBoxLayout()

        # === 第一行：IP + 连接按钮 ===
        ip_layout = QHBoxLayout()
        self.ip_edit = QLineEdit()
        self.ip_edit.setPlaceholderText("例如：10.20.22.230")
        self.settings = QSettings("ScanGUI", "DetectorApp")
        self.ip_edit.setText(self.settings.value("last_ip", "10.20.22.230"))
        self.btn_connect = QPushButton("连接探测器")
        self.btn_connect.clicked.connect(self.connect_device)
        ip_layout.addWidget(QLabel("设备 IP："))
        ip_layout.addWidget(self.ip_edit)
        ip_layout.addWidget(self.btn_connect)
        main_layout.addLayout(ip_layout)

        # === 第二行：状态 ===
        status_layout = QHBoxLayout()
        self.status_label = QLabel("当前状态：未连接")
        self.btn_status = QPushButton("获取状态")
        self.btn_status.clicked.connect(self.get_status)
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.btn_status)
        main_layout.addLayout(status_layout)

        # === 第三行：参数设置 ===
        params_layout = QHBoxLayout()
        self.pos_params, self.power_inputs, self.det_inputs = [], {}, {}

        # ---- 位置参数 ----
        self.group_pos = QGroupBox("位置参数")
        pos_form = QFormLayout()
        for i in range(2):
            cfg = {
                "pos": QSpinBox(), "en": QLineEdit(),
                "polarity": QLineEdit(), "clearPos": QLineEdit(),
                "zeroShift": QSpinBox()
            }
            cfg["pos"].setRange(0, 10)
            cfg["pos"].setValue(i)
            cfg["en"].setText("1" if i == 0 else "0")
            cfg["polarity"].setText("1" if i == 0 else "0")
            cfg["clearPos"].setText("1")
            cfg["zeroShift"].setRange(0, 10)
            pos_form.addRow(QLabel(f"位置 {i}："))
            for k, v in cfg.items():
                pos_form.addRow(f"  {k}", v)
            self.pos_params.append(cfg)
        self.group_pos.setLayout(pos_form)
        params_layout.addWidget(self.group_pos)

        # ---- 电源参数 ----
        self.group_power = QGroupBox("电源参数")
        power_form = QFormLayout()
        for name in ["laser1", "laser0", "opa", "vbias", "vcc12", "vdd25"]:
            le = QLineEdit()
            le.setText("1" if name in ["opa", "vbias", "vcc12", "vdd25"] else "0")
            power_form.addRow(f"{name} (0/1)", le)
            self.power_inputs[name] = le
        self.group_power.setLayout(power_form)
        params_layout.addWidget(self.group_power)

        # ---- 探测参数 ----
        self.group_det = QGroupBox("探测参数")
        det_form = QFormLayout()
        defaults = {"packagePix": 64, "pixNum": 256, "winNum": 4, "maxThr": 511}
        for k, v in defaults.items():
            sb = QSpinBox()
            sb.setRange(0, 10000)
            sb.setValue(v)
            det_form.addRow(k, sb)
            self.det_inputs[k] = sb
        self.group_det.setLayout(det_form)
        params_layout.addWidget(self.group_det)

        main_layout.addLayout(params_layout)

        # === 应用按钮 ===
        self.btn_apply = QPushButton("应用全部参数")
        self.btn_apply.clicked.connect(self.apply_all_params)
        main_layout.addWidget(self.btn_apply)

        # === 日志框 ===
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        main_layout.addWidget(self.log_box)
        self.setLayout(main_layout)

    # ---------------------------------------------------------
    def connect_device(self):
        ip = self.ip_edit.text().strip()
        if not ip:
            self.log_box.append("[ERROR] IP 地址不能为空。")
            return
        self.settings.setValue("last_ip", ip)
        self.settings.sync()
        self.log_box.append(f"[INFO] 正在连接 {ip} ...")
        self.controller.connect(ip, self._on_connect_result)

    def _on_connect_result(self, success, msg):
        self.status_label.setText(f"当前状态：{'已连接' if success else '离线模式'}")
        self.log_box.append(f"[{'INFO' if success else 'ERROR'}] {msg}")

    # ---------------------------------------------------------
    def get_status(self):
        self.log_box.append("[INFO] 正在读取状态...")
        self.controller.get_status(self._on_status_result)

    def _on_status_result(self, success, result):
        import json
        """状态结果回调"""
        if success:
            # 在日志框中逐行输出状态
            self.log_box.append("[DONE] 状态更新完成。")
            self.log_box.append("[INFO] 状态信息：")
            for k, v in result.items():
                self.log_box.append(f"  {k}: {json.dumps(v, indent=2, ensure_ascii=False)}")
        else:
            self.log_box.append(f"[ERROR] 获取状态失败：{result}")

    # ---------------------------------------------------------
    def apply_all_params(self):
        """从 UI 收集参数并应用"""
        pos_cfgs = [
            {
                "pos": c["pos"].value(),
                "en": int(c["en"].text() or 0),
                "polarity": int(c["polarity"].text() or 0),
                "clearPos": int(c["clearPos"].text() or 0),
                "zeroShift": c["zeroShift"].value(),
            } for c in self.pos_params
        ]
        power_dict = {k: int(v.text() or 0) for k, v in self.power_inputs.items()}
        det_params = {k: v.value() for k, v in self.det_inputs.items()}

        self.log_box.append("[INFO] 正在应用参数配置 ...")
        self.controller.apply_config(pos_cfgs, power_dict, det_params, self._on_apply_result)

    def _on_apply_result(self, success, msg):
        self.log_box.append(f"[{'DONE' if success else 'ERROR'}] {msg}")
