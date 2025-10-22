# Data Portal - System Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                          USER BROWSER                            │
│                    (Chrome, Firefox, etc.)                       │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            │ HTTPS
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                      RENDER WEB SERVICE                          │
│                  (data-portal-xdir.onrender.com)                 │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    Gunicorn WSGI Server                     │ │
│  │                   (Port from env: 5000)                     │ │
│  └──────────────────────────┬─────────────────────────────────┘ │
│                             │                                    │
│  ┌──────────────────────────▼─────────────────────────────────┐ │
│  │                    Flask Application                        │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │ │
│  │  │   app.py     │  │  models.py   │  │   config.py     │  │ │
│  │  │  (Routes &   │  │  (Database   │  │ (DB & Env Vars) │  │ │
│  │  │   Session)   │  │   Logic)     │  │                 │  │ │
│  │  └──────────────┘  └──────────────┘  └─────────────────┘  │ │
│  │                                                             │ │
│  │  Templates: login.html, index.html, view.html, download.html│ │
│  │  Static: script.js                                         │ │
│  └─────────────────────────┬───────────────────────────────────┘ │
└────────────────────────────┼─────────────────────────────────────┘
                             │
                             │ MySQL Protocol
                             │ (SSL/TLS optional)
                             │
┌────────────────────────────▼─────────────────────────────────────┐
│                    RAILWAY MYSQL DATABASE                        │
│              interchange.proxy.rlwy.net:21193                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Database: railway                                        │   │
│  │  User: root (recommend app_user for security)            │   │
│  │                                                           │   │
│  │  Base Tables:                                             │   │
│  │    - id_grind, od_grind, od_patch                         │   │
│  │    - milling, wasem, turning                              │   │
│  │                                                           │   │
│  │  Dynamic Tables (created on submission):                  │   │
│  │    - submitted_{table}_{year}_{month}                     │   │
│  │      Example: submitted_id_grind_2025_10                  │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      GITHUB REPOSITORY                           │
│                    Abhigna41/Data_Portal                         │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  On push to main branch:                                   │ │
│  │  Render auto-deploys from GitHub                           │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

## Request Flow

### 1. Login Flow
```
User → /login (POST)
  ↓
Flask validates username/password (from env vars)
  ↓
Session cookie set
  ↓
Redirect to /portal
```

### 2. Data Submission Flow
```
User fills form → /submit (POST JSON)
  ↓
models.submit_data()
  ↓
Creates table: submitted_{table}_{year}_{month} (if not exists)
  ↓
INSERT INTO submitted table
  ↓
Response: ✅ Success
```

### 3. View Data Flow
```
User selects table/month → /view (POST)
  ↓
models.get_submitted_tables() - finds all submitted_* tables
  ↓
models.fetch_rows(submitted_{table}_{month})
  ↓
Render view.html with rows
```

### 4. Download CSV Flow
```
User selects table/month → /download (GET)
  ↓
SELECT * FROM submitted_{table}_{month}
  ↓
Generate CSV in memory (io.StringIO)
  ↓
send_file() streams CSV to browser
  ↓
Browser downloads: {table}_{month}.csv
```

## Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| **Frontend** | HTML5, CSS3, JavaScript | - |
| **UI Framework** | Custom CSS (no external framework) | - |
| **Icons** | Font Awesome | 6.4.0 |
| **Backend** | Flask | 3.1.2 |
| **WSGI Server** | Gunicorn | 21.2.0 |
| **Database** | MySQL | 8.0 (Railway) |
| **DB Driver** | mysql-connector-python | 9.4.0 |
| **Environment** | Python | 3.13 |
| **Config** | python-dotenv | 1.0.0 |
| **Hosting** | Render | Free tier |
| **Database Host** | Railway | Free tier |
| **Version Control** | GitHub | - |

## Security Architecture

### Authentication
- Session-based authentication (Flask sessions)
- Admin credentials from environment variables
- Session secret key: FLASK_SECRET_KEY

### Database Security
- Connection pooling (pool_size: 5)
- Connection timeout: 10s
- consume_results: True (prevents cursor errors)
- Optional TLS/SSL support:
  - MYSQL_REQUIRE_SSL=true
  - MYSQL_SSL_CA for certificate verification

### Recommended Security Measures
```
1. Use dedicated DB user (app_user) instead of root
2. Rotate credentials when exposed
3. Enable TLS for DB connections
4. Keep .env out of git (.gitignore)
5. Use strong FLASK_SECRET_KEY
```

## Environment Variables

### Local Development (.env)
```
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=****
MYSQL_DB=data_portal

FLASK_SECRET_KEY=****
ADMIN_USERNAME=****
ADMIN_PASSWORD=****
```

### Production (Render)
```
MYSQL_HOST=interchange.proxy.rlwy.net
MYSQL_PORT=21193
MYSQL_USER=app_user
MYSQL_PASSWORD=****
MYSQL_DB=railway

MYSQL_REQUIRE_SSL=true

FLASK_SECRET_KEY=****
ADMIN_USERNAME=****
ADMIN_PASSWORD=****
```

## Deployment Architecture

```
Developer pushes to GitHub (main branch)
         ↓
Render detects commit
         ↓
Render builds:
  - pip install -r requirements.txt
  - Start: gunicorn app:app
         ↓
Health check: /health endpoint
         ↓
Live at: https://data-portal-xdir.onrender.com
```

### Auto-deploy on push
- No manual deployment needed
- GitHub webhooks trigger Render build
- Build time: ~1-2 minutes

### Cold Start (Free Tier)
- Service spins down after 15 min inactivity
- First request after idle: 30-60s delay
- Subsequent requests: normal speed

## File Structure

```
Application/
├── app.py                    # Main Flask app, routes
├── models.py                 # Database functions
├── config.py                 # Environment & DB config
├── requirements.txt          # Python dependencies
├── Procfile                  # Gunicorn start command
├── .env                      # Local environment (gitignored)
├── .gitignore               # Git ignore rules
├── README.md                # Project documentation
├── ARCHITECTURE.md          # This file
├── templates/
│   ├── login.html           # Login page
│   ├── index.html           # Portal dashboard
│   ├── view.html            # View submitted data
│   ├── download.html        # Download CSV page
│   └── macros.html          # Jinja macros
├── static/
│   └── script.js            # Client-side interactions
├── db/
│   └── app_user.sql         # SQL to create least-privilege user
└── ops/
    └── render-env-example.txt  # Example Render env vars
```

## Database Schema

### Base Tables (6 tables)
```sql
CREATE TABLE id_grind (
  id INT AUTO_INCREMENT PRIMARY KEY,
  item VARCHAR(255),
  code VARCHAR(255),
  rate DECIMAL(10,2)
);
-- Similar structure for: od_grind, od_patch, milling, wasem, turning
```

### Dynamic Submitted Tables
Created automatically when user submits data:
```sql
CREATE TABLE submitted_id_grind_2025_10 (
  id INT AUTO_INCREMENT PRIMARY KEY,
  date DATE,
  item VARCHAR(255),
  code VARCHAR(255),
  rate DECIMAL(10,2),
  quantity INT,
  total DECIMAL(10,2),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## API Endpoints

| Route | Method | Auth Required | Description |
|-------|--------|---------------|-------------|
| `/` | GET | No | Login page |
| `/login` | POST | No | Authenticate user |
| `/portal` | GET | Yes | Dashboard |
| `/get_items` | GET | No | Fetch items for a table |
| `/submit` | POST | No | Submit new data |
| `/view` | GET, POST | No | View submitted data |
| `/download_page` | GET | Yes | Download selection page |
| `/download` | GET | No | Stream CSV file |
| `/delete_data` | POST | Yes | Delete records |
| `/health` | GET | No | Health check (DB status) |
| `/debug/routes` | GET | Yes | List all routes |

## Performance Considerations

### Connection Pooling
- Pool size: 5 connections
- Reuses connections across requests
- Reduces connection overhead

### Timeouts
- Connection timeout: 10s
- Prevents hanging on DB issues

### CSV Streaming
- Uses io.StringIO for in-memory CSV generation
- No disk I/O required
- Efficient for large datasets

### Free Tier Limitations
- Render: 750 hours/month, spins down after idle
- Railway: 500 hours/month DB uptime
- Cold starts add latency

## Monitoring & Health

### Health Endpoint
```bash
GET /health
Response: {"ok": true, "db": "ok"}
```

### Common Issues
1. "Bad Gateway" → Render service down or deploying
2. "Worker timeout" → Cold start (wait 30-60s)
3. "Unread result found" → Fixed with consume_results=True
4. "Connection refused" → Railway DB down or credentials wrong

## Future Enhancements (Optional)

- [ ] User roles and permissions
- [ ] Email notifications on data submission
- [ ] Data validation rules
- [ ] Audit logging
- [ ] Export to Excel/PDF
- [ ] Charts and analytics dashboard
- [ ] API key authentication for programmatic access
- [ ] WebSocket for real-time updates

---

**Last Updated:** October 22, 2025  
**Version:** 2.1  
**Maintained by:** Data Portal Team
