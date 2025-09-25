# billing_final.py
import sqlite3
from flask import Flask, render_template_string, request, redirect, Response
from io import StringIO
import csv
from datetime import datetime, timedelta
from num2words import num2words   # for amount in words

app = Flask(__name__)

DB = "billing_final.db"
GST_PERCENT = 18  # GST rate

# ---------------- Database Setup ----------------
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    # customers table now includes gstin
    c.execute('''CREATE TABLE IF NOT EXISTS customers
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT,
                  phone TEXT,
                  email TEXT,
                  address TEXT,
                  gstin TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS items
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, price REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS invoices
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER, date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS invoice_items
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, invoice_id INTEGER, item_id INTEGER, qty INTEGER)''')
    conn.commit()
    conn.close()

# ---------------- Template ----------------
template = """ 
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>INetwork Hub Billing</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
body{background:#f8f9fa;}
.sidebar{height:100vh;background:#343a40;color:#fff;position:fixed;width:220px;padding-top:20px;}
.sidebar a{color:#fff;text-decoration:none;display:block;padding:10px 15px;margin:5px 0;border-radius:5px;}
.sidebar a:hover{background:#495057;}
.content{margin-left:240px;padding:20px;}
.navbar{margin-left:220px;}
</style>
</head>
<body>
<div class="sidebar">
<h4 class="text-center">INetwork Hub Billing</h4>
<a href="#dashboard" onclick="showDiv('dashboard')">Dashboard</a>
<a href="#customers" onclick="showDiv('customers')">Customers</a>
<a href="#items" onclick="showDiv('items')">Items</a>
<a href="#invoices" onclick="showDiv('invoices')">Invoices</a>
<a href="#export" onclick="showDiv('export')">Export CSV</a>
</div>

<nav class="navbar navbar-light bg-light">
<div class="container-fluid">
<span class="navbar-brand mb-0 h1">Billing Final Software</span>
<button class="btn btn-primary" onclick="showDiv('addInvoice')">+ New Invoice</button>
</div>
</nav>

<div class="content">
<!-- Dashboard -->
<div id="dashboard">
<h3>Dashboard</h3>
<div class="row">
<div class="col-md-3"><div class="card shadow-sm mb-3"><div class="card-body"><h5>Total Customers</h5><p class="fs-4">{{total_customers}}</p></div></div></div>
<div class="col-md-3"><div class="card shadow-sm mb-3"><div class="card-body"><h5>Total Items</h5><p class="fs-4">{{total_items}}</p></div></div></div>
<div class="col-md-3"><div class="card shadow-sm mb-3"><div class="card-body"><h5>Total Invoices</h5><p class="fs-4">{{total_invoices}}</p></div></div></div>
<div class="col-md-3"><div class="card shadow-sm mb-3"><div class="card-body"><h5>Total Revenue</h5><p class="fs-4">₹{{total_revenue}}</p></div></div></div>
</div>
</div>

<!-- Customers -->
<div id="customers" style="display:none;">
<h3>Customers <button class="btn btn-sm btn-success" onclick="showDiv('addCustomer')">+ Add</button></h3>
<table class="table table-striped">
<thead><tr><th>Name</th><th>Phone</th><th>Email</th><th>Address</th><th>GSTIN</th><th>Actions</th></tr></thead>
<tbody>
{% for c in customers %}
<tr>
<td>{{c[1]}}</td><td>{{c[2]}}</td><td>{{c[3]}}</td><td>{{c[4]}}</td><td>{{c[5]}}</td>
<td>
<form method="post" action="/delete_customer" style="display:inline;"><input type="hidden" name="id" value="{{c[0]}}">
<button class="btn btn-sm btn-danger" type="submit">Delete</button></form>
</td>
</tr>
{% endfor %}
</tbody>
</table>
</div>

<!-- Items -->
<div id="items" style="display:none;">
<h3>Items <button class="btn btn-sm btn-success" onclick="showDiv('addItem')">+ Add</button></h3>
<table class="table table-striped">
<thead><tr><th>Name</th><th>Price</th><th>Actions</th></tr></thead>
<tbody>
{% for i in items %}
<tr>
<td>{{i[1]}}</td><td>{{i[2]}}</td>
<td>
<form method="post" action="/delete_item" style="display:inline;"><input type="hidden" name="id" value="{{i[0]}}">
<button class="btn btn-sm btn-danger" type="submit">Delete</button></form>
</td>
</tr>
{% endfor %}
</tbody>
</table>
</div>

<!-- Invoices -->
<div id="invoices" style="display:none;">
<h3>Invoices</h3>
<table class="table table-striped">
<thead><tr><th>ID</th><th>Customer</th><th>Date</th><th>Total (₹)</th><th>Actions</th></tr></thead>
<tbody>
{% for inv in invoices %}
<tr>
<td>{{inv[0]}}</td><td>{{inv[1]}}</td><td>{{inv[2]}}</td><td>{{inv[3]}}</td>
<td>
<form method="post" action="/delete_invoice" style="display:inline;">
<input type="hidden" name="id" value="{{inv[0]}}">
<button class="btn btn-sm btn-danger" type="submit">Delete</button></form>
<a class="btn btn-sm btn-primary" href="/print_invoice/{{inv[0]}}" target="_blank">Print</a>
</td>
</tr>
{% endfor %}
</tbody>
</table>
</div>

<!-- Export CSV -->
<div id="export" style="display:none;">
<h3>Export Invoices CSV</h3>
<a class="btn btn-success" href="/export_csv">Download CSV</a>
</div>

<!-- Add Customer -->
<div id="addCustomer" style="display:none;">
<h3>Add Customer</h3>
<form method="post" action="/add_customer">
<div class="mb-3"><input type="text" name="name" class="form-control" placeholder="Name" required></div>
<div class="mb-3"><input type="text" name="phone" class="form-control" placeholder="Phone"></div>
<div class="mb-3"><input type="email" name="email" class="form-control" placeholder="Email"></div>
<div class="mb-3"><input type="text" name="address" class="form-control" placeholder="Address"></div>
<div class="mb-3"><input type="text" name="gstin" class="form-control" placeholder="GSTIN"></div>
<button class="btn btn-primary" type="submit">Save</button>
<button class="btn btn-secondary" type="button" onclick="showDiv('customers')">Cancel</button>
</form>
</div>

<!-- Add Item -->
<div id="addItem" style="display:none;">
<h3>Add Item</h3>
<form method="post" action="/add_item">
<div class="mb-3"><input type="text" name="name" class="form-control" placeholder="Item Name" required></div>
<div class="mb-3"><input type="number" name="price" class="form-control" placeholder="Price" step="0.01" required></div>
<button class="btn btn-primary" type="submit">Save</button>
<button class="btn btn-secondary" type="button" onclick="showDiv('items')">Cancel</button>
</form>
</div>

<!-- Add Invoice -->
<div id="addInvoice" style="display:none;">
<h3>Add Invoice</h3>
<form method="post" action="/add_invoice">
<div class="mb-3"><select class="form-control" name="customer_id" required>
<option value="">Select Customer</option>
{% for c in customers %}<option value="{{c[0]}}">{{c[1]}}</option>{% endfor %}
</select></div>
<div class="mb-3">
{% for i in items %}
<div>
<input type="checkbox" name="item_id" value="{{i[0]}}"> {{i[1]}} (₹{{i[2]}})
<input type="number" name="qty_{{i[0]}}" placeholder="Qty" value="1" style="width:60px;">
</div>
{% endfor %}
</div>
<div class="mb-3"><input type="date" name="date" class="form-control" required></div>
<button class="btn btn-primary" type="submit">Save Invoice</button>
<button class="btn btn-secondary" type="button" onclick="showDiv('dashboard')">Cancel</button>
</form>
</div>

</div>

<script>
function showDiv(id){
let sections=['dashboard','customers','items','invoices','addCustomer','addItem','addInvoice','export'];
sections.forEach(s=>document.getElementById(s).style.display='none');
document.getElementById(id).style.display='block';
}
</script>

</body>
</html>
"""

# ---------------- Routes ----------------
@app.route('/')
def home():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM customers")
    total_customers = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM items")
    total_items = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM invoices")
    total_invoices = c.fetchone()[0]
    
    # Total revenue calculation
    c.execute('''SELECT invoice_items.qty, items.price 
                 FROM invoice_items LEFT JOIN items ON invoice_items.item_id = items.id''')
    rows = c.fetchall()
    total_revenue = sum(qty*price*(1+GST_PERCENT/100) for qty, price in rows)

    c.execute("SELECT * FROM customers")
    customers = c.fetchall()
    c.execute("SELECT * FROM items")
    items = c.fetchall()
    c.execute('''SELECT invoices.id, customers.name, invoices.date
                 FROM invoices LEFT JOIN customers ON invoices.customer_id = customers.id
                 ORDER BY invoices.id DESC''')
    invoices = c.fetchall()
    conn.close()
    # Calculate invoice total dynamically
    invoices_total = []
    for inv in invoices:
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute('''SELECT invoice_items.qty, items.price FROM invoice_items 
                     LEFT JOIN items ON invoice_items.item_id = items.id 
                     WHERE invoice_items.invoice_id=?''', (inv[0],))
        rows = c.fetchall()
        total = sum(qty*price*(1+GST_PERCENT/100) for qty, price in rows)
        invoices_total.append((inv[0], inv[1], inv[2], round(total,2)))
        conn.close()
    return render_template_string(template,
                                  total_customers=total_customers,
                                  total_items=total_items,
                                  total_invoices=total_invoices,
                                  total_revenue=round(total_revenue,2),
                                  customers=customers,
                                  items=items,
                                  invoices=invoices_total)

# ---------------- Add / Delete ----------------
@app.route('/add_customer', methods=['POST'])
def add_customer():
    data = request.form
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT INTO customers (name, phone, email, address, gstin) VALUES (?,?,?,?,?)",
              (data['name'], data.get('phone'), data.get('email'), data.get('address'), data.get('gstin')))
    conn.commit()
    conn.close()
    return redirect('/')

@app.route('/delete_customer', methods=['POST'])
def delete_customer():
    cid = request.form['id']
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("DELETE FROM customers WHERE id=?", (cid,))
    conn.commit()
    conn.close()
    return redirect('/')

@app.route('/add_item', methods=['POST'])
def add_item():
    data = request.form
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT INTO items (name, price) VALUES (?,?)", (data['name'], data['price']))
    conn.commit()
    conn.close()
    return redirect('/')

@app.route('/delete_item', methods=['POST'])
def delete_item():
    iid = request.form['id']
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("DELETE FROM items WHERE id=?", (iid,))
    conn.commit()
    conn.close()
    return redirect('/')

# ---------------- Add Invoice ----------------
@app.route('/add_invoice', methods=['POST'])
def add_invoice():
    data = request.form
    customer_id = data['customer_id']
    date = data['date']
    items_selected = request.form.getlist('item_id')
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT INTO invoices (customer_id, date) VALUES (?,?)", (customer_id, date))
    invoice_id = c.lastrowid
    for item_id in items_selected:
        qty = int(data.get(f"qty_{item_id}",1))
        c.execute("INSERT INTO invoice_items (invoice_id, item_id, qty) VALUES (?,?,?)",
                  (invoice_id, item_id, qty))
    conn.commit()
    conn.close()
    return redirect('/')

@app.route('/delete_invoice', methods=['POST'])
def delete_invoice():
    iid = request.form['id']
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("DELETE FROM invoice_items WHERE invoice_id=?", (iid,))
    c.execute("DELETE FROM invoices WHERE id=?", (iid,))
    conn.commit()
    conn.close()
    return redirect('/')

# ---------------- Print Invoice ----------------
@app.route('/print_invoice/<int:invoice_id>')
def print_invoice(invoice_id):
    COMPANY_NAME = "INetwork Hub Pvt. Ltd."
    COMPANY_ADDRESS = "123, Main Street, Kolkata"
    COMPANY_PHONE = "+91 9065860876"
    COMPANY_EMAIL = "info@inetworkhub.com"
    COMPANY_LOGO = "/static/logo.png"
    COMPANY_GSTIN = "22AAAAA0000A1Z5"

    BANK_NAME = "State Bank of India"
    IFSC_CODE = "SBIN0001234"
    ACCOUNT_NUMBER = "123456789012"

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''SELECT invoices.id, customers.name, customers.phone, customers.email, 
                 customers.address, customers.gstin, invoices.date
                 FROM invoices 
                 LEFT JOIN customers ON invoices.customer_id = customers.id
                 WHERE invoices.id=?''', (invoice_id,))
    invoice = c.fetchone()
    
    c.execute('''SELECT items.name, invoice_items.qty, items.price
                 FROM invoice_items 
                 LEFT JOIN items ON invoice_items.item_id = items.id
                 WHERE invoice_items.invoice_id=?''', (invoice_id,))
    items = c.fetchall()
    conn.close()

    subtotal = sum(it[2] * it[1] for it in items)
    gst_amount = subtotal * GST_PERCENT / 100
    grand_total = subtotal + gst_amount
    amount_words = num2words(grand_total, lang='en').title() + " Only"

    inv_date = datetime.strptime(invoice[6], "%Y-%m-%d")
    due_date = inv_date + timedelta(days=7)
    invoice_number = f"INH-{invoice[0]:03d}"

    CUSTOMER_GSTIN = invoice[5] if invoice[5] else "N/A"

    html = f"""
    <html>
    <head>
    <style>
    body {{ font-family: Arial, sans-serif; margin: 20px; }}
    .header {{ display:flex; align-items:center; }}
    .logo {{ width:120px; height:60px; margin-right:20px; }}
    .company-details {{ font-size:14px; }}
    .bill-box {{ margin-top:20px; display:flex; justify-content:space-between; }}
    .bill-from, .bill-to {{ border:1px solid #ddd; padding:10px; width:45%; }}
    table {{ width:100%; border-collapse: collapse; margin-top:20px; }}
    table, th, td {{ border:1px solid #000; }}
    th, td {{ padding:8px; text-align:left; }}
    .totals {{ margin-top:20px; width:100%; }}
    .signature {{ margin-top:20px; text-align:right; }}
    .footer {{ margin-top:40px; display:flex; justify-content:space-between; }}
    .bank-details {{ font-size:14px; }}
    .nospacing {{ letter-spacing:0; word-spacing:0; white-space:nowrap; }}
    </style>
    </head>
    <body>

    <div class="header">
        <img src="{COMPANY_LOGO}" class="logo">
        <div class="company-details">
            <strong>{COMPANY_NAME}</strong><br>
            {COMPANY_ADDRESS}<br>
            {COMPANY_PHONE} | {COMPANY_EMAIL}<br>
            <strong class="nospacing">GSTIN:</strong> {COMPANY_GSTIN}
        </div>
    </div>

    <div class="bill-box">
        <div class="bill-from">
            <strong>Bill From:</strong><br>
            {COMPANY_NAME}<br>
            {COMPANY_ADDRESS}<br>
            {COMPANY_PHONE} | {COMPANY_EMAIL}<br>
            <strong class="nospacing">GSTIN:</strong> {COMPANY_GSTIN}
        </div>
        <div class="bill-to">
            <strong>Bill To:</strong><br>
            {invoice[1]}<br>
            {invoice[4]}<br>
            {invoice[2]} | {invoice[3]}<br>
            <strong class="nospacing">GSTIN:</strong> {CUSTOMER_GSTIN}<br>
            <strong>Invoice Date:</strong> {invoice[6]}<br>
            <strong>Due Date:</strong> {due_date.strftime("%Y-%m-%d")}<br>
            <strong>Invoice No:</strong> {invoice_number}
        </div>
    </div>

    <table>
        <tr>
            <th>Item</th><th>Qty</th><th>Price (₹)</th><th>Total (₹)</th><th>GST (₹)</th>
        </tr>
    """
    # items rows
    for it in items:
        line_total = it[2] * it[1]
        line_gst = line_total * GST_PERCENT / 100
        html += f"""
        <tr>
            <td>{it[0]}</td>
            <td>{it[1]}</td>
            <td>{it[2]:.2f}</td>
            <td>{line_total:.2f}</td>
            <td>{line_gst:.2f}</td>
        </tr>
        """

    # totals & signature
    html += f"""
    </table>

    <div class="totals">
        <p><strong>Subtotal:</strong> ₹{subtotal:.2f}</p>
        <p><strong>GST ({GST_PERCENT}%):</strong> ₹{gst_amount:.2f}</p>
        <h3>Grand Total: ₹{grand_total:.2f}</h3>
        <p><em>In Words: {amount_words}</em></p>
    </div>

    <div class="signature">
        <div style="border:1px solid #000; padding:15px; width:220px; text-align:center; display:inline-block; margin-left:auto;">
            Authorized Signatory
            <br><br>
            _______________
        </div>
    </div>

    <div class="footer">
        <div class="bank-details">
            <strong>Bank Details:</strong><br>
            Bank: {BANK_NAME}<br>
            A/C: {ACCOUNT_NUMBER}<br>
            IFSC: {IFSC_CODE}
        </div>
    </div>

    <div style="clear:both; margin-top:50px;">
        <em>Thank you for your business!</em>
    </div>

    <button onclick="window.print()" style="margin-top:20px;">Print</button>
    </body>
    </html>
    """
    return html

# ---------------- Export CSV ----------------
@app.route('/export_csv')
def export_csv():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''SELECT invoices.id, customers.name, invoices.date, items.name, invoice_items.qty, items.price, customers.gstin
                 FROM invoices 
                 LEFT JOIN customers ON invoices.customer_id = customers.id
                 LEFT JOIN invoice_items ON invoices.id = invoice_items.invoice_id
                 LEFT JOIN items ON invoice_items.item_id = items.id''')
    rows = c.fetchall()
    conn.close()

    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(["Invoice ID","Customer","Date","Item","Qty","Price","Customer GSTIN"])
    cw.writerows(rows)
    output = si.getvalue()
    return Response(output, mimetype="text/csv",
                    headers={"Content-Disposition":"attachment;filename=invoices.csv"})

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=10000, debug=True)

