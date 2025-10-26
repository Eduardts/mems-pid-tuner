#!/usr/bin/env python3
"""
App.py
Simple PyQt5 GUI for connecting to the Arduino PID tuner, adjusting gains and setpoint,
and plotting live telemetry.
Requires: pyserial, PyQt5, matplotlib, numpy
"""
import sys
import threading
import time
from collections import deque

import serial
import serial.tools.list_ports
import numpy as np

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QComboBox
)

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

BAUD = 115200

class SerialReaderThread(QtCore.QThread):
    telemetry = QtCore.pyqtSignal(float, float, float, float)  # t, sp, meas, out

    def __init__(self, ser):
        super().__init__()
        self.ser = ser
        self._running = True

    def run(self):
        while self._running:
            try:
                line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                if not line:
                    continue
                # try parse CSV telemetry "t,sp,meas,out"
                parts = [p.strip() for p in line.split(',') if p.strip()!='']
                if len(parts) >= 4:
                    try:
                        t = float(parts[0])
                        sp = float(parts[1])
                        meas = float(parts[2])
                        out = float(parts[3])
                        self.telemetry.emit(t, sp, meas, out)
                    except:
                        pass
            except Exception:
                time.sleep(0.05)

    def stop(self):
        self._running = False
        self.wait(200)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MEMS PID Tuner")
        self.ser = None
        self.reader = None

        self.data_t = deque(maxlen=2000)
        self.data_sp = deque(maxlen=2000)
        self.data_meas = deque(maxlen=2000)
        self.data_out = deque(maxlen=2000)

        self._build_ui()
        self._refresh_ports()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout()
        central.setLayout(layout)

        # controls
        ctrl_layout = QHBoxLayout()
        layout.addLayout(ctrl_layout)

        self.port_combo = QComboBox()
        ctrl_layout.addWidget(QLabel("Port:"))
        ctrl_layout.addWidget(self.port_combo)
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._refresh_ports)
        ctrl_layout.addWidget(self.refresh_btn)
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self._toggle_connect)
        ctrl_layout.addWidget(self.connect_btn)

        # PID controls
        pid_layout = QHBoxLayout()
        layout.addLayout(pid_layout)
        self.kp_edit = QLineEdit("2.0")
        self.ki_edit = QLineEdit("0.0")
        self.kd_edit = QLineEdit("0.0")
        pid_layout.addWidget(QLabel("Kp"))
        pid_layout.addWidget(self.kp_edit)
        pid_layout.addWidget(QLabel("Ki"))
        pid_layout.addWidget(self.ki_edit)
        pid_layout.addWidget(QLabel("Kd"))
        pid_layout.addWidget(self.kd_edit)
        self.set_gains_btn = QPushButton("Set Gains")
        self.set_gains_btn.clicked.connect(self._set_gains)
        pid_layout.addWidget(self.set_gains_btn)

        sp_layout = QHBoxLayout()
        layout.addLayout(sp_layout)
        self.setpoint_edit = QLineEdit("512")
        sp_layout.addWidget(QLabel("Setpoint"))
        sp_layout.addWidget(self.setpoint_edit)
        self.set_sp_btn = QPushButton("Set SP")
        self.set_sp_btn.clicked.connect(self._set_setpoint)
        sp_layout.addWidget(self.set_sp_btn)
        self.start_btn = QPushButton("Start")
        self.start_btn.clicked.connect(self._start_control)
        sp_layout.addWidget(self.start_btn)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self._stop_control)
        sp_layout.addWidget(self.stop_btn)

        # plot
        fig = Figure(figsize=(6, 3))
        self.canvas = FigureCanvas(fig)
        layout.addWidget(self.canvas)
        self.ax = fig.add_subplot(111)
        self.line_sp, = self.ax.plot([], [], label='Setpoint')
        self.line_meas, = self.ax.plot([], [], label='Measurement')
        self.line_out, = self.ax.plot([], [], label='Output')
        self.ax.legend()
        self.ax.set_ylim(0, 1100)  # for 10-bit ADC range; adjust as needed

        # timer to refresh plot
        self.plot_timer = QtCore.QTimer()
        self.plot_timer.timeout.connect(self._update_plot)
        self.plot_timer.start(100)

    def _refresh_ports(self):
        self.port_combo.clear()
        ports = serial.tools.list_ports.comports()
        for p in ports:
            self.port_combo.addItem(f"{p.device} - {p.description}", p.device)

    def _toggle_connect(self):
        if self.ser and self.ser.is_open:
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
        port = self.port_combo.currentData()
        if not port:
            QtWidgets.QMessageBox.warning(self, "No port", "Select a serial port first.")
            return
        try:
            self.ser = serial.Serial(port, BAUD, timeout=1)
            time.sleep(0.1)
            self.reader = SerialReaderThread(self.ser)
            self.reader.telemetry.connect(self._on_telemetry)
            self.reader.start()
            self.connect_btn.setText("Disconnect")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Connection error", str(e))

    def _disconnect(self):
        if self.reader:
            self.reader.stop()
            self.reader = None
        if self.ser:
            try:
                self.ser.close()
            except:
                pass
            self.ser = None
        self.connect_btn.setText("Connect")

    def _set_gains(self):
        if not self.ser or not self.ser.is_open:
            QtWidgets.QMessageBox.warning(self, "Not connected", "Connect first.")
            return
        try:
            kp = float(self.kp_edit.text())
            ki = float(self.ki_edit.text())
            kd = float(self.kd_edit.text())
            cmd = f"SET {kp} {ki} {kd}\n"
            self.ser.write(cmd.encode('utf-8'))
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Format error", str(e))

    def _set_setpoint(self):
        if not self.ser or not self.ser.is_open:
            QtWidgets.QMessageBox.warning(self, "Not connected", "Connect first.")
            return
        try:
            sp = float(self.setpoint_edit.text())
            cmd = f"SETPOINT {sp}\n"
            self.ser.write(cmd.encode('utf-8'))
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Format error", str(e))

    def _start_control(self):
        if not self.ser or not self.ser.is_open:
            QtWidgets.QMessageBox.warning(self, "Not connected", "Connect first.")
            return
        self.ser.write(b"START\n")

    def _stop_control(self):
        if not self.ser or not self.ser.is_open:
            QtWidgets.QMessageBox.warning(self, "Not connected", "Connect first.")
            return
        self.ser.write(b"STOP\n")

    @QtCore.pyqtSlot(float, float, float, float)
    def _on_telemetry(self, t, sp, meas, out):
        self.data_t.append(t / 1000.0)  # convert ms to s
        self.data_sp.append(sp)
        self.data_meas.append(meas)
        self.data_out.append(out)

    def _update_plot(self):
        if len(self.data_t) == 0:
            return
        t0 = np.array(self.data_t)
        sp = np.array(self.data_sp)
        meas = np.array(self.data_meas)
        out = np.array(self.data_out)
        self.line_sp.set_data(t0 - t0[0], sp)
        self.line_meas.set_data(t0 - t0[0], meas)
        self.line_out.set_data(t0 - t0[0], out)
        self.ax.relim()
        self.ax.autoscale_view(True, True, True)
        self.canvas.draw_idle()

    def closeEvent(self, event):
        self._disconnect()
        super().closeEvent(event)

def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
