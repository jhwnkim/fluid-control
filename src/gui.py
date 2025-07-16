import sys
import numpy as np
import csv
import struct
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
import serial.tools.list_ports
import time

class ArduinoSerial():
    """
    Handles the connection to the Arduino board via serial communication.
    Allows sending and receiving data, as well as scanning for available ports.
    If no port is specified, it will scan for available ports and connect to the first Arduino
    """
    def __init__(self, port: str, baudrate: int = 500000, timeout: float = 1):
        """
        Initializes the ArduinoSerial object with the specified port, baudrate, and timeout.
        If the port is not specified, it will scan for available ports.
        
        :param port: Serial port to connect to (e.g., 'COM3' on Windows or '/dev/ttyUSB0' on Linux)
        :param baudrate: Baud rate for the serial communication (default is 500000)
        :param timeout: Timeout for the serial communication (default is 1 second)        
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.connection = None

    def connect(self):
        """
        Connects to the Arduino board via the specified serial port.
        If the port is not set, it scans for available ports and connects to the first one
        that matches 'Arduino' in its description.
        Raises a SerialException if the connection fails.

        :raises serial.SerialException: If the connection to the Arduino fails
        
        :return: None
        """
        try:
            # If port is not set scan ports
            if self.port == "":
                ports = serial.tools.list_ports.comports()
                select_idx = -1
                for idx, port in enumerate(ports):
                    print(f"Device: {port.device}, Description: {port.description}")
                    if 'Arduino' in port.description:
                        print(f"Arduino found on {port.device}")
                        self.port = port.device
                        select_idx = idx

            self.connection = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
            time.sleep(2) # Wait for Arduino reset
            print(f"Connected to {self.port} at {self.baudrate} baud.")
        except serial.SerialException as e:
            print(f"Failed to connect: {e}")

    def disconnect(self):
        """
        Disconnects from the Arduino board.
        If the connection is open, it closes the connection and prints a message.
        
        :return: None
        """
        if self.connection and self.connection.is_open:
            self.connection.close()
            print('Disconnected.')

    def send(self, data: str):
        """
        Sends data to the Arduino board via the serial connection.
        If the connection is open, it encodes the data and writes it to the serial port
        
        :param data: Data to send to the Arduino
        
        :return: None
        """
        if self.connection and self.connection.is_open:
            self.connection.write(data.encode())
            # print(f"Sent: {data}")

    def receive(self) -> str:
        """
        Receives data from the Arduino board via the serial connection.
        If the connection is open and there is data available, it reads a line from the serial port.
        If no data is available, it returns an empty string.
        
        :return: Received data as a string, or an empty string if no data is available
        """
        if self.connection and self.connection.is_open:
            if self.connection.in_waiting > 0:
                return self.connection.readline()
                # return self.connection.readline().decode().strip()
        return ""
    
    def reset_input_buffer(self):
        """
        Resets the input buffer of the serial connection.
        This is useful to clear any unread data in the buffer before starting a new read operation.
        
        :return: None
        """
        if self.connection and self.connection.is_open:
            self.connection.reset_input_buffer()

    def is_connected(self) -> bool:
        """
        Checks if the Arduino is connected by verifying if the connection is not None and is open.
        
        :return: True if connected, False otherwise
        """
        return self.connection is not None and self.connection.is_open

    def __del__(self):
        """
        Destructor to ensure the connection is closed when the object is deleted.
        This is called when the object goes out of scope or is explicitly deleted.
        """
        self.disconnect()


class PlotApp(QMainWindow):
    """
    Main application class for the fluid control GUI.
    Inherits from QMainWindow and sets up the GUI layout, controls, and plots.
    Initializes the Arduino connection, sets up the GUI components, and handles real-time data updates.
    The GUI includes controls for pumps, valves, and sensor plots.
    """
    def __init__(self):
        """
        Initializes the GUI components and layout.
        """

        super().__init__()

        self.sample_period_ms = 100
        self.display_period_ms = 110

        ############# Connect Devices ##############
        self.ard = ArduinoSerial(port="")
        self.ard.connect()

        ############# Initialize variables ##############
        self.data_window_len = 50
        self.num_sensor_channels = 2

        self.sensors = ['A0', 'A1', 'FS']
        # self.adc_data = [deque(maxlen=self.data_window_len) for _ in range(self.num_sensor_channels)]
        self.adc_data = {}
        for ch in self.sensors:
            self.adc_data[ch] = deque(maxlen=self.data_window_len)

        self.num_pumps = 4

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
        self.pump_flowrate_spinbox = []
        self.pump_button = []
        
        for idx in range(self.num_pumps):
            controls_layout.addWidget(QLabel(f"Pump {idx} flow rate ():"), control_row, 0, 1, 1) #, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
            
            self.pump_flowrate_spinbox.append(QDoubleSpinBox())
            self.pump_flowrate_spinbox[idx].setRange(0.0, 100.0)
            self.pump_flowrate_spinbox[idx].setSingleStep(0.1)
            self.pump_flowrate_spinbox[idx].setValue(0.0)
            controls_layout.addWidget(self.pump_flowrate_spinbox[idx], control_row, 1, 1, 1) #, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
            self.pump_button.append(QPushButton(f"Set Pump {idx} ON"))
            controls_layout.addWidget(self.pump_button[idx], control_row, 2, 1, 1) #, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
            control_row += 1

            self.pump_button[idx].clicked.connect(lambda checked, index=idx: self.toggle_pump(index))
            

        self.all_pumps_on_button = QPushButton("All Pumps ON")
        self.all_pumps_on_button.clicked.connect(self.all_pumps_on)
        controls_layout.addWidget(self.all_pumps_on_button, control_row, 1, 1, 1) #, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.all_pumps_off_button = QPushButton("All Pumps OFF")
        self.all_pumps_off_button.clicked.connect(self.all_pumps_off)
        controls_layout.addWidget(self.all_pumps_off_button, control_row, 2, 1, 1) #, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
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
            self.sensor_plot_items.append(self.plot_widget.addPlot(row=i, col=0, title=f"ADC Channel {i}"))
            if i > 0:
                self.sensor_plot_items[i].setXLink(self.sensor_plot_items[0])
            self.sensor_plot_data_items.append(self.sensor_plot_items[-1].plot())

        # Add Flow sensor plot
        self.sensor_plot_items.append(self.plot_widget.addPlot(row=self.num_sensor_channels, col=0, title=f"Flow rate"))
        self.sensor_plot_items[-1].setXLink(self.sensor_plot_items[0])
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
        self.timer_ui.setInterval(self.display_period_ms)
        self.timer_ui.timeout.connect(self.update_plot)

        # Timer for Arduino data poll
        self.timer_data = QTimer()
        self.timer_data.setInterval(self.sample_period_ms)
        self.timer_data.timeout.connect(self.grab_data)

        # Data storage
        self.x = np.linspace(0, 10, 500)
        self.y = []

        # Menu bar
        self.create_menu_bar()

        self.update_plot()

    def create_menu_bar(self):
        """
        Creates the menu bar with File, View, and Help menus.
        Adds actions for exporting images and CSV files, toggling the grid, and showing an about dialog.
        """
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
        """
        Shows an about dialog with information about the application.
        """
        QMessageBox.information(self, "About", "Fluid Control GUI\n Created using PyQt6 + PyQtGraph")

    def update_plot(self):
        """
        Updates the plots with the latest sensor data.
        This method is called periodically by the timer to refresh the plots with new data.
        It reads the latest values from the sensors and updates the corresponding plot items.
        """

        # print('update plot: read values from sensors and update plots')
        # for ch in range(self.num_sensor_channels):
        plot_idx = 0
        for ch in self.sensors:
            self.sensor_plot_data_items[plot_idx].setData(list(self.adc_data[ch]))
            plot_idx += 1

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
        """
        Reads data from the Arduino sensors and updates the adc_data deque.
        This method is called periodically by the timer to fetch new sensor readings.
        It sends a read command to each sensor channel, waits for the response, and appends the data
        to the corresponding deque in adc_data.
        """
        
        for ch in self.sensors:
            self.ard.reset_input_buffer()
            self.ard.send(f"READ {ch}\n")
            time.sleep(0.020)
            data = self.ard.receive()
            print(f"Sensor {ch}: {data}")
            if len(data) > 0:
                if data[0] == int.from_bytes(b'R'):
                    payloadLength = data[1]
                    print(f' Read packet received with length {payloadLength} bytes')
                    if ch == 'FS':
                        self.adc_data[ch].append(struct.unpack('<f', data[2:2+payloadLength])[0])
                    else:
                        self.adc_data[ch].append(int.from_bytes(data[2:2+payloadLength], byteorder='little'))
                    print(f' Read packet data: {self.adc_data[ch][-1]}')

                    
    def toggle_pump(self, idx: int):
        """
        Toggles the state of the specified pump.
        If the pump is currently set to ON, it changes the button text to OFF and vice
        versa. It also prints the current state of the pump to the console.
        
        :param idx: Index of the pump to toggle (0 to num_pumps-1)
        """
        if idx < 0 or idx >= self.num_pumps:
            print(f"Invalid pump index: {idx}. Must be between 0 and {self.num_pumps - 1}.")
            return

        print(f"Toggle Pump {idx} state")

        if self.pump_button[idx].text() == f"Set Pump {idx} ON":
            print(" Turn pump on")
            self.pump_button[idx].setText(f"Set Pump {idx} OFF")
        elif self.pump_button[idx].text() == f"Set Pump {idx} OFF":
            print(" Turn pump off")
            self.pump_button[idx].setText(f"Set Pump {idx} ON")

    def all_pumps_on(self):
        """
        Turns all pumps on by iterating through the pump buttons and toggling each one that is currently set to OFF.
        This method is called when the "All Pumps ON" button is clicked.
        """
        print("Turn all pumps on")
        for idx in range(self.num_pumps):
            if self.pump_button[idx].text() == f"Set Pump {idx} ON":
                self.toggle_pump(idx)

    def all_pumps_off(self):
        """
        Turns all pumps off by iterating through the pump buttons and toggling each one that is currently set to ON.
        This method is called when the "All Pumps OFF" button is clicked.
        """
        print("Turn all pumps off")
        for idx in range(self.num_pumps):
            if self.pump_button[idx].text() == f"Set Pump {idx} OFF":
                self.toggle_pump(idx)

    def toggle_grid(self):
        """
        Toggles the visibility of the grid on the plot.
        """
        show = self.grid_checkbox.isChecked()
        self.plot_widget.showGrid(x=show, y=show)

    def toggle_timer(self):
        """
        Toggles the real-time data update timer.
        If the timer is currently running, it stops the timer and updates the button text to "Start Real-Time".
        If the timer is not running, it starts the timer and updates the button text to "Stop Real-Time".
        This method is called when the "Start Real-Time" button is clicked.
        """
        if self.toggle_timer_button.isChecked():
            self.timer_ui.start()
            self.timer_data.start()
            self.toggle_timer_button.setText("Stop Real-Time")
        else:
            self.timer_data.stop()
            self.timer_ui.stop()
            self.toggle_timer_button.setText("Start Real-Time")

    def export_image(self):
        """
        Exports the current plot as an image file.
        Opens a file dialog to select the save location and file name.
        Uses the ImageExporter from pyqtgraph to save the plot as a PNG file.
        
        :return: None
        """
        filename, _ = QFileDialog.getSaveFileName(self, "Save Plot Image", "", "PNG Files (*.png);;All Files (*)")
        if filename:
            exporter = pg.exporters.ImageExporter(self.plot_widget.plotItem)
            exporter.export(filename)

    def export_csv(self):
        """
        Exports the current plot data to a CSV file.
        Opens a file dialog to select the save location and file name.
        Uses the csv module to write the data to the CSV file.

        :return: None
        """
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
