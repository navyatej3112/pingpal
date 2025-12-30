#!/usr/bin/env python3
"""
PingPal Dashboard - Streamlit dashboard for monitoring endpoint status.
"""

import sqlite3
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional


DB_PATH = "pingpal.db"


def get_db_connection():
    """Get database connection."""
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def get_latest_status():
    """Get latest check result for each endpoint."""
    conn = get_db_connection()
    
    query = """
        SELECT 
            name,
            url,
            timestamp_utc,
            status_code,
            ok,
            latency_ms,
            error_type,
            error_message
        FROM checks
        WHERE (name, timestamp_utc) IN (
            SELECT name, MAX(timestamp_utc)
            FROM checks
            GROUP BY name
        )
        ORDER BY name
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


def get_checks_for_window(name: Optional[str], hours: int):
    """Get checks within the specified time window."""
    conn = get_db_connection()
    
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    
    if name:
        query = """
            SELECT 
                timestamp_utc,
                name,
                url,
                status_code,
                ok,
                latency_ms,
                error_type,
                error_message
            FROM checks
            WHERE name = ? AND timestamp_utc >= ?
            ORDER BY timestamp_utc
        """
        df = pd.read_sql_query(query, conn, params=(name, cutoff))
    else:
        query = """
            SELECT 
                timestamp_utc,
                name,
                url,
                status_code,
                ok,
                latency_ms,
                error_type,
                error_message
            FROM checks
            WHERE timestamp_utc >= ?
            ORDER BY timestamp_utc
        """
        df = pd.read_sql_query(query, conn, params=(cutoff,))
    
    conn.close()
    return df


def calculate_uptime(df: pd.DataFrame) -> float:
    """Calculate uptime percentage from dataframe."""
    if df.empty:
        return 0.0
    
    total_checks = len(df)
    successful_checks = len(df[df['ok'] == 1])
    
    return (successful_checks / total_checks * 100) if total_checks > 0 else 0.0


def main():
    st.set_page_config(page_title="PingPal Dashboard", layout="wide")
    st.title("PingPal - Uptime & Latency Monitor")
    
    # Check if database exists
    if not Path(DB_PATH).exists():
        st.error(f"Database {DB_PATH} not found. Please run the collector first.")
        return
    
    # Sidebar filters
    st.sidebar.header("Filters")
    
    # Get unique endpoint names
    conn = get_db_connection()
    names_df = pd.read_sql_query("SELECT DISTINCT name FROM checks ORDER BY name", conn)
    conn.close()
    
    endpoint_names = ["All"] + names_df['name'].tolist()
    selected_endpoint = st.sidebar.selectbox("Endpoint", endpoint_names)
    
    time_windows = {
        "Last 1 hour": 1,
        "Last 6 hours": 6,
        "Last 24 hours": 24,
        "Last 7 days": 168
    }
    selected_window = st.sidebar.selectbox("Time Window", list(time_windows.keys()))
    window_hours = time_windows[selected_window]
    
    # Current Status Table
    st.header("Current Status")
    latest_df = get_latest_status()
    
    if not latest_df.empty:
        # Format the status table
        status_df = latest_df[['name', 'url', 'timestamp_utc', 'status_code', 'ok', 'latency_ms']].copy()
        status_df['status'] = status_df.apply(
            lambda row: f"✓ {int(row['status_code'])}" if row['ok'] else "✗ Error",
            axis=1
        )
        status_df['latency_ms'] = status_df['latency_ms'].round(1)
        status_df = status_df[['name', 'url', 'status', 'latency_ms', 'timestamp_utc']]
        status_df.columns = ['Name', 'URL', 'Status', 'Latency (ms)', 'Last Check']
        
        st.dataframe(status_df, use_container_width=True, hide_index=True)
    else:
        st.info("No data available yet. Start the collector to begin monitoring.")
    
    # Uptime and Charts Section
    st.header("Historical Data")
    
    # Get data for selected window
    endpoint_filter = None if selected_endpoint == "All" else selected_endpoint
    history_df = get_checks_for_window(endpoint_filter, window_hours)
    
    if history_df.empty:
        st.info(f"No data available for the selected time window ({selected_window}).")
    else:
        # Convert timestamp to datetime
        history_df['timestamp'] = pd.to_datetime(history_df['timestamp_utc'])
        
        # Uptime Percentage
        col1, col2 = st.columns(2)
        
        with col1:
            if endpoint_filter:
                uptime = calculate_uptime(history_df)
                st.metric("Uptime", f"{uptime:.2f}%")
            else:
                st.write("**Uptime by Endpoint:**")
                uptime_data = []
                for name in history_df['name'].unique():
                    endpoint_df = history_df[history_df['name'] == name]
                    uptime_pct = calculate_uptime(endpoint_df)
                    uptime_data.append({'Endpoint': name, 'Uptime %': uptime_pct})
                
                uptime_df = pd.DataFrame(uptime_data)
                st.dataframe(uptime_df, use_container_width=True, hide_index=True)
        
        with col2:
            total_checks = len(history_df)
            st.metric("Total Checks", total_checks)
        
        # Latency Chart
        st.subheader("Latency Over Time")
        
        if endpoint_filter:
            # Single endpoint - line chart
            fig = px.line(
                history_df,
                x='timestamp',
                y='latency_ms',
                title=f"Latency for {endpoint_filter}",
                labels={'latency_ms': 'Latency (ms)', 'timestamp': 'Time'}
            )
            fig.update_traces(mode='lines+markers')
        else:
            # Multiple endpoints - line chart with different colors
            fig = px.line(
                history_df,
                x='timestamp',
                y='latency_ms',
                color='name',
                title="Latency Over Time (All Endpoints)",
                labels={'latency_ms': 'Latency (ms)', 'timestamp': 'Time', 'name': 'Endpoint'}
            )
            fig.update_traces(mode='lines+markers')
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Export CSV
        st.subheader("Export Data")
        csv = history_df.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"pingpal_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )


if __name__ == "__main__":
    main()

