# Credential Manager

A secure and efficient credential management system built with FastAPI. This application helps you organize, track, and manage credentials for multiple systems and domains.

## Features

- 📁 **Credential Processing**: Automatically parse credential files in `url:user:password` format
- 🌐 **Domain Organization**: Group credentials by domain for better organization
- ✅ **Status Checking**: Real-time domain availability checking (online/offline)
- 🔍 **Advanced Filtering**: Filter by status (online/offline/all) and accessed credentials
- 📊 **Statistics Dashboard**: View comprehensive statistics about your credentials
- 📄 **Pagination**: Efficient pagination for large credential databases
- 🔐 **Security Features**: 
  - Password masking by default
  - One-click copy functionality
  - Access tracking for credentials
- 🎨 **Modern UI**: Beautiful, responsive interface with smooth animations

## Installation

1. **Clone or navigate to the project directory:**
   ```bash
   cd creds_manage
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   python main.py
   ```
   Or using uvicorn directly:
   ```bash
   uvicorn main:app --reload
   ```

4. **Access the application:**
   - Main page: http://localhost:8000
   - Management page: http://localhost:8000/manage

## Usage

### 1. Prepare Credential Files

Place your credential files in the `creds/` folder. Each file should contain credentials in the following format:

```
url:username:password
```

Example:
```
https://example.com/login:admin:password123
https://example.com/admin:root:securepass
```

### 2. Process Files

1. Navigate to the **Management** page
2. Click the **Process Files** button
3. The system will:
   - Parse all `.txt` files in the `creds/` folder
   - Extract domains and credentials
   - Store them in the database
   - Move processed files to `processed_creds/` folder

### 3. View Credentials

1. On the main page, you'll see domains grouped together
2. Click on a domain card to expand and view its credentials
3. Each credential shows:
   - URL (clickable, opens in new tab)
   - Username (with copy button)
   - Password (masked, with copy/show toggle)
   - Admin status
   - Access checkbox

### 4. Check Domain Status

- Domains are automatically checked for availability
- Status badges show: ONLINE, OFFLINE, or UNKNOWN
- Click "Update Working Status" to save current statuses to database

### 5. Filtering Options

- **Status Filter**: Filter by All, Online, or Offline domains
- **Accessed Filter**: Show only credentials that have been accessed
- Default view shows only online domains

## Project Structure

```
creds_manage/
├── main.py              # FastAPI application and routes
├── database.py          # Database configuration
├── models.py            # SQLAlchemy models
├── schemas.py           # Pydantic schemas
├── requirements.txt     # Python dependencies
├── credentials.db       # SQLite database (created automatically)
├── creds/              # Input folder for credential files
├── processed_creds/    # Processed files are moved here
├── templates/          # HTML templates
│   ├── index.html      # Main credentials page
│   └── manage.html     # Management dashboard
└── static/             # Static files (CSS, JS, images)
```

## Database Schema

### Domain Table
- `id`: Primary key
- `domain`: Domain name (unique)
- `is_working`: Boolean (True=online, False=offline, None=unknown)
- `is_important`: Boolean flag for important domains

### Credential Table
- `id`: Primary key
- `domain_id`: Foreign key to Domain
- `url`: Full URL
- `user`: Username
- `password`: Password
- `is_accessed`: Boolean (track if credential has been used)
- `is_admin`: Boolean (auto-detected if URL/username contains 'admin')

## API Endpoints

- `GET /`: Main credentials page
- `GET /manage`: Management dashboard
- `POST /api/process`: Process credential files
- `POST /api/update-working-status`: Update domain working status
- `POST /api/credential/{id}/toggle-accessed`: Toggle credential accessed status
- `GET /api/stats`: Get database statistics

## Features Details

### Domain Status Checking

The system uses a cross-origin compatible method to check if domains are online:
- Attempts to load favicon.ico from the domain
- Tries HTTPS first, then HTTP
- 8-second timeout per domain
- Concurrent checking (max 5 at a time)

### Credential Processing

- Automatically extracts domain from URLs
- Handles various URL formats (with/without protocol, paths, etc.)
- Detects admin credentials automatically
- Prevents duplicates (same URL + username)
- Moves processed files to avoid reprocessing

### Security Considerations

- Passwords are masked by default
- Copy functionality uses browser clipboard API
- Database stores credentials locally (SQLite)
- No external API calls with sensitive data

## Troubleshooting

### Domain Status Shows "UNKNOWN"
- The domain checking relies on favicon availability
- Some domains may not serve favicons, causing false negatives
- You can manually update status using the "Update Working Status" button

### Files Not Processing
- Ensure files are in `.txt` format
- Check file encoding (UTF-8 recommended)
- Verify format is `url:user:password` (splitting from right)
- Check console/terminal for error messages

### Database Issues
- Delete `credentials.db` to reset the database
- Ensure write permissions in the project directory

## Future Enhancements

- Export credentials functionality
- Search and advanced filtering
- Credential encryption at rest
- Import from password managers
- Domain importance marking
- Credential expiration tracking

## License

This project is provided as-is for credential management purposes.


uvicorn main:app --reload --host 0.0.0.0 --port 8000
