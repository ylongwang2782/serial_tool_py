import tkinter as tk
from tkinter import ttk
import serial
import threading
from datetime import datetime

class SerialDebugger:
    def __init__(self, port, baudrate, treeview):
        self.port = port
        self.baudrate = baudrate
        self.serial_connection = None
        self.running = False
        self.treeview = treeview
        self.treeview_rows = {}
        self.log_file = "serial_log.txt"

    def start(self):
        try:
            self.serial_connection = serial.Serial(self.port, self.baudrate, timeout=1)
            self.running = True
            threading.Thread(target=self.read_from_port).start()
            self.treeview.insert("", tk.END, values=("Info", f"Connected to {self.port} at {self.baudrate} baudrate"))
            self.log_to_file("Info", f"Connected to {self.port} at {self.baudrate} baudrate")
        except Exception as e:
            self.treeview.insert("", tk.END, values=("Error", f"Error opening serial port: {e}"))
            self.log_to_file("Error", f"Error opening serial port: {e}")

    def stop(self):
        self.running = False
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
            self.treeview.insert("", tk.END, values=("Info", f"Disconnected from {self.port}"))
            self.log_to_file("Info", f"Disconnected from {self.port}")

    def read_from_port(self):
        buffer = ""
        while self.running:
            if self.serial_connection.in_waiting > 0:
                data = self.serial_connection.read(self.serial_connection.in_waiting)
                hex_data = data.hex()
                buffer += hex_data

                while "a5ffcc" in buffer:
                    start_index = buffer.find("a5ffcc")
                    if len(buffer[start_index:]) < 12:
                        break  # 不完整的帧头，继续读取

                    frame_len = int(buffer[start_index+6:start_index+8], 16)
                    end_index = start_index + frame_len * 2

                    if len(buffer[start_index:end_index]) < frame_len * 2:
                        break  # 不完整的帧，继续读取
                    
                    frame_data = buffer[start_index:end_index]
                    slot_num = int(buffer[start_index+10:start_index+12], 16)
                    # 将 frame_data 转换为大写
                    frame_data = frame_data.upper()
                    # 在 frame_data 中间添加空格
                    spaced_frame_data = ' '.join(frame_data[i:i+2] for i in range(0, len(frame_data), 2))
                    self.update_treeview(slot_num, spaced_frame_data)

                    buffer = buffer[end_index:]

    def update_treeview(self, slot_num, hex_data):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if slot_num in self.treeview_rows:
            self.treeview.item(self.treeview_rows[slot_num], values=(slot_num, hex_data))
        else:
            row_id = self.treeview.insert("", tk.END, values=(slot_num, hex_data))
            self.treeview_rows[slot_num] = row_id

        self.log_to_file(slot_num, hex_data, timestamp)

    def write_to_port(self, data):
        if self.serial_connection and self.serial_connection.is_open:
            data_without_spaces = data.replace(" ", "")
            self.serial_connection.write(data_without_spaces.encode('utf-8'))
            # self.treeview.insert("", tk.END, values=("Sent", data))
            self.log_to_file("Sent", data_without_spaces)

    def log_to_file(self, slot, data, timestamp=None):
        if not timestamp:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.log_file, "a") as f:
            f.write(f"{timestamp} Slot: {slot}, Data: {data}\n")

class SerialDebuggerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Serial Debugger")

        self.port_label = tk.Label(root, text="Serial Port:")
        self.port_label.grid(row=0, column=0, sticky='ew')
        self.port_entry = tk.Entry(root)
        self.port_entry.grid(row=0, column=1, sticky='ew')

        self.baudrate_label = tk.Label(root, text="Baudrate:")
        self.baudrate_label.grid(row=1, column=0, sticky='ew')
        self.baudrate_entry = tk.Entry(root)
        self.baudrate_entry.grid(row=1, column=1, sticky='ew')

        self.connect_button = tk.Button(root, text="Connect", command=self.toggle_connection)
        self.connect_button.grid(row=2, column=0, columnspan=2, sticky='ew')

        self.treeview = ttk.Treeview(root, columns=("Slot", "Data"), show="headings")
        self.treeview.heading("Slot", text="Slot")
        self.treeview.heading("Data", text="Data")
        self.treeview.column("Slot", width=100)  # 固定 Slot 列宽度
        self.treeview.grid(row=3, column=0, columnspan=2, sticky="nsew")

        self.input_label = tk.Label(root, text="Send Data:")
        self.input_label.grid(row=4, column=0, sticky='ew')
        self.input_entry = tk.Entry(root)
        self.input_entry.grid(row=4, column=1, sticky='ew')

        self.send_button = tk.Button(root, text="Send", command=self.send_data)
        self.send_button.grid(row=5, column=0, columnspan=2, sticky='ew')

        # Configure grid weights
        root.grid_rowconfigure(3, weight=1)
        root.grid_columnconfigure(0, weight=1)
        root.grid_columnconfigure(1, weight=1)

        self.debugger = None

        # Bind the <Configure> event to adjust column widths
        root.bind('<Configure>', self.on_resize)

    def toggle_connection(self):
        if self.debugger and self.debugger.running:
            self.debugger.stop()
            self.connect_button.config(text="Connect")
        else:
            port = self.port_entry.get()
            baudrate = int(self.baudrate_entry.get())
            self.debugger = SerialDebugger(port, baudrate, self.treeview)
            self.debugger.start()
            self.connect_button.config(text="Disconnect")

    def send_data(self):
        data = self.input_entry.get()
        if self.debugger:
            self.debugger.write_to_port(data)

    def on_resize(self, event):
        # Get the new width of the treeview
        new_width = event.width - 116  # 100 for Slot column width + 16 for scrollbar width
        self.treeview.column("Data", width=new_width)

if __name__ == "__main__":
    root = tk.Tk()
    app = SerialDebuggerGUI(root)
    root.mainloop()
