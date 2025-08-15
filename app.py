import os
import sys
import tkinter as tk

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui"))

from ui import main_ui
from utils import db_utils

def main():
    # ===== Ensure DB folders exist =====
    db_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "db")
    if not os.path.exists(db_folder):
        os.makedirs(db_folder)

    db_utils.DB_PATH = os.path.join(db_folder, "restaurant.db")  # Set DB path

    # ===== Create tables =====
    db_utils.create_tables()

    # ===== Sync menu from CSV =====
    db_utils.sync_menu_from_csv()

    # ===== Launch GUI =====
    root = tk.Tk()
    app = main_ui.RestaurantBillingApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
