from flask import Flask, render_template, request, jsonify, send_file
import mysql.connector
from datetime import datetime
import csv
import io

app = Flask(__name__)

# MySQL config
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '0000',  # Replace with your MySQL password
    'database': 'data_portal'
}

conn = mysql.connector.connect(**db_config)
cursor = conn.cursor(dictionary=True)

tables_list = ['id_grind','od_grind','od_patch','milling','wasem','turning']

@app.route('/')
def index():
    return render_template('index.html', tables=tables_list)

@app.route('/get_items')
def get_items():
    table = request.args.get('table')
    if table not in tables_list:
        return jsonify([])

    try:
        if table.lower() == 'wasem':
            cursor.execute(f"SELECT DISTINCT Item, Code, G_Rate, H_Rate FROM {table} WHERE Item IS NOT NULL")
        else:
            cursor.execute(f"SELECT DISTINCT Item, Code, Rate FROM {table} WHERE Item IS NOT NULL")
        items = cursor.fetchall()
        return jsonify(items)
    except Exception as e:
        print("Error fetching items:", e)
        return jsonify([])

@app.route('/submit', methods=['POST'])
def submit():
    data = request.get_json()
    table_name = data.get('table')
    date_str = data.get('date')
    item = data.get('item')
    code = data.get('code')
    rate = data.get('rate')
    quantity = float(data.get('quantity'))
    total = data.get('total')

    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    table_month = f"{date_obj.year}_{date_obj.month:02d}"
    final_table = f"submitted_{table_name}_{table_month}"

    try:
        if table_name.lower() == "wasem":
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {final_table} (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    date DATE,
                    item VARCHAR(100),
                    code VARCHAR(50),
                    g_rate FLOAT,
                    h_rate FLOAT,
                    quantity FLOAT,
                    g_total FLOAT,
                    h_total FLOAT
                )
            """)
            g_rate, h_rate = [float(x.strip()) for x in rate.replace("G:", "").replace("H:", "").split("|")]
            g_total, h_total = [float(x.strip()) for x in total.replace("G Total:", "").replace("H Total:", "").split("|")]
            cursor.execute(f"""
                INSERT INTO {final_table} (date, item, code, g_rate, h_rate, quantity, g_total, h_total)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """, (date_str, item, code, g_rate, h_rate, quantity, g_total, h_total))
        else:
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {final_table} (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    date DATE,
                    item VARCHAR(100),
                    code VARCHAR(50),
                    rate FLOAT,
                    quantity FLOAT,
                    total FLOAT
                )
            """)
            cursor.execute(f"""
                INSERT INTO {final_table} (date, item, code, rate, quantity, total)
                VALUES (%s,%s,%s,%s,%s,%s)
            """, (date_str, item, code, float(rate), quantity, float(total)))

        conn.commit()
        return "✅ Data submitted successfully!"
    except Exception as e:
        print("Error inserting data:", e)
        return "❌ Failed to submit data."

@app.route('/view', methods=['GET', 'POST'])
def view_data():
    cursor.execute("SHOW TABLES LIKE 'submitted_%'")
    all_tables = [list(row.values())[0] for row in cursor.fetchall()]
    tables_set = set()
    for t in all_tables:
        parts = t.split("_")
        if len(parts) >= 4:
            table_name = parts[1]
            month_year = f"{parts[2]}_{parts[3]}"
            tables_set.add((table_name, month_year))
    tables_sorted = sorted(list(tables_set))

    selected_table = None
    selected_month = None
    rows = []

    if request.method == 'POST':
        table_month = request.form.get('table_month')  # e.g., id_grind_2025_10
        parts = table_month.split("_")
        selected_table = parts[0]
        selected_month = "_".join(parts[1:])
        final_table = f"submitted_{selected_table}_{selected_month}"
        try:
            cursor.execute(f"SELECT * FROM {final_table} ORDER BY id DESC")
            rows = cursor.fetchall()
        except Exception as e:
            print("Error fetching table:", e)
            rows = []

    return render_template('view.html', tables_list=tables_sorted, rows=rows,
                           selected_table=selected_table, selected_month=selected_month)

@app.route('/download', methods=['GET'])
def download_data():
    table_month = request.args.get('table_month')
    if not table_month:
        return "Table not selected"

    parts = table_month.split("_")
    table = parts[0]
    month = "_".join(parts[1:])
    final_table = f"submitted_{table}_{month}"

    try:
        cursor.execute(f"SELECT * FROM {final_table}")
        rows = cursor.fetchall()
        if not rows:
            return "No data found"

        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(rows[0].keys())
        for row in rows:
            writer.writerow(row.values())
        output.seek(0)

        return send_file(io.BytesIO(output.getvalue().encode()),
                         mimetype='text/csv',
                         download_name=f"{final_table}.csv",
                         as_attachment=True)
    except Exception as e:
        print("Error generating CSV:", e)
        return "Failed to download CSV"

if __name__ == '__main__':
    app.run(debug=True)
