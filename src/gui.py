import sys
import numpy as np
import csv
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QSlider, QComboBox, QCheckBox, QLabel, QFileDialog,
    QMenuBar, QMenu, QMessageBox, QGridLayout, QDoubleSpinBox
)
from PyQt6.QtCore import Qt, QTimer
import pyqtgraph as pg
import pyqtgraph.exporters
from collections import deque

import serial
import time

class ArduinoSerial():
    def __init__(self, port: str, baudrate: int = 38400, timeout: float = 1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.connection = None

    def connect(self):
        try:
            self.connection = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
            time.sleep(2) # Wait for Arduino reset
            print(f"Connected to {self.port} at {self.baudrate} baud.")
        except serial.SerialException as e:
            print(f"Failed to connect: {e}")

    def disconnect(self):
        if self.connection and self.connection.is_open:
            self.connection.close()
            print('Disconnected.')

    def send(self, data: str):
        if self.connection and self.connection.is_open:
            self.connection.write(data.encode())
            # print(f"Sent: {data}")

    def receive(self) -> str:
        if self.connection and self.connection.is_open:
            if self.connection.in_waiting > 0:
                return self.connection.readline().decode().strip()
        return ""

    def is_connected(self) -> bool:
        return self.connection is not None and self.connection.is_open

    def __del__(self):
        self.disconnect()


class PlotApp(QMainWindow):
    def __init__(self):
        super().__init__()

        ############# Connect Devices ##############
        self.ard = ArduinoSerial(port="/dev/cu.usbmodem23329801")
        self.ard.connect()

        ############# Initialize variables ##############
        self.data_window_len = 50
        self.num_sensor_channels = 3

        self.adc_data = [deque(maxlen=self.data_window_len) for _ in range(self.num_sensor_channels)]


        ############# Setup GUI ###############
        self.setWindowTitle("fluid-control")

        # Central widget and layout
        central_widget = QWidget()
        main_layout = QGridLayout()
        # main_layout.setSizeConstraint(QGridLayout.SizeConstraint.SetFixedSize)



        # Controls layout
        controls_layout = QGridLayout()

        # Plots layout
        plots_layout = QGridLayout()

        # Setup main layout
        main_layout.addLayout(controls_layout, 0, 0, 1, 1)
        main_layout.addLayout(plots_layout, 0, 1, 12, 4)

        # Control section
        control_row = 0

        # Pump control
        controls_layout.addWidget(QLabel('Pump flow rate ():'), control_row, 0, 1, 1) #, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.flowrate_spinbox = QDoubleSpinBox()
        self.flowrate_spinbox.setRange(0.0, 100.0)
        self.flowrate_spinbox.setSingleStep(0.1)
        self.flowrate_spinbox.setValue(0.0)
        controls_layout.addWidget(self.flowrate_spinbox, control_row, 1, 1, 1) #, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        self.pump_button = QPushButton("Set Pump ON")
        controls_layout.addWidget(self.pump_button, control_row, 2, 1, 1) #, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        control_row += 1

        # Valve control
        controls_layout.addWidget(QLabel('Input valve position:'), control_row, 0, 1, 1) #, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.input_valve_combobox = QComboBox()
        self.input_valve_combobox.addItems(["Sample", "Oil"])
        controls_layout.addWidget(self.input_valve_combobox, control_row, 1, 1, 1) #, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        control_row += 1

        controls_layout.addWidget(QLabel('Output valve position:'), control_row, 0, 1, 1) #, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.output_valve_combobox = QComboBox()
        self.output_valve_combobox.addItems(["Waste", "Sample"])
        controls_layout.addWidget(self.output_valve_combobox, control_row, 1, 1, 1) #, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        control_row += 1



        # Plot sections
        # self.plot_widgets = []
        plots_row = 0

        self.plot_widget = pg.GraphicsLayoutWidget(show=True, title="Sensors")
        self.sensor_plot_items = []
        self.sensor_plot_data_items = []
        for i in range(self.num_sensor_channels):
            self.sensor_plot_items.append(self.plot_widget.addPlot(row=i, col=0, title=f"Sensor {i+1}"))
            if i > 0:
                self.sensor_plot_items[i].setXLink(self.sensor_plot_items[0])
            self.sensor_plot_data_items.append(self.sensor_plot_items[-1].plot())



        # for i in range(num_sensor_channels):
        #     # Sensor label
        #     # sensor_label = QLabel(f"Sensor {i+1} (units)")
        #     self.plot_widgets.append(pg.PlotWidget())
        #     self.plot_widgets[-1].showGrid(x=True, y=True)
        #     self.plot_widgets[-1].setTitle(f"Sensor {i+1}")

        #     plots_layout.addWidget(self.plot_widgets[-1], plots_row, 0, 1, 4)
        #     # plots_row += 1
        plots_layout.addWidget(self.plot_widget, plots_row, 0, 11, 4)
        plots_row += 11

        self.grid_checkbox = QCheckBox("Show Grid")
        self.grid_checkbox.setChecked(True)
        self.grid_checkbox.stateChanged.connect(self.toggle_grid)
        plots_layout.addWidget(self.grid_checkbox, plots_row, 0, 1, 1)

        self.toggle_timer_button = QPushButton("Start Real-Time")
        self.toggle_timer_button.setCheckable(True)
        self.toggle_timer_button.clicked.connect(self.toggle_timer)
        plots_layout.addWidget(self.toggle_timer_button, plots_row, 1, 1, 2) #, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        plots_row += 1


        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        # Timer for real-time updates
        self.timer_ui = QTimer()
        self.timer_ui.setInterval(100)
        self.timer_ui.timeout.connect(self.update_plot)

        # Timer for Arduino data poll
        self.timer_data = QTimer()
        self.timer_data.setInterval(50)
        self.timer_data.timeout.connect(self.grab_data)

        # Data storage
        self.x = np.linspace(0, 10, 500)
        self.y = []

        # Menu bar
        self.create_menu_bar()

        self.update_plot()

    def create_menu_bar(self):
        menu_bar = self.menuBar()

        # File Menu
        file_menu = menu_bar.addMenu("File")

        export_image_action = file_menu.addAction("Export Image")
        export_image_action.triggered.connect(self.export_image)

        export_csv_action = file_menu.addAction("Export CSV")
        export_csv_action.triggered.connect(self.export_csv)

        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(self.close)

        # View Menu
        view_menu = menu_bar.addMenu("View")

        toggle_grid_action = view_menu.addAction("Toggle Grid")
        toggle_grid_action.setCheckable(True)
        toggle_grid_action.setChecked(True)
        toggle_grid_action.triggered.connect(self.grid_checkbox.toggle)

        # Help Menu
        help_menu = menu_bar.addMenu("Help")

        about_action = help_menu.addAction("About")
        about_action.triggered.connect(self.show_about_dialog)

    def show_about_dialog(self):
        QMessageBox.information(self, "About", "PyQt6 + PyQtGraph Plotting App\nCreated with ❤️")

    def update_plot(self):
        # print('update plot: read values from sensors and update plots')
        for ch in range(self.num_sensor_channels):
            self.sensor_plot_data_items[ch].setData(list(self.adc_data[ch]))
        # freq = self.freq_slider.value()
        # func = self.function_selector.currentText()
        # self.plot_widget.clear()

        # self.y = []
        # if func in ["Sine", "Both"]:
        #     y_sin = np.sin(freq * self.x)
        #     self.plot_widget.plot(self.x, y_sin, pen='r', name="Sine")
        #     self.y.append(("Sine", y_sin))
        # if func in ["Cosine", "Both"]:
        #     y_cos = np.cos(freq * self.x)
        #     self.plot_widget.plot(self.x, y_cos, pen='b', name="Cosine")
        #     self.y.append(("Cosine", y_cos))

    def grab_data(self):
        for ch in range(self.num_sensor_channels):
            self.ard.send(f"READ A{ch}\n")
            time.sleep(0.025)
            data = self.ard.receive()
            # print(f"Ch{ch}: {data}")
            if len(data) > 0:
                self.adc_data[ch].append(int(data))


    def toggle_grid(self):
        show = self.grid_checkbox.isChecked()
        self.plot_widget.showGrid(x=show, y=show)

    def toggle_timer(self):
        if self.toggle_timer_button.isChecked():
            self.timer_ui.start()
            self.timer_data.start()
            self.toggle_timer_button.setText("Stop Real-Time")
        else:
            self.timer_data.stop()
            self.timer_ui.stop()
            self.toggle_timer_button.setText("Start Real-Time")

    def export_image(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Save Plot Image", "", "PNG Files (*.png);;All Files (*)")
        if filename:
            exporter = pg.exporters.ImageExporter(self.plot_widget.plotItem)
            exporter.export(filename)

    def export_csv(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Export Data to CSV", "", "CSV Files (*.csv);;All Files (*)")
        if filename:
            with open(filename, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                header = ["x"] + [label for label, _ in self.y]
                writer.writerow(header)
                for i in range(len(self.x)):
                    row = [self.x[i]] + [y[i] for _, y in self.y]
                    writer.writerow(row)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PlotApp()
    window.show()
    sys.exit(app.exec())
