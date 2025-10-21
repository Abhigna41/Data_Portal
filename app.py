from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, session
import io
import csv
from models import *
from config import SECRET_KEY, ADMIN_USERNAME, ADMIN_PASSWORD

import firebase_admin
from firebase_admin import credentials, storage
from google.cloud import storage as gcs_storage
from datetime import timedelta
import os

from dotenv import load_dotenv
from datetime import datetime
from firebase_utils import upload_bytes, download_bytes
 

# Load the path from environment variable (recommended)
FIREBASE_KEY_PATH = os.getenv("FIREBASE_KEY_PATH", "firebase-key.json")
# Set the Firebase bucket name directly since we know the project ID
FIREBASE_BUCKET = "dataportal-6d718.appspot.com"

# Initialize Firebase admin with the service account and configure the bucket
cred = credentials.Certificate(FIREBASE_KEY_PATH)
firebase_admin.initialize_app(cred, {
    'storageBucket': FIREBASE_BUCKET
})

# Final initialization of a firebase-admin storage bucket object. If the bucket cannot
# be configured here, operations that use it will raise and we will show clearer errors.
try:
    if FIREBASE_BUCKET:
        bucket = storage.bucket(FIREBASE_BUCKET)
    else:
        # Fall back to default bucket configured in the app (if any)
        bucket = storage.bucket()
except Exception as e:
    # Keep `bucket` name unset so routes can report clearer errors
    print('Failed to initialize Firebase bucket:', e)
    bucket = None
#--------------------------------------------------------------------------


app = Flask(__name__)
app.secret_key = SECRET_KEY

def upload_csv_to_firebase(file_name, file_content):
    # Upload CSV to Firebase Storage but keep the file private.
    # We return the storage path (blob.name) so the app can reference it,
    # but we do NOT make it public.
    blob = bucket.blob(file_name)
    blob.upload_from_string(file_content, content_type='text/csv')
    return blob.name


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
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        data = fetch_items(cursor, table)
        return jsonify(data)
    finally:
        cursor.close()
        conn.close()

@app.route('/submit', methods=['POST'])
def submit():
    data = request.get_json()
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Insert into local DB
        submit_data(cursor, conn, data['table'], data['date'], data['item'], data['code'], data['rate'], data['quantity'], data['total'])

        # Also upload the current table/month CSV to Firebase so submitted data is stored there
        try:
            # derive table_month and final_table same way models.submit_data does
            date_obj = datetime.strptime(data['date'], "%Y-%m-%d")
            table_month = f"{date_obj.year}_{date_obj.month:02d}"
            final_table = f"submitted_{data['table']}_{table_month}"

            # fetch all rows for this submitted table and build CSV
            temp_cursor = conn.cursor(dictionary=True)
            temp_cursor.execute(f"SELECT * FROM {final_table} ORDER BY id DESC")
            rows = temp_cursor.fetchall()
            temp_cursor.close()

            if rows:
                out = io.StringIO()
                writer = csv.writer(out)
                writer.writerow(rows[0].keys())
                for r in rows:
                    writer.writerow(r.values())
                out.seek(0)

                # store under a folder path so files are organized in the bucket
                storage_path = f"submitted/{final_table}.csv"
                try:
                    upload_csv_to_firebase(storage_path, out.getvalue())
                except Exception as fb_e:
                    # Log Firebase upload failure but don't fail the whole submission
                    print('Firebase upload error:', fb_e)

        except Exception as e_inner:
            # non-fatal: log and continue
            print('Error preparing Firebase CSV:', e_inner)

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

@app.route('/firebase-upload', methods=['POST'])
def firebase_upload():
    # Simple endpoint to upload a file (form field 'file') to firebase storage
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    f = request.files['file']
    filename = f.filename or f"upload_{int(datetime.utcnow().timestamp())}"
    data = f.read()
    try:
        public_url = upload_bytes(f"uploads/{filename}", data, content_type=f.content_type)
        return jsonify({'message': 'uploaded', 'url': public_url})
    except Exception as e:
        print('Upload error:', e)
        return jsonify({'error': 'Upload failed'}), 500

@app.route('/firebase-download')
def firebase_download():
    # Provide a `path` query param that matches the object path in the bucket
    path = request.args.get('path')
    if not path:
        return jsonify({'error': 'path query param required'}), 400
    try:
        data = download_bytes(path)
        return send_file(io.BytesIO(data), download_name=os.path.basename(path), as_attachment=True)
    except Exception as e:
        print('Download error:', e)
        return jsonify({'error': 'Download failed'}), 500



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


# --- FIREBASE BROWSE / DOWNLOAD ---
@app.route('/firebase_files')
def firebase_files():
    # list CSV files in the configured Firebase storage bucket
    if 'user' not in session:
        return redirect(url_for('index'))
    try:
        if not bucket:
            raise RuntimeError('Firebase bucket not configured. Check FIREBASE_KEY_PATH and FIREBASE_STORAGE_BUCKET.')
        blobs = bucket.list_blobs()
        csv_files = [b.name for b in blobs if b.name.lower().endswith('.csv')]
        return render_template('firebase_files.html', files=csv_files)
    except Exception as e:
        # Print full traceback server-side, and return the exception message in the response
        import traceback
        traceback.print_exc()
        return f"❌ Failed to list Firebase files: {str(e)}"


@app.route('/firebase_download_legacy')
def firebase_download_legacy():
    # stream a file from Firebase storage to the client
    if 'user' not in session:
        return redirect(url_for('index'))
    name = request.args.get('name')
    if not name:
        return "⚠️ File name not provided"
    try:
        blob = bucket.blob(name)
        data = blob.download_as_bytes()
        mem = io.BytesIO(data)
        mem.seek(0)
        # return as attachment so browser opens or downloads the CSV
        try:
            return send_file(mem, mimetype='text/csv', as_attachment=True, download_name=name)
        except TypeError:
            return send_file(mem, mimetype='text/csv', as_attachment=True, attachment_filename=name)
    except Exception as e:
        print('Error downloading Firebase file:', e)
        return "❌ Failed to download file from Firebase"


@app.route('/firebase_signed_url')
def firebase_signed_url():
    # Generate a signed URL for an object for direct download.
    if 'user' not in session:
        return jsonify({'success': False, 'message': 'Not authorized'}), 401
    name = request.args.get('name')
    expiry_min = int(request.args.get('expiry', 15))
    if not name:
        return jsonify({'success': False, 'message': 'File name required'}), 400

    try:
        # Use google-cloud-storage client (not firebase_admin) to generate signed URL
        client = gcs_storage.Client.from_service_account_json(FIREBASE_KEY_PATH)
        bucket_obj = client.bucket(FIREBASE_BUCKET)
        blob = bucket_obj.blob(name)

        url = blob.generate_signed_url(version='v4', expiration=timedelta(minutes=expiry_min), method='GET')
        return jsonify({'success': True, 'url': url})
    except Exception as e:
        print('Error generating signed URL:', e)
        return jsonify({'success': False, 'message': 'Failed to generate signed URL'}), 500


# Debug route: list buckets accessible by the service account and show the resolved FIREBASE_BUCKET.
@app.route('/debug/firebase_buckets')
def debug_firebase_buckets():
    if 'user' not in session:
        return redirect(url_for('index'))
    try:
        client = gcs_storage.Client.from_service_account_json(FIREBASE_KEY_PATH)
        buckets = [b.name for b in client.list_buckets()]
        return jsonify({'resolved_bucket_env': FIREBASE_BUCKET, 'available_buckets': buckets})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'resolved_bucket_env': FIREBASE_BUCKET}), 500


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