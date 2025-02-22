import os
import sqlite3
import threading
import tkinter as tk
from tkinter import ttk
import webview
from config import DB_NAME, ALLOWED_MMSI
from database import create_table
import receiver
import sender
from map_viewer import generate_map


class AISViewer:
    def __init__(self, root):
        self.root = root
        high = 600
        width = 1200
        screenWidth = root.winfo_screenwidth()
        screenHeight = root.winfo_screenheight()
        centerX = int((screenWidth/2) - (width/2))
        centerY = int((screenHeight/2) - (high/2))
        self.root.minsize(width, high)
        self.root.title("AIS Data Viewer")
        self.root.geometry(f"{width}x{high}+{centerX}+{centerY}")

        self.tree = ttk.Treeview(root,
                                 columns=("ID", "MMSI", "Lat", "Lon", "Speed", "Course", "Ship Type", "Received At"),
                                 show="headings")
        self.tree.heading("ID", text="ID")
        self.tree.heading("ID", text="ID")
        self.tree.heading("MMSI", text="MMSI")
        self.tree.heading("Lat", text="Latitude")
        self.tree.heading("Lon", text="Longitude")
        self.tree.heading("Speed", text="Speed (knots)")
        self.tree.heading("Course", text="Course (°)")
        self.tree.heading("Ship Type", text="Ship Type")
        self.tree.heading("Received At", text="Received At")
        self.tree.pack(fill=tk.BOTH, expand=True, pady=10)

        # Tombol kontrol untuk Start/Stop Receiver
        self.btn_start_receiver = ttk.Button(root, text="Start Receiver", command=self.start_receiver)
        self.btn_start_receiver.pack(side=tk.LEFT, padx=10, pady=5)

        self.btn_stop_receiver = ttk.Button(root, text="Stop Receiver", command=self.stop_receiver)
        self.btn_stop_receiver.pack(side=tk.LEFT, padx=10, pady=5)

        # Tombol kontrol untuk Start/Stop Sender
        self.btn_start_sender = ttk.Button(root, text="Start Sender", command=self.start_sender)
        self.btn_start_sender.pack(side=tk.LEFT, padx=10, pady=5)

        self.btn_stop_sender = ttk.Button(root, text="Stop Sender", command=self.stop_sender)
        self.btn_stop_sender.pack(side=tk.LEFT, padx=10, pady=5)

        # Input filter MMSI
        self.mmsi_label = tk.Label(root, text="Filter MMSI (Pisahkan dengan koma):")
        self.mmsi_label.pack()
        self.mmsi_entry = tk.Entry(root, width=50)
        self.mmsi_entry.pack()

        # Tombol Set Filter
        self.btn_set_filter = ttk.Button(root, text="Set Filter", command=self.set_mmsi_filter)
        self.btn_set_filter.pack(pady=5)

        # Tombol Refresh Data
        self.btn_refresh = ttk.Button(root, text="Refresh Data", command=self.load_data)
        self.btn_refresh.pack(pady=5)

        # Tombol untuk membuka peta
        self.btn_open_map = ttk.Button(root, text="Buka Peta", command=self.show_map)
        self.btn_open_map.pack(pady=5)

        # Status Threads
        self.receiver_thread = None
        self.sender_thread = None
        self.running_receiver = False
        self.running_sender = False

        # Inisialisasi database
        create_table()

        self.load_data()

    def load_data(self):
        """Ambil data AIS terbaru dari database dan tampilkan di GUI"""
        for row in self.tree.get_children():
            self.tree.delete(row)

        connection = sqlite3.connect(DB_NAME)
        cursor = connection.cursor()
        cursor.execute(
            "SELECT id, mmsi, lat, lon, sog, cog, ship_type, received_at FROM ais_history ORDER BY id DESC LIMIT 20")
        rows = cursor.fetchall()
        connection.close()

        for row in rows:
            self.tree.insert("", "end", values=row)

    def start_receiver(self):
        """Menjalankan penerima AIS di thread terpisah"""
        if not self.running_receiver:
            self.receiver_thread = threading.Thread(target=receiver.receive_nmea_udp, daemon=True)
            self.receiver_thread.start()
            print("Receiver Started")

    @staticmethod
    def stop_receiver():
        """Menghentikan penerima AIS"""
        receiver.stop_nmea_receiver()
        print("Receiver Stopped")

    def start_sender(self):
        """Menjalankan pengiriman AIS ke OpenCPN di thread terpisah"""
        if not self.running_sender:
            self.sender_thread = threading.Thread(target=sender.send_ais_data, daemon=True)
            self.sender_thread.start()
            print("Sender Started")

    @staticmethod
    def stop_sender():
        """Menghentikan pengiriman AIS ke OpenCPN"""
        sender.stop_ais_sender()
        print("Sender Stopped")

    def show_map(self):
        map_path = generate_map()
        webview.create_window("AIS Ship Tracker", map_path)
        webview.start()

    def set_mmsi_filter(self):
        """Memperbarui daftar MMSI yang akan dikirim ke OpenCPN"""
        global ALLOWED_MMSI
        mmsi_list = self.mmsi_entry.get().split(",")
        ALLOWED_MMSI = [mmsi.strip() for mmsi in mmsi_list if mmsi.strip()]
        print(f"Filter MMSI diperbarui: {ALLOWED_MMSI}")


if __name__ == "__main__":
    root = tk.Tk()
    app = AISViewer(root)
    root.mainloop()
