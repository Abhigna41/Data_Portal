from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, session
import io
import csv
from models import *
from config import SECRET_KEY, ADMIN_USERNAME, ADMIN_PASSWORD
import os
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()


app = Flask(__name__)
app.secret_key = SECRET_KEY

# --- LOGIN & PORTAL ---
@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        session['user'] = username
        return redirect(url_for('portal'))
    return render_template('login.html', error="Invalid username or password")

@app.route('/portal')
def portal():
    if 'user' not in session:
        return redirect(url_for('index'))
    return render_template('index.html', tables=get_tables_list())



# --- DATA ENDPOINTS ---
@app.route('/get_items')
def get_items():
    table = request.args.get('table')
    if table not in get_tables_list():
        return jsonify([])
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        data = fetch_items(cursor, table)
        cursor.close()
        conn.close()
        return jsonify(data)
    except Exception as e:
        print(f"Error fetching items from {table}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/submit', methods=['POST'])
def submit():
    data = request.get_json()
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Insert into local DB
        submit_data(cursor, conn, data['table'], data['date'], data['item'], data['code'], data['rate'], data['quantity'], data['total'])
        return "✅ Data submitted successfully!"
    except Exception as e:
        print(e)
        return "❌ Failed to submit data."
    finally:
        cursor.close()
        conn.close()

# --- VIEW & DOWNLOAD ---
@app.route('/view', methods=['GET','POST'])
def view_data():
    all_tables = get_tables_list()
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    table_month_dict = get_submitted_tables(cursor, all_tables)
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
                rows = fetch_rows(cursor, final_table)
                if not rows:
                    message = "⚠️ No data found for selected table/month."
            except:
                message = "⚠️ No data found for selected table/month."
    cursor.close()
    conn.close()
    return render_template('view.html', table_month_dict=table_month_dict, selected_table=selected_table, selected_month=selected_month, rows=rows, message=message)

@app.route('/download_page')
def download_page():
    if 'user' not in session:
        return redirect(url_for('index'))

    # Create a new connection and cursor
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    all_tables = ['id_grind', 'od_grind', 'od_patch', 'milling', 'wasem', 'turning']

    table_month_dict = {}
    cursor.execute("SHOW TABLES LIKE 'submitted_%'")
    submitted_tables = [row['Tables_in_data_portal (submitted_%)'] for row in cursor.fetchall()]

    for table_name in all_tables:
        table_month_dict[table_name] = []
        for t in submitted_tables:
            if not t.startswith("submitted_"):
                continue
            table_part = t.replace("submitted_", "", 1)
            parts = table_part.rsplit("_", 2)
            if len(parts) != 3:
                continue
            name, year, month = parts
            if name == table_name:
                table_month_dict[table_name].append(f"{year}_{month}")

    cursor.close()
    conn.close()

    return render_template('download.html', table_month_dict=table_month_dict)

@app.route('/download', methods=['GET'])
def download_data():
    table = request.args.get('table')
    month = request.args.get('month')

    if not table or not month:
        return "⚠️ Table or month not selected"

    final_table = f"submitted_{table}_{month}"
    # open a fresh DB connection for this request
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(f"SELECT * FROM {final_table}")
        rows = cursor.fetchall()
        if not rows:
            return "⚠️ No data to download"

        # Generate CSV content
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(rows[0].keys())
        for row in rows:
            writer.writerow(row.values())
        output.seek(0)

        # Return the CSV directly to the client as an attachment
        mem = io.BytesIO()
        mem.write(output.getvalue().encode('utf-8'))
        mem.seek(0)
        filename = f"{table}_{month}.csv"
        # Flask >=2.0 uses download_name; older versions use attachment_filename
        try:
            return send_file(mem, mimetype='text/csv', as_attachment=True, download_name=filename)
        except TypeError:
            return send_file(mem, mimetype='text/csv', as_attachment=True, attachment_filename=filename)

    except Exception as e:
        print(e)
        return "❌ Failed to download CSV"
    finally:
        try:
            cursor.close()
        except:
            pass
        try:
            conn.close()
        except:
            pass


# List all registered routes to help diagnose 404s
@app.route('/debug/routes')
def debug_routes():
    if 'user' not in session:
        return redirect(url_for('index'))
    try:
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append({
                'rule': str(rule),
                'endpoint': rule.endpoint,
                'methods': sorted(list(rule.methods - {'HEAD', 'OPTIONS'}))
            })
        # Sort for readability
        routes.sort(key=lambda r: r['rule'])
        return jsonify({'routes': routes})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# Lightweight health check for deployment and DB connectivity
@app.route('/health')
def health():
    try:
        # DB check
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        return jsonify({'ok': True, 'db': 'ok'})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


# --- DELETE DATA ---
@app.route('/delete_data', methods=['POST'])
def delete_data_route():
    if 'user' not in session:
        return jsonify({'success': False, 'message': 'Not authorized'})
    data = request.get_json()
    table = data.get('table')
    month = data.get('month')
    record_id = data.get('id')
    if not table or not month:
        return jsonify({'success': False, 'message': 'Table and month are required'})
    final_table = f"submitted_{table}_{month}"
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        success = delete_data(cursor, conn, final_table, record_id)
        if not success:
            return jsonify({'success': False, 'message': 'No data found to delete'})
        message = "✅ Record/table deleted successfully!" if record_id else f"✅ All data for {table} ({month}) deleted successfully!"
        return jsonify({'success': True, 'message': message})
    except Exception as e:
        print(e)
        return jsonify({'success': False, 'message': '❌ Failed to delete data'})
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)