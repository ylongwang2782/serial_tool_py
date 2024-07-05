import tkinter as tk
from tkinter import ttk
import serial
import threading
from datetime import datetime
import serial.tools.list_ports

class PdtTestToolGUI:

    def __init__(self, root):
        self.root = root
        self.root.title("PdtTestTool")

        # create widgets
        self.port_label = tk.Label(root, text="Serial Port:")
        self.port_label.grid(row=0, column=0, sticky='ew')
        self.port_combobox = ttk.Combobox(root)
        self.port_combobox.grid(row=0, column=1, sticky='ew')
        self.refresh_button = tk.Button(root, text="Refresh", command=self.refresh_ports)
        self.refresh_button.grid(row=0, column=2, sticky='ew')
        # set baudrate combobox
        self.baudrate_label = tk.Label(root, text="Baudrate:")
        self.baudrate_label.grid(row=1, column=0, sticky='ew')
        self.baudrate_combobox = ttk.Combobox(root, values=["9600", "19200", "38400", "57600", "115200"])
        self.baudrate_combobox.grid(row=1, column=1, columnspan=2, sticky='ew')
        self.baudrate_combobox.set("115200")



if __name__ == "__main__":
    root = tk.Tk()
    app = PdtTestToolGUI(root)
    root.mainloop()