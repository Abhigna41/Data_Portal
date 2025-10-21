import mysql.connector
from config import DB_CONFIG
from datetime import datetime

# Connect to DB
def get_connection():
    conn = mysql.connector.connect(**DB_CONFIG)
    return conn

# Fetch tables list
def get_tables_list():
    return ['id_grind','od_grind','od_patch','milling','wasem','turning']

# Fetch items for dropdown
def fetch_items(cursor, table):
    if table.lower() == 'wasem':
        cursor.execute(f"SELECT DISTINCT Item, Code, G_Rate, H_Rate FROM {table} WHERE Item IS NOT NULL")
    else:
        cursor.execute(f"SELECT DISTINCT Item, Code, Rate FROM {table} WHERE Item IS NOT NULL")
    return cursor.fetchall()

# Insert submitted data
def submit_data(cursor, conn, table_name, date_str, item, code, rate, quantity, total):
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    table_month = f"{date_obj.year}_{date_obj.month:02d}"
    final_table = f"submitted_{table_name}_{table_month}"

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

# Get submitted tables and months
def get_submitted_tables(cursor, all_tables):
    cursor.execute("SHOW TABLES LIKE 'submitted_%'")
    submitted_tables = [list(r.values())[0] for r in cursor.fetchall()]
    table_month_dict = {}
    for table_name in all_tables:
        table_month_dict[table_name] = []
        for t in submitted_tables:
            if not t.startswith("submitted_"): continue
            table_part = t.replace("submitted_", "", 1)
            parts = table_part.rsplit("_", 2)
            if len(parts) != 3: continue
            name, year, month = parts
            if name == table_name:
                table_month_dict[table_name].append(f"{year}_{month}")
    return table_month_dict

# Fetch data for view/download
def fetch_rows(cursor, final_table):
    cursor.execute(f"SELECT * FROM {final_table} ORDER BY id DESC")
    return cursor.fetchall()

# Delete record or table
def delete_data(cursor, conn, final_table, record_id=None):
    cursor.execute(f"SHOW TABLES LIKE '{final_table}'")
    if not cursor.fetchone():
        return False
    if record_id:
        cursor.execute(f"DELETE FROM {final_table} WHERE id = %s", (record_id,))
    else:
        cursor.execute(f"DROP TABLE {final_table}")
    conn.commit()
    return True
