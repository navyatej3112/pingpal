#!/usr/bin/env python3
"""
PingPal Collector - Monitors endpoints and records results to SQLite.
"""

import asyncio
import sqlite3
import time
import yaml
import sys
from datetime import datetime, timezone
from typing import Dict, List, Optional
import aiohttp
from pathlib import Path


DB_PATH = "pingpal.db"
CONFIG_PATH = "endpoints.yml"


def init_database():
    """Initialize SQLite database with schema and indexes."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp_utc TEXT NOT NULL,
            name TEXT NOT NULL,
            url TEXT NOT NULL,
            status_code INTEGER,
            ok INTEGER NOT NULL,
            latency_ms REAL NOT NULL,
            error_type TEXT,
            error_message TEXT
        )
    """)
    
    # Create indexes for efficient queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON checks(timestamp_utc)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_name ON checks(name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_name_timestamp ON checks(name, timestamp_utc)")
    
    conn.commit()
    conn.close()


def load_config() -> List[Dict]:
    """Load and validate endpoint configuration from YAML."""
    try:
        with open(CONFIG_PATH, 'r') as f:
            config = yaml.safe_load(f)
        
        if not config or 'endpoints' not in config:
            raise ValueError("Config must contain 'endpoints' key")
        
        endpoints = []
        for ep in config['endpoints']:
            if 'name' not in ep or 'url' not in ep:
                raise ValueError("Each endpoint must have 'name' and 'url'")
            
            endpoint = {
                'name': ep['name'],
                'url': ep['url'],
                'method': ep.get('method', 'GET'),
                'interval_seconds': ep.get('interval_seconds', 60),
                'timeout_seconds': ep.get('timeout_seconds', 5)
            }
            endpoints.append(endpoint)
        
        return endpoints
    except FileNotFoundError:
        print(f"Error: {CONFIG_PATH} not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error loading config: {e}")
        sys.exit(1)


def save_check(result: Dict):
    """Save check result to database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO checks 
        (timestamp_utc, name, url, status_code, ok, latency_ms, error_type, error_message)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        result['timestamp_utc'],
        result['name'],
        result['url'],
        result['status_code'],
        result['ok'],
        result['latency_ms'],
        result['error_type'],
        result['error_message']
    ))
    
    conn.commit()
    conn.close()


async def check_endpoint(session: aiohttp.ClientSession, endpoint: Dict) -> Dict:
    """Perform a single endpoint check."""
    start_time = time.time()
    timestamp_utc = datetime.now(timezone.utc).isoformat()
    
    result = {
        'timestamp_utc': timestamp_utc,
        'name': endpoint['name'],
        'url': endpoint['url'],
        'status_code': None,
        'ok': False,
        'latency_ms': 0.0,
        'error_type': None,
        'error_message': None
    }
    
    try:
        timeout = aiohttp.ClientTimeout(total=endpoint['timeout_seconds'])
        method = endpoint['method'].upper()
        
        async with session.request(method, endpoint['url'], timeout=timeout) as response:
            result['status_code'] = response.status
            result['ok'] = 200 <= response.status < 400
            result['latency_ms'] = (time.time() - start_time) * 1000
            
    except asyncio.TimeoutError:
        result['error_type'] = 'Timeout'
        result['error_message'] = f"Request timed out after {endpoint['timeout_seconds']}s"
        result['latency_ms'] = endpoint['timeout_seconds'] * 1000
    except aiohttp.ClientError as e:
        result['error_type'] = 'ClientError'
        result['error_message'] = str(e)
        result['latency_ms'] = (time.time() - start_time) * 1000
    except Exception as e:
        result['error_type'] = type(e).__name__
        result['error_message'] = str(e)
        result['latency_ms'] = (time.time() - start_time) * 1000
    
    return result


async def monitor_endpoint(session: aiohttp.ClientSession, endpoint: Dict):
    """Monitor a single endpoint at its specified interval."""
    interval = endpoint['interval_seconds']
    
    while True:
        result = await check_endpoint(session, endpoint)
        save_check(result)
        
        # Compact console log
        status = f"✓ {result['status_code']}" if result['ok'] else f"✗ {result['error_type'] or result['status_code']}"
        print(f"{result['timestamp_utc'][:19]} | {result['name']:20} | {status:15} | {result['latency_ms']:6.1f}ms")
        
        await asyncio.sleep(interval)


async def main():
    """Main collector loop."""
    endpoints = load_config()
    
    if not endpoints:
        print("No endpoints configured")
        return
    
    init_database()
    
    print(f"PingPal Collector started - monitoring {len(endpoints)} endpoint(s)")
    print("Press Ctrl+C to stop\n")
    
    async with aiohttp.ClientSession() as session:
        tasks = [monitor_endpoint(session, ep) for ep in endpoints]
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            print("\n\nShutting down...")


if __name__ == "__main__":
    asyncio.run(main())

