import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk
from tkinter import messagebox, ttk, simpledialog
from collections import defaultdict
from utils import db_utils
from fpdf import FPDF
import tempfile
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
import base64


class RestaurantBillingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Restaurant Billing System")
        self.root.geometry("1000x700")
        self.root.configure(bg="#f4f6f7")

        db_utils.create_tables()
        db_utils.sync_menu_from_csv()

        # ===== Title =====
        title_label = tk.Label(
            self.root, text="🍽 Restaurant Billing System",
            font=("Arial", 22, "bold"), bg="#2E86C1", fg="white", pady=10
        )
        title_label.pack(fill="x")

        main_frame = tk.Frame(self.root, bg="#f4f6f7")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # ===== Left: Order & Payment =====
        left_frame = tk.Frame(main_frame, bg="#f4f6f7")
        left_frame.pack(side="left", fill="y", padx=10)

        # Order Type
        self.order_type = tk.StringVar(value="Dine-in")
        tk.Label(left_frame, text="Order Type:", font=("Arial", 12, "bold"), bg="#f4f6f7").pack(anchor="w")
        tk.Radiobutton(left_frame, text="Dine-in", variable=self.order_type, value="Dine-in", bg="#f4f6f7").pack(anchor="w")
        tk.Radiobutton(left_frame, text="Takeaway", variable=self.order_type, value="Takeaway", bg="#f4f6f7").pack(anchor="w")

        # Payment Method
        self.payment_method = tk.StringVar(value="Cash")
        tk.Label(left_frame, text="Payment Method:", font=("Arial", 12, "bold"), bg="#f4f6f7", pady=5).pack(anchor="w")
        tk.Radiobutton(left_frame, text="Cash", variable=self.payment_method, value="Cash", bg="#f4f6f7").pack(anchor="w")
        tk.Radiobutton(left_frame, text="Card", variable=self.payment_method, value="Card", bg="#f4f6f7").pack(anchor="w")
        tk.Radiobutton(left_frame, text="UPI", variable=self.payment_method, value="UPI", bg="#f4f6f7").pack(anchor="w")

        # ===== Scrollable Menu =====
        menu_frame_container = tk.Frame(main_frame, bg="#f4f6f7")
        menu_frame_container.pack(side="left", fill="both", expand=True)

        tk.Label(menu_frame_container, text="💡 All items include 5% GST",
                 font=("Arial", 11, "italic"), bg="#f4f6f7", fg="#7B7D7D").pack(anchor="w", pady=(0, 5), padx=5)

        menu_canvas = tk.Canvas(menu_frame_container, bg="#f4f6f7", highlightthickness=0)
        scrollbar = tk.Scrollbar(menu_frame_container, orient="vertical", command=menu_canvas.yview)
        scrollable_menu_frame = tk.Frame(menu_canvas, bg="#f4f6f7")

        scrollable_menu_frame.bind("<Configure>", lambda e: menu_canvas.configure(scrollregion=menu_canvas.bbox("all")))
        menu_canvas.create_window((0, 0), window=scrollable_menu_frame, anchor="nw")
        menu_canvas.configure(yscrollcommand=scrollbar.set)

        menu_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # ===== Bill Frame =====
        bill_frame = tk.LabelFrame(main_frame, text="Bill", font=("Arial", 14, "bold"),
                                   padx=10, pady=10, bg="#f4f6f7", fg="#154360")
        bill_frame.pack(side="right", fill="both", expand=True)

        self.bill_text = tk.Text(bill_frame, font=("Courier", 12), height=20, bg="white", fg="black")
        self.bill_text.pack(fill="both", expand=True)

        # ===== Buttons =====
        btn_frame = tk.Frame(self.root, pady=10, bg="#f4f6f7")
        btn_frame.pack()

        tk.Button(btn_frame, text="Generate Bill", command=self.generate_bill,
                  bg="#28B463", fg="white", font=("Arial", 14), width=15).grid(row=0, column=0, padx=5)
        tk.Button(btn_frame, text="Clear", command=self.clear_all,
                  bg="#E67E22", fg="white", font=("Arial", 14), width=15).grid(row=0, column=1, padx=5)
        tk.Button(btn_frame, text="Exit", command=self.root.quit,
                  bg="#C0392B", fg="white", font=("Arial", 14), width=15).grid(row=0, column=2, padx=5)
        tk.Button(btn_frame, text="View History", command=self.show_history,
                  bg="#5DADE2", fg="white", font=("Arial", 14), width=15).grid(row=0, column=3, padx=5)
        tk.Button(btn_frame, text="Send Bill", command=self.send_bill,
                  bg="#8E44AD", fg="white", font=("Arial", 14), width=15).grid(row=0, column=4, padx=5)

        self.category_order = ["Starters", "Sandwiches", "Pizza", "Pasta",
                               "Main Course", "Rice", "Noodles", "Indian Bread",
                               "Beverages", "Desserts", "Uncategorized"]

        self.category_colors = {
            "Starters": "#FDEDEC",
            "Sandwiches": "#EBDEF0",
            "Pizza": "#E8DAEF",
            "Pasta": "#D6EAF8",
            "Main Course": "#D4EFDF",
            "Rice": "#FCF3CF",
            "Noodles": "#FADBD8",
            "Indian Bread": "#FDEBD0",
            "Beverages": "#D1F2EB",
            "Desserts": "#F9E79F",
            "Uncategorized": "#EAECEE"
        }

        self.menu_items = db_utils.get_menu_items()
        self.selected_items = {}
        self.expanded_state = {}

        self.build_menu(scrollable_menu_frame)

    # ===== Menu & Category =====
    def build_menu(self, parent_frame):
        self.cat_header_frames = {}
        self.cat_items_frames = {}

        category_dict = defaultdict(list)
        for item in self.menu_items:
            if len(item) == 5:
                item_id, name, price, cat, gst = item
            elif len(item) == 4:
                item_id, name, price, cat = item
                gst = 5
            else:
                item_id, name, price = item
                cat, gst = "Uncategorized", 5
            category_dict[cat].append((item_id, name, price, gst))

        for category in self.category_order:
            if category not in category_dict:
                continue

            header_bg = self.category_colors.get(category, "#EAECEE")
            header_frame = tk.Frame(parent_frame, bg=header_bg)
            header_frame.pack(fill="x", pady=2)

            header_label = tk.Label(header_frame, text=category, font=("Arial", 14, "bold"),
                                    bg=header_bg, anchor="w", padx=10)
            header_label.pack(fill="x")

            items_frame = tk.Frame(parent_frame, bg="#F8F9F9")
            items_frame.category = category
            items_frame.populated = False

            header_label.bind("<Button-1>", lambda e, cat=category: self.toggle_category(cat))
            header_frame.bind("<Button-1>", lambda e, cat=category: self.toggle_category(cat))

            self.cat_header_frames[category] = header_frame
            self.cat_items_frames[category] = items_frame
            self.expanded_state[category] = False

    def toggle_category(self, category):
        items_frame = self.cat_items_frames[category]
        header_frame = self.cat_header_frames[category]

        if self.expanded_state.get(category, False):
            items_frame.pack_forget()
            self.expanded_state[category] = False
            return

        if not items_frame.populated:
            for item in self.menu_items:
                if len(item) == 5:
                    item_id, name, price, cat, gst = item
                elif len(item) == 4:
                    item_id, name, price, cat = item
                    gst = 5
                else:
                    item_id, name, price = item
                    cat, gst = "Uncategorized", 5
                if cat != category:
                    continue

                row = tk.Frame(items_frame, bg="#F8F9F9")
                var = tk.IntVar()
                chk = tk.Checkbutton(row, text=f"{name} - ₹{price}", variable=var,
                                     font=("Arial", 12), bg="#F8F9F9", anchor="w")
                chk.pack(side="left", padx=15, pady=1)

                qty_entry = tk.Entry(row, width=5)
                qty_entry.pack(side="right", padx=15, pady=1)

                if item_id in self.selected_items:
                    old_var, old_qty, *_ = self.selected_items[item_id]
                    qty_entry.delete(0, tk.END)
                    qty_entry.insert(0, old_qty.get() if old_qty.get() else "")
                    var.set(old_var.get())
                self.selected_items[item_id] = (var, qty_entry, price, gst)
                row.pack(fill="x")
            items_frame.populated = True

        items_frame.pack(fill="x", padx=20, pady=2, after=header_frame)
        self.expanded_state[category] = True

    # ===== Generate Bill =====
    def generate_bill(self):
        self.bill_text.delete(1.0, tk.END)
        self.bill_text.insert(tk.END, "===== Restaurant Bill =====\n\n")
        self.bill_text.insert(tk.END, f"Order Type: {self.order_type.get()}\n")
        self.bill_text.insert(tk.END, f"Payment Method: {self.payment_method.get()}\n\n")

        subtotal = 0
        gst_total = 0

        for item_id, (var, qty_entry, price, gst) in self.selected_items.items():
            if var.get() == 1:
                qty_str = qty_entry.get()
                if qty_str.isdigit() and int(qty_str) > 0:
                    qty = int(qty_str)
                    total_price = price * qty
                    gst_amt = (total_price * gst) / 100
                    subtotal += total_price
                    gst_total += gst_amt
                    self.bill_text.insert(tk.END, f"{db_utils.get_item_name(item_id)} x {qty} = ₹{total_price}\n")
                else:
                    messagebox.showerror("Error", "Invalid quantity entered")
                    return

        total_amount = subtotal + gst_total
        self.bill_text.insert(tk.END, f"\nSubtotal: ₹{subtotal}")
        self.bill_text.insert(tk.END, f"\nGST Total: ₹{gst_total}")
        self.bill_text.insert(tk.END, f"\nTotal Amount: ₹{total_amount}")

        # Save order
        db_utils.save_order(self.selected_items, total_amount, self.order_type.get(), self.payment_method.get())

    # ===== PDF Generation =====
    def save_bill_as_pdf(self):
        pdf = FPDF()
        pdf.add_page()

        # ===== Register Unicode font =====
        # Replace 'DejaVuSans.ttf' with your actual font path if different
        pdf.add_font('DejaVu', '', r'ui\DejaVuSans.ttf', uni=True)
        pdf.add_font('DejaVu', 'B', r'ui\DejaVuSans-Bold.ttf', uni=True) # Bold
        pdf.add_font('DejaVu', 'I', r'ui\DejaVuSans-Oblique.ttf', uni=True) # Italic (optional)

        pdf.set_font('DejaVu', 'B', 16)
        pdf.cell(0, 10, "DineDash Restaurant", ln=True, align="C")

        pdf.set_font('DejaVu', 'B', 14)
        pdf.cell(0, 10, "Restaurant Bill", ln=True, align="C")
        pdf.ln(5)

        pdf.set_font('DejaVu', '', 12)
        pdf.cell(0, 8, f"Order Type: {self.order_type.get()}", ln=True)
        pdf.cell(0, 8, f"Payment Method: {self.payment_method.get()}", ln=True)
        pdf.ln(5)

        pdf.set_font('DejaVu', 'B', 12)
        pdf.cell(90, 8, "Item", border=1)
        pdf.cell(25, 8, "Qty", border=1, align="C")
        pdf.cell(35, 8, "Price", border=1, align="R")
        pdf.cell(35, 8, "Total", border=1, align="R")
        pdf.ln()

        pdf.set_font('DejaVu', '', 12)
        subtotal = 0
        gst_total = 0
        for item_id, (var, qty_entry, price, gst) in self.selected_items.items():
            if var.get() == 1:
                qty_str = qty_entry.get()
                if qty_str.isdigit() and int(qty_str) > 0:
                    qty = int(qty_str)
                    total_price = price * qty
                    gst_amt = (total_price * gst) / 100
                    subtotal += total_price
                    gst_total += gst_amt
                    pdf.cell(90, 8, db_utils.get_item_name(item_id), border=1)
                    pdf.cell(25, 8, str(qty), border=1, align="C")
                    pdf.cell(35, 8, f"₹{price}", border=1, align="R")
                    pdf.cell(35, 8, f"₹{total_price}", border=1, align="R")
                    pdf.ln()

        total_amount = subtotal + gst_total
        pdf.ln(2)
        pdf.cell(150, 8, "Subtotal:", border=0, align="R")
        pdf.cell(35, 8, f"₹{subtotal}", border=1, align="R")
        pdf.ln()
        pdf.cell(150, 8, "GST Total:", border=0, align="R")
        pdf.cell(35, 8, f"₹{gst_total}", border=1, align="R")
        pdf.ln()
        pdf.cell(150, 8, "Total Amount:", border=0, align="R")
        pdf.cell(35, 8, f"₹{total_amount}", border=1, align="R")

        temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        pdf.output(temp_pdf.name)
        return temp_pdf.name


    # ===== SendGrid Email =====
    def send_email_bill(self, to_email, pdf_path):
        sender_email = "demo.restaurant1234@gmail.com"  # verified in SendGrid
        subject = "Your DineDash Bill"
        content = "Thank you for dining with us! Your bill is attached."

        with open(pdf_path, "rb") as f:
            pdf_data = f.read()
        encoded_pdf = base64.b64encode(pdf_data).decode()

        attachment = Attachment(
            FileContent(encoded_pdf),
            FileName("bill.pdf"),
            FileType("application/pdf"),
            Disposition("attachment")
        )

        message = Mail(
            from_email=sender_email,
            to_emails=to_email,
            subject=subject,
            plain_text_content=content
        )
        message.attachment = attachment

        try:
            sg = SendGridAPIClient("SENDGRID-API-KEY")
            response = sg.send(message)
            if 200 <= response.status_code < 300:
                messagebox.showinfo("Success", f"Bill sent to {to_email} successfully!")
            else:
                messagebox.showerror("Error", f"Failed to send email. Status Code: {response.status_code}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to send email: {e}")

    # ===== Send Bill =====
    def send_bill(self):
        # Generate PDF for the current selected items
        pdf_path = self.save_bill_as_pdf()

        # Ask for customer email
        email = simpledialog.askstring("Send Bill", "Enter customer email to send bill:")
        if not email:
            return  # Exit if user cancels or leaves blank

        sender_email = " "  # replace with your verified email
        subject = "Your DineDash Bill"
        content = "Thank you for dining with us! Your bill is attached."

        # Read and encode PDF
        with open(pdf_path, "rb") as f:
            pdf_data = f.read()
        encoded_pdf = base64.b64encode(pdf_data).decode()

        # Create attachment
        attachment = Attachment(
            FileContent(encoded_pdf),
            FileName("bill.pdf"),
            FileType("application/pdf"),
            Disposition("attachment")
        )

        # Prepare email
        message = Mail(
            from_email=sender_email,
            to_emails=email,
            subject=subject,
            plain_text_content=content
        )
        message.attachment = attachment

        # Send email
        try:
            sg = SendGridAPIClient("SENDGRID-API-KEY")  # replace with your API key
            response = sg.send(message)
            if 200 <= response.status_code < 300:
                messagebox.showinfo("Success", f"Bill sent to {email} successfully!")
            else:
                messagebox.showerror("Error", f"Failed to send email. Status Code: {response.status_code}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to send email: {e}")


    # ===== Other Utility Functions =====
    def clear_all(self):
        for var, qty_entry, *_ in self.selected_items.values():
            var.set(0)
            qty_entry.delete(0, tk.END)
        self.bill_text.delete(1.0, tk.END)

    def show_history(self):
        history_win = tk.Toplevel(self.root)
        history_win.title("Order History")
        history_win.geometry("800x400")

        cols = ("Order ID", "Order Type", "Total Amount", "Payment Method", "Date/Time")
        tree = ttk.Treeview(history_win, columns=cols, show="headings")
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=150)
        tree.pack(fill="both", expand=True)

        orders = db_utils.get_all_orders()
        for order in orders:
            tree.insert("", "end", values=order)

        def on_order_select(event):
            selected = tree.selection()
            if not selected:
                return
            order_data = tree.item(selected[0], "values")
            self.show_order_details(order_data[0])

        tree.bind("<Double-1>", on_order_select)

    def show_order_details(self, order_id):
        details_win = tk.Toplevel(self.root)
        details_win.title(f"Order Details - ID {order_id}")
        details_win.geometry("500x400")

        tk.Label(details_win, text=f"Order ID: {order_id}", font=("Arial", 12, "bold")).pack()
        items = db_utils.get_order_items(order_id)
        txt = tk.Text(details_win, font=("Courier", 12))
        for item_name, qty in items:
            txt.insert(tk.END, f"{item_name} x {qty}\n")
        txt.pack(fill="both", expand=True)


if __name__ == "__main__":
    root = tk.Tk()
    app = RestaurantBillingApp(root)
    root.mainloop()

