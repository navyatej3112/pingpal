"""Tests for database operations."""

import pytest
import sqlite3
import tempfile
import os
from pathlib import Path
import sys
from datetime import datetime, timezone

# Add parent directory to path to import collector
sys.path.insert(0, str(Path(__file__).parent.parent))

from collector import init_database, save_check


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(db_fd)
    
    # Temporarily replace DB_PATH
    import collector
    original_path = collector.DB_PATH
    collector.DB_PATH = db_path
    
    init_database()
    
    yield db_path
    
    # Cleanup
    collector.DB_PATH = original_path
    if os.path.exists(db_path):
        os.unlink(db_path)


def test_init_database(temp_db):
    """Test database initialization creates correct schema."""
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    
    # Check table exists
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='checks'
    """)
    assert cursor.fetchone() is not None
    
    # Check columns
    cursor.execute("PRAGMA table_info(checks)")
    columns = {row[1]: row[2] for row in cursor.fetchall()}
    
    assert 'id' in columns
    assert 'timestamp_utc' in columns
    assert 'name' in columns
    assert 'url' in columns
    assert 'status_code' in columns
    assert 'ok' in columns
    assert 'latency_ms' in columns
    assert 'error_type' in columns
    assert 'error_message' in columns
    
    # Check indexes exist
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='index' AND name LIKE 'idx_%'
    """)
    indexes = [row[0] for row in cursor.fetchall()]
    
    assert 'idx_timestamp' in indexes
    assert 'idx_name' in indexes
    assert 'idx_name_timestamp' in indexes
    
    conn.close()


def test_save_check_success(temp_db):
    """Test saving a successful check."""
    result = {
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'name': 'Test Endpoint',
        'url': 'https://example.com',
        'status_code': 200,
        'ok': True,
        'latency_ms': 123.45,
        'error_type': None,
        'error_message': None
    }
    
    save_check(result)
    
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM checks WHERE name = ?", ('Test Endpoint',))
    row = cursor.fetchone()
    conn.close()
    
    assert row is not None
    assert row[2] == 'Test Endpoint'
    assert row[3] == 'https://example.com'
    assert row[4] == 200
    assert row[5] == 1  # ok = True
    assert row[6] == 123.45


def test_save_check_failure(temp_db):
    """Test saving a failed check."""
    result = {
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'name': 'Failed Endpoint',
        'url': 'https://example.com',
        'status_code': None,
        'ok': False,
        'latency_ms': 5000.0,
        'error_type': 'Timeout',
        'error_message': 'Request timed out'
    }
    
    save_check(result)
    
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM checks WHERE name = ?", ('Failed Endpoint',))
    row = cursor.fetchone()
    conn.close()
    
    assert row is not None
    assert row[4] is None  # status_code
    assert row[5] == 0  # ok = False
    assert row[7] == 'Timeout'
    assert row[8] == 'Request timed out'


def test_get_latest_status(temp_db):
    """Test querying latest status for each endpoint."""
    # Insert multiple checks for same endpoint
    results = [
        {
            'timestamp_utc': '2024-01-01T10:00:00+00:00',
            'name': 'Endpoint A',
            'url': 'https://example.com/a',
            'status_code': 200,
            'ok': True,
            'latency_ms': 100.0,
            'error_type': None,
            'error_message': None
        },
        {
            'timestamp_utc': '2024-01-01T11:00:00+00:00',
            'name': 'Endpoint A',
            'url': 'https://example.com/a',
            'status_code': 200,
            'ok': True,
            'latency_ms': 150.0,
            'error_type': None,
            'error_message': None
        },
        {
            'timestamp_utc': '2024-01-01T10:30:00+00:00',
            'name': 'Endpoint B',
            'url': 'https://example.com/b',
            'status_code': 404,
            'ok': False,
            'latency_ms': 200.0,
            'error_type': None,
            'error_message': None
        }
    ]
    
    for result in results:
        save_check(result)
    
    # Query latest status (similar to dashboard query)
    conn = sqlite3.connect(temp_db)
    query = """
        SELECT 
            name,
            url,
            timestamp_utc,
            status_code,
            ok,
            latency_ms
        FROM checks
        WHERE (name, timestamp_utc) IN (
            SELECT name, MAX(timestamp_utc)
            FROM checks
            GROUP BY name
        )
        ORDER BY name
    """
    cursor = conn.cursor()
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    
    assert len(rows) == 2
    
    # Endpoint A should have the latest check (11:00)
    endpoint_a = [r for r in rows if r[0] == 'Endpoint A'][0]
    assert endpoint_a[2] == '2024-01-01T11:00:00+00:00'
    assert endpoint_a[5] == 150.0
    
    # Endpoint B should have its only check
    endpoint_b = [r for r in rows if r[0] == 'Endpoint B'][0]
    assert endpoint_b[2] == '2024-01-01T10:30:00+00:00'
    assert endpoint_b[3] == 404

