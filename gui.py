import sqlite3
import tkinter as tk
from tkinter import ttk
from config import DB_NAME

class AISViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("AIS Data Viewer")
        self.root.geometry("800x400")

        self.tree = ttk.Treeview(root, columns=("ID", "MMSI", "NMEA", "Received At"), show="headings")
        self.tree.heading("ID", text="ID")
        self.tree.heading("MMSI", text="MMSI")
        self.tree.heading("NMEA", text="NMEA Data")
        self.tree.heading("Received At", text="Received At")
        self.tree.pack(fill=tk.BOTH, expand=True)

        self.refresh_button = tk.Button(root, text="Refresh", command=self.load_data)
        self.refresh_button.pack()

        self.load_data()

    def load_data(self):
        """Ambil data AIS terbaru dari database dan tampilkan di GUI"""
        for row in self.tree.get_children():
            self.tree.delete(row)

        connection = sqlite3.connect(DB_NAME)
        cursor = connection.cursor()
        cursor.execute("SELECT id, mmsi, nmea, received_at FROM ais_history ORDER BY id DESC LIMIT 20")
        rows = cursor.fetchall()
        connection.close()

        for row in rows:
            self.tree.insert("", "end", values=row)

if __name__ == "__main__":
    root = tk.Tk()
    app = AISViewer(root)
    root.mainloop()
