import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import db_utils

def calculate_totals(selected_data):
    """
    Calculate subtotal, GST total, and final total for the selected items.
    
    selected_data: List of dicts like:
        [{'item_id': 1, 'qty': 2, 'price': 100, 'gst': 5}, ...]
    
    Returns:
        dict with 'subtotal', 'gst_total', 'total_amount', 'bill_lines'
    """
    subtotal = 0
    gst_total = 0
    bill_lines = []

    for item in selected_data:
        # Ensure numeric values
        try:
            price = float(item.get('price', 0))
        except ValueError:
            price = 0.0
        try:
            qty = int(item.get('qty', 0))
        except ValueError:
            qty = 0
        try:
            gst_percent = float(item.get('gst', 0))
        except ValueError:
            gst_percent = 0.0

        total_price = round(price * qty, 2)
        gst_amount = round(total_price * gst_percent / 100, 2)

        subtotal += total_price
        gst_total += gst_amount

        # Fetch item name safely from DB
        item_name = db_utils.get_item_name(item.get('item_id')) or f"Item {item.get('item_id')}"
        bill_lines.append(f"{item_name} x {qty} = ₹{total_price:.2f} (+{gst_amount:.2f} GST)")

    total_amount = subtotal + gst_total

    return {
        'subtotal': round(subtotal, 2),
        'gst_total': round(gst_total, 2),
        'total_amount': round(total_amount, 2),
        'bill_lines': bill_lines
    }
