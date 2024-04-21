from serial.tools import list_ports

import serial

import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt5.QtCore import QObject, pyqtSignal, QThread

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt

import time


PORT = "COM3"
BANDWIDTH = 9600
NS_IN_MS = 1_000_000
MS_IN_S = 1_000


def init_controller():
    serialCom = serial.Serial(PORT, BANDWIDTH)
    serialCom.setDTR(False)

    time.sleep(1)

    serialCom.flushInput()
    serialCom.setDTR(True)

    return serialCom


class ArduinoWorker(QObject):
    arduino_received = pyqtSignal(float)

    def __init__(self):
        super().__init__()
        self.serial_com = init_controller()
        self.is_running = True

    def run(self):
        print("Listening thread started")
        while self.is_running:
            s_bytes = self.serial_com.readline()
            value_str = s_bytes.decode('utf-8').strip('\r\n')
            self.arduino_received.emit(float(value_str))

    def stop(self):
        self.is_running = False


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("График")
        self.setGeometry(100, 100, 800, 600)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)

        self.figure, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.figure)
        self.layout.addWidget(self.canvas)

        self.start_time = None
        self.timestamps = []
        self.values = []

        self.arduino_worker = ArduinoWorker()
        self.arduino_thread = QThread()
        self.arduino_worker.moveToThread(self.arduino_thread)

        self.arduino_worker.arduino_received.connect(self.onArduinoReceive)
        self.arduino_thread.started.connect(self.arduino_worker.run)

        self.arduino_thread.start()

    def onArduinoReceive(self, value):
        self.values.append(value)

        current_time_ms = time.time_ns() // NS_IN_MS
        if not self.start_time:
            self.start_time = current_time_ms
        relative_time_ms = current_time_ms - self.start_time
        self.timestamps.append(relative_time_ms / MS_IN_S)
        if len(self.timestamps) > 100:
            self.values = self.values[-100:]
            self.timestamps = self.timestamps[-100:]

        self.ax.clear()
        self.ax.plot(self.timestamps, self.values, marker='o', linestyle='-')
        self.ax.set_xlabel('Время (с)')
        self.ax.set_ylabel('Температура (С°)')
        self.ax.set_title('График')
        self.ax.grid(True)
        self.canvas.draw()

    def closeEvent(self, event):
        self.arduino_worker.stop()
        self.arduino_thread.quit()
        self.arduino_thread.wait()
        event.accept()



def main():
    print("Доступные порты: ")
    for port in list_ports.comports():
        print(port, end=" ")
    print()

    app = QApplication(sys.argv)
    window = Window()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()