import sqlite3
import csv
import os
from datetime import datetime

CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "menu.csv")
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "db", "restaurant.db")


# ===== Basic DB Utilities =====
def get_connection():
    return sqlite3.connect(DB_PATH)


def execute_query(query, params=()):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    conn.commit()
    conn.close()


def fetch_one(query, params=()):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    result = cursor.fetchone()
    conn.close()
    return result


def fetch_all(query, params=()):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    result = cursor.fetchall()
    conn.close()
    return result


# ===== Menu & Orders Tables =====
def create_tables():
    execute_query("""
    CREATE TABLE IF NOT EXISTS menu (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        price REAL,
        category TEXT,
        gst REAL
    )
    """)
    execute_query("""
    CREATE TABLE IF NOT EXISTS orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_type TEXT,
        total_amount REAL,
        payment_method TEXT,
        datetime TEXT
    )
    """)
    execute_query("""
    CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER,
        item_name TEXT,
        quantity INTEGER,
        price REAL,
        FOREIGN KEY(order_id) REFERENCES orders(order_id)
    )
    """)
    execute_query("""
    CREATE TABLE IF NOT EXISTS current_orders (
        table_no TEXT,
        item_id INTEGER,
        item_name TEXT,
        quantity INTEGER,
        price REAL
    )
    """)
    execute_query("""
    CREATE TABLE IF NOT EXISTS manager_credentials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        restaurant_name TEXT,
        email TEXT,
        app_password TEXT,
        logo_path TEXT
    )
    """)


def sync_menu_from_csv():
    if not os.path.exists(CSV_PATH):
        print(f"menu.csv not found at {CSV_PATH}")
        return
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header_skipped = False
        for row in reader:
            if not row:
                continue
            # Skip header row
            if not header_skipped:
                header_skipped = True
                if row[0].lower() == 'name':
                    continue
            name, price, category, gst = row[0], float(row[1]), row[2], float(row[3])
            if not fetch_one("SELECT id FROM menu WHERE name=?", (name,)):
                execute_query(
                    "INSERT INTO menu (name, price, category, gst) VALUES (?, ?, ?, ?)",
                    (name, price, category, gst)
                )


def get_menu_items():
    return fetch_all("SELECT id, name, price, category, gst FROM menu")


def get_item_name(item_id):
    result = fetch_one("SELECT name FROM menu WHERE id=?", (item_id,))
    return result[0] if result else "Unknown"


# ===== Current Orders =====
def add_current_order(table_no, item_id, item_name, quantity, price):
    execute_query(
        "INSERT INTO current_orders (table_no, item_id, item_name, quantity, price) VALUES (?, ?, ?, ?, ?)",
        (table_no, item_id, item_name, quantity, price)
    )


def clear_current_orders(table_no):
    execute_query("DELETE FROM current_orders WHERE table_no=?", (table_no,))


# ===== Save Order =====
def save_order(selected_items, total_amount, order_type, payment_method):
    dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    execute_query(
        "INSERT INTO orders (order_type, total_amount, payment_method, datetime) VALUES (?, ?, ?, ?)",
        (order_type, total_amount, payment_method, dt)
    )
    order_id = fetch_one("SELECT last_insert_rowid()")[0]

    # Loop over selected_items dictionary
    for item_id, (var, qty_entry, price, gst) in selected_items.items():
        if var.get() == 1:
            qty_str = qty_entry.get()
            if qty_str.isdigit() and int(qty_str) > 0:
                qty = int(qty_str)
                item_name = get_item_name(item_id)
                execute_query(
                    "INSERT INTO order_items (order_id, item_name, quantity, price) VALUES (?, ?, ?, ?)",
                    (order_id, item_name, qty, price)
                )

    return order_id


# ===== Fetch Orders =====
def get_all_orders():
    return fetch_all(
        "SELECT order_id, order_type, total_amount, payment_method, datetime FROM orders ORDER BY order_id DESC"
    )


def get_order_items(order_id):
    return fetch_all(
        "SELECT item_name, quantity, price FROM order_items WHERE order_id=?", (order_id,)
    )


# ===== Manager Credentials =====
def get_manager_credentials():
    row = fetch_one("SELECT restaurant_name, email, app_password, logo_path FROM manager_credentials LIMIT 1")
    if row:
        return {"restaurant_name": row[0], "email": row[1], "app_password": row[2], "logo_path": row[3]}
    return None


def add_or_update_manager_credentials(restaurant_name, email, app_password, logo_path=""):
    row = fetch_one("SELECT id FROM manager_credentials LIMIT 1")
    if row:
        execute_query(
            "UPDATE manager_credentials SET restaurant_name=?, email=?, app_password=?, logo_path=? WHERE id=?",
            (restaurant_name, email, app_password, logo_path, row[0])
        )
    else:
        execute_query(
            "INSERT INTO manager_credentials (restaurant_name, email, app_password, logo_path) VALUES (?, ?, ?, ?)",
            (restaurant_name, email, app_password, logo_path)
        )
