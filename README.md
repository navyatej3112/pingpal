# PingPal

A lightweight uptime and latency monitor with a Python collector and Streamlit dashboard. Monitor multiple endpoints concurrently, track uptime percentages, and visualize latency trends over time.

## Features

- **🔄 Concurrent Monitoring**: Non-blocking async checks for multiple endpoints with independent intervals
- **📊 Real-time Dashboard**: Streamlit interface with status tables, uptime metrics, and interactive latency charts
- **💾 SQLite Storage**: Automatic database creation with optimized indexes for efficient queries
- **📈 Historical Analysis**: View uptime percentages and latency trends over customizable time windows (1h, 6h, 24h, 7d)
- **🔍 Endpoint Filtering**: Filter dashboard data by specific endpoints
- **📥 CSV Export**: Download historical check data for analysis
- **⚙️ YAML Configuration**: Simple endpoint configuration with sensible defaults

## Quickstart

### Prerequisites

- Python 3.8 or higher
- pip

### Setup and Run

```bash
# 1. Create virtual environment
python3 -m venv venv

# 2. Activate virtual environment
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run collector (in one terminal)
python collector.py

# 5. Run dashboard (in another terminal)
streamlit run dashboard.py

# 6. Run tests
python -m pytest tests/
```

The collector creates `pingpal.db` automatically on first run. The dashboard opens at `http://localhost:8501`.

### Helper Scripts

For convenience, use the provided scripts:

```bash
# Run collector (auto-activates venv if present)
./scripts/run_collector.sh

# Run dashboard (auto-activates venv if present)
./scripts/run_dashboard.sh
```

## Configuration

Edit `endpoints.yml` to define your endpoints:

```yaml
endpoints:
  - name: GitHub API
    url: https://api.github.com
    method: GET
    interval_seconds: 60
    timeout_seconds: 5
  
  - name: HTTPBin 200
    url: https://httpbin.org/status/200
    method: GET
    interval_seconds: 30
    timeout_seconds: 5
```

Each endpoint supports:
- `name`: Display name for the endpoint (required)
- `url`: URL to monitor (required)
- `method`: HTTP method (default: `GET`)
- `interval_seconds`: Check interval in seconds (default: `60`)
- `timeout_seconds`: Request timeout in seconds (default: `5`)

## Dashboard Features

- **Current Status Table**: Latest check result for each endpoint with status code and latency
- **Uptime Percentage**: Calculated over selectable time windows (1h, 6h, 24h, 7d)
- **Latency Charts**: Interactive Plotly charts showing latency trends over time
- **Endpoint Filtering**: Filter data by specific endpoint or view all
- **CSV Export**: Download historical data as CSV for external analysis

## Screenshots

_Add screenshots or GIFs of the dashboard here_

## Database Schema

The `checks` table stores:
- `id`: Primary key
- `timestamp_utc`: ISO format UTC timestamp
- `name`: Endpoint name
- `url`: Endpoint URL
- `status_code`: HTTP status code (nullable)
- `ok`: Boolean (1 = success, 0 = failure)
- `latency_ms`: Request latency in milliseconds
- `error_type`: Error type if failed (nullable)
- `error_message`: Error message if failed (nullable)

Indexes are created on `timestamp_utc`, `name`, and `(name, timestamp_utc)` for efficient queries.

## Troubleshooting

### Streamlit Port Already in Use

If port 8501 is already in use, Streamlit will automatically try the next available port. You can also specify a custom port:

```bash
streamlit run dashboard.py --server.port 8502
```

### Database File Not Found

The database `pingpal.db` is created automatically when the collector starts. If you see "Database not found" in the dashboard:
1. Make sure the collector has been run at least once
2. Ensure both collector and dashboard are running from the same directory
3. Check that `pingpal.db` exists in the project root

### Virtual Environment Not Activated

If you see import errors, make sure your virtual environment is activated:

```bash
source venv/bin/activate  # Mac/Linux
# or
venv\Scripts\activate  # Windows
```

### Collector Not Writing Data

- Verify `endpoints.yml` exists and is valid YAML
- Check that endpoints have valid URLs
- Ensure network connectivity to the endpoints
- Check console output for error messages

## License

MIT
