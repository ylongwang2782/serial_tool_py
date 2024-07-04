import tkinter as tk
from tkinter import ttk
import serial
import threading
from datetime import datetime
import serial.tools.list_ports

class SerialDebugger:
    FRAME_TYPE_MAP = {
        0: "广播帧",
        1: "入网回复帧",
        2: "数据帧",
        3: "阻抗帧",
        4: "命令帧",
        5: "命令回复帧"
    }

    def __init__(self, port, baudrate, treeview, data_treeview):
        self.port = port
        self.baudrate = baudrate
        self.serial_connection = None
        self.running = False
        self.treeview = treeview
        self.data_treeview = data_treeview
        self.treeview_rows = {}
        self.data_treeview_rows = {}
        self.log_file = "serial_log.txt"

    def start(self):
        try:
            self.serial_connection = serial.Serial(self.port, self.baudrate, timeout=1)
            self.running = True
            threading.Thread(target=self.read_from_port).start()
            self.log_to_file("Info", f"Connected to {self.port} at {self.baudrate} baudrate")
        except Exception as e:
            self.log_to_file("Error", f"Error opening serial port: {e}")

    def stop(self):
        self.running = False
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
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
                    
                    frame = buffer[start_index:end_index]
                    slot_num = int(frame[10:12], 16)
                    frame_type = int(frame[12:14], 16)
                    frame_data = frame[14:end_index].upper()
                    spaced_frame_data = ' '.join(frame_data[i:i+2] for i in range(0, len(frame_data), 2))
                    
                    if frame_type in (0,1,4,5):
                        self.update_treeview(slot_num, frame_type, spaced_frame_data)
                    if frame_type in (2,3):
                        self.update_data_treeview(slot_num, frame_type, spaced_frame_data)

                    buffer = buffer[end_index:]

    def update_treeview(self, slot_num, frame_type, hex_data):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        frame_type_text = self.FRAME_TYPE_MAP.get(frame_type, f"未知类型({frame_type})")
        if slot_num in self.treeview_rows:
            self.treeview.item(self.treeview_rows[slot_num], values=(slot_num, frame_type_text, hex_data))
        else:
            row_id = self.treeview.insert("", slot_num, values=(slot_num, frame_type_text, hex_data))
            self.treeview_rows[slot_num] = row_id

        self.log_to_file(slot_num, f"Type: {frame_type_text}, Data: {hex_data}", timestamp)

    def update_data_treeview(self, slot_num, frame_type, hex_data):
        timestamp = datetime.now().strftime("%H:%M:%S")
        frame_type_text = self.FRAME_TYPE_MAP.get(frame_type, f"未知类型({frame_type})")

        if slot_num in self.data_treeview_rows:
            self.data_treeview.item(self.data_treeview_rows[slot_num], values=(timestamp, slot_num, frame_type_text, hex_data))
        else:
            row_id = self.data_treeview.insert("", slot_num, values=(timestamp, slot_num, frame_type_text, hex_data))
            self.data_treeview_rows[slot_num] = row_id

    def write_to_port(self, data):
        if self.serial_connection and self.serial_connection.is_open:
            data_without_spaces = data.replace(" ", "")
            data_bytes = bytes.fromhex(data_without_spaces)
            self.serial_connection.write(data_bytes)

            if data_without_spaces.startswith("A5FFCC"):
                frame_len = int(data_without_spaces[6:8], 16)
                slot_num = int(data_without_spaces[10:12], 16)
                frame_type = int(data_without_spaces[12:14], 16)
                frame_data = data_without_spaces[14:14 + (frame_len - 7) * 2].upper()
                spaced_frame_data = ' '.join(frame_data[i:i+2] for i in range(0, len(frame_data), 2))
                self.update_treeview(slot_num, frame_type, spaced_frame_data)

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
        self.port_combobox = ttk.Combobox(root)
        self.port_combobox.grid(row=0, column=1, sticky='ew')
        self.refresh_button = tk.Button(root, text="Refresh", command=self.refresh_ports)
        self.refresh_button.grid(row=0, column=2, sticky='ew')

        self.baudrate_label = tk.Label(root, text="Baudrate:")
        self.baudrate_label.grid(row=1, column=0, sticky='ew')
                # Change from tk.Entry to ttk.Combobox
        self.baudrate_combobox = ttk.Combobox(root, values=["9600", "19200", "38400", "57600", "115200"])
        self.baudrate_combobox.grid(row=1, column=1, columnspan=2, sticky='ew')
        self.baudrate_combobox.set("115200")  # Set a default value

        self.connect_button = tk.Button(root, text="Connect", command=self.toggle_connection)
        self.connect_button.grid(row=2, column=0, columnspan=3, sticky='ew')

        self.treeview = ttk.Treeview(root, columns=("Slot", "Frame Type", "Data"), show="headings")
        self.treeview.heading("Slot", text="Slot")
        self.treeview.heading("Frame Type", text="Frame Type")
        self.treeview.heading("Data", text="Data")
        self.treeview.column("Slot", width=100)
        self.treeview.column("Frame Type", width=100)
        self.treeview.column("Data", width=600)
        self.treeview.grid(row=3, column=0, columnspan=3, sticky="nsew")

        self.data_treeview = ttk.Treeview(root, columns=("Timestamp", "Slot", "Frame Type", "Data"), show="headings")
        self.data_treeview.heading("Timestamp", text="Timestamp")
        self.data_treeview.heading("Slot", text="Slot")
        self.data_treeview.heading("Frame Type", text="Frame Type")
        self.data_treeview.heading("Data", text="Data")
        self.data_treeview.column("Timestamp", width=100)
        self.data_treeview.column("Slot", width=100)
        self.data_treeview.column("Frame Type", width=100)
        self.data_treeview.column("Data", width=600)
        self.data_treeview.grid(row=4, column=0, columnspan=3, sticky="nsew")

        self.input_label = tk.Label(root, text="Send Data:")
        self.input_label.grid(row=5, column=0, sticky='ew')
        self.input_entry = tk.Entry(root)
        self.input_entry.grid(row=5, column=1, columnspan=2, sticky='ew')

        self.send_button = tk.Button(root, text="Send", command=self.send_data)
        self.send_button.grid(row=6, column=0, columnspan=3, sticky='ew')

        root.grid_rowconfigure(3, weight=1)
        root.grid_rowconfigure(4, weight=1)
        root.grid_columnconfigure(0, weight=1)
        root.grid_columnconfigure(1, weight=1)
        root.grid_columnconfigure(2, weight=1)

        self.debugger = None

        # Bind the <Configure> event to adjust column widths
        root.bind('<Configure>', self.on_resize)

        self.refresh_ports()

    def refresh_ports(self):
        ports = serial.tools.list_ports.comports()
        port_list = [port.device for port in ports]
        self.port_combobox['values'] = port_list
        if port_list:
            self.port_combobox.current(0)

    def toggle_connection(self):
        if self.debugger and self.debugger.running:
            self.debugger.stop()
            self.connect_button.config(text="Connect")
        else:
            port = self.port_combobox.get()
            baudrate = self.baudrate_combobox.get()
            self.debugger = SerialDebugger(port, baudrate, self.treeview, self.data_treeview)
            self.debugger.start()
            self.connect_button.config(text="Disconnect")

    def send_data(self):
        data = self.input_entry.get()
        if self.debugger:
            self.debugger.write_to_port(data)

    def clear_treeview(self):
        for item in self.treeview.get_children():
            self.treeview.delete(item)
        for item in self.data_treeview.get_children():
            self.data_treeview.delete(item)

    def on_resize(self, event):
        new_width = event.width - 300 
        self.treeview.column("Data", width=new_width)
        self.data_treeview.column("Data", width=new_width)

if __name__ == "__main__":
    root = tk.Tk()
    app = SerialDebuggerGUI(root)
    root.mainloop()
