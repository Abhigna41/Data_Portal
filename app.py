from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, session
import mysql.connector
from datetime import datetime
import csv, io

app = Flask(__name__)
app.secret_key = "project_application_7days"

# MySQL config
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '0000',
    'database': 'data_portal'
}

conn = mysql.connector.connect(**db_config)
cursor = conn.cursor(dictionary=True)

tables_list = ['id_grind','od_grind','od_patch','milling','wasem','turning']

# ---------------- LOGIN ----------------
@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    if username == "admin" and password == "1234":
        session['user'] = username
        return redirect(url_for('portal'))
    return render_template('login.html', error="Invalid username or password")

@app.route('/portal')
def portal():
    if 'user' not in session:
        return redirect(url_for('index'))
    return render_template('index.html', tables=tables_list)

# ---------------- DATA ENDPOINTS ----------------
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
        return jsonify(cursor.fetchall())
    except Exception as e:
        print(e)
        return jsonify([])

@app.route('/submit', methods=['POST'])
def submit():
    data = request.get_json()
    table_name = data['table']
    date_str = data['date']
    item = data['item']
    code = data['code']
    rate = data['rate']
    quantity = float(data['quantity'])
    total = data['total']

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
                    G_Rate FLOAT,
                    H_Rate FLOAT,
                    quantity FLOAT,
                    G_Total FLOAT,
                    H_Total FLOAT
                )
            """)
            g_rate, h_rate = [float(x.strip()) for x in rate.replace("G:","").replace("H:","").split("|")]
            g_total, h_total = [float(x.strip()) for x in total.replace("G Total:","").replace("H Total:","").split("|")]
            cursor.execute(f"""
                INSERT INTO {final_table} (date,item,code,G_Rate,H_Rate,quantity,G_Total,H_Total)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """,(date_str,item,code,g_rate,h_rate,quantity,g_total,h_total))
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
                INSERT INTO {final_table} (date,item,code,rate,quantity,total)
                VALUES (%s,%s,%s,%s,%s,%s)
            """,(date_str,item,code,float(rate),quantity,float(total)))
        conn.commit()
        return "✅ Data submitted successfully!"
    except Exception as e:
        print(e)
        return "❌ Failed to submit data."

# ---------------- VIEW & DOWNLOAD ----------------
@app.route('/view', methods=['GET','POST'])
def view_data():
    # All predefined tables
    all_tables = ['id_grind', 'od_grind', 'od_patch', 'milling', 'wasem', 'turning']

    # Build dictionary: table_name -> list of months
    table_month_dict = {}
    cursor.execute("SHOW TABLES LIKE 'submitted_%'")
    submitted_tables = [list(r.values())[0] for r in cursor.fetchall()]

    for table_name in all_tables:
        table_month_dict[table_name] = []
        for t in submitted_tables:
            # Remove 'submitted_' prefix
            if not t.startswith("submitted_"):
                continue
            table_part = t.replace("submitted_", "", 1)
            # Split from last 2 underscores
            parts = table_part.rsplit("_", 2)
            if len(parts) != 3:
                continue
            name, year, month = parts
            if name == table_name:
                table_month_dict[table_name].append(f"{year}_{month}")

    selected_table = None
    selected_month = None
    rows = []
    message = ""

    if request.method == 'POST':
        selected_table = request.form.get('table')
        selected_month = request.form.get('month')
        if selected_table and selected_month:
            final_table = f"submitted_{selected_table}_{selected_month}"
            try:
                cursor.execute(f"SELECT * FROM {final_table} ORDER BY id DESC")
                rows = cursor.fetchall()
                if not rows:
                    message = "⚠️ No data found for selected table/month."
            except:
                message = "⚠️ No data found for selected table/month."

    return render_template(
        'view.html',
        table_month_dict=table_month_dict,
        selected_table=selected_table,
        selected_month=selected_month,
        rows=rows,
        message=message
    )

@app.route('/download_page')
def download_page():
    if 'user' not in session:
        return redirect(url_for('index'))
    
    # All predefined tables
    all_tables = ['id_grind', 'od_grind', 'od_patch', 'milling', 'wasem', 'turning']

    # Build dictionary: table_name -> list of months
    table_month_dict = {}
    cursor.execute("SHOW TABLES LIKE 'submitted_%'")
    submitted_tables = [list(r.values())[0] for r in cursor.fetchall()]

    for table_name in all_tables:
        table_month_dict[table_name] = []
        for t in submitted_tables:
            # Remove 'submitted_' prefix
            if not t.startswith("submitted_"):
                continue
            table_part = t.replace("submitted_", "", 1)
            # Split from last 2 underscores
            parts = table_part.rsplit("_", 2)
            if len(parts) != 3:
                continue
            name, year, month = parts
            if name == table_name:
                table_month_dict[table_name].append(f"{year}_{month}")
    
    return render_template('download.html', table_month_dict=table_month_dict)

@app.route('/download', methods=['GET'])
def download_data():
    table = request.args.get('table')
    month = request.args.get('month')

    if not table or not month:
        return "⚠️ Table or month not selected"

    final_table = f"submitted_{table}_{month}"
    try:
        cursor.execute(f"SELECT * FROM {final_table}")
        rows = cursor.fetchall()
        if not rows:
            return "⚠️ No data to download"

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(rows[0].keys())
        for row in rows:
            writer.writerow(row.values())
        output.seek(0)

        return send_file(
            io.BytesIO(output.getvalue().encode()),
            mimetype='text/csv',
            download_name=f"{table}_{month}.csv",
            as_attachment=True
        )
    except Exception as e:
        print(e)
        return "❌ Failed to download CSV"
    
# ---------------- DELETE DATA ----------------
@app.route('/delete_data', methods=['POST'])
def delete_data():
    if 'user' not in session:
        return jsonify({'success': False, 'message': 'Not authorized'})
    
    data = request.get_json()
    table = data.get('table')
    month = data.get('month')
    record_id = data.get('id')

    if not table or not month:
        return jsonify({'success': False, 'message': 'Table and month are required'})

    final_table = f"submitted_{table}_{month}"
    
    try:
        # Check if table exists
        cursor.execute(f"SHOW TABLES LIKE '{final_table}'")
        if not cursor.fetchone():
            return jsonify({'success': False, 'message': 'No data found to delete'})
        
        if record_id:
            # Delete specific record
            cursor.execute(f"DELETE FROM {final_table} WHERE id = %s", (record_id,))
            message = "✅ Record deleted successfully!"
        else:
            # Delete entire table for that month
            cursor.execute(f"DROP TABLE {final_table}")
            message = f"✅ All data for {table} ({month}) deleted successfully!"
        
        conn.commit()
        return jsonify({'success': True, 'message': message})
    except Exception as e:
        print(e)
        return jsonify({'success': False, 'message': '❌ Failed to delete data'})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)