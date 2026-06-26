import os
import json
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Set up Streamlit page configuration
st.set_page_config(
    page_title="Cooperation Systems Evaluation Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Professional scientific styling styling (CSS)
st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 15px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .metric-val {
        font-size: 24px;
        font-weight: bold;
        color: #1f77b4;
    }
    .metric-label {
        font-size: 14px;
        color: #6c757d;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
</style>
""", unsafe_allow_html=True)

st.title("📊 Cooperation Systems Evaluation Dashboard")
st.markdown("""
*Cooperation Systems (M.Sc.) — Quantitative Evaluation of NLP-based Triggers vs. Slash Commands in Community Engagement Bots.*
""")

LOG_FILE = "metrics_log.jsonl"

def load_data():
    if not os.path.exists(LOG_FILE):
        return pd.DataFrame()
    
    entries = []
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    
    if not entries:
        return pd.DataFrame()
        
    df = pd.DataFrame(entries)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df

df = load_data()

if df.empty:
    st.warning("⚠️ No metrics log file found (`metrics_log.jsonl` is missing or empty).")
    st.info("💡 Pro-tip: Please run the mock data generator script `generate_mock_logs.py` to seed evaluation logs immediately, or trigger interactions with the bot in Discord.")
    if st.button("🚀 Seed Mock Data Now"):
        import subprocess
        subprocess.run([".venv/Scripts/python.exe", "generate_mock_logs.py"])
        st.rerun()
else:
    # Sidebar filters
    st.sidebar.header("🔬 Evaluation Filters")
    
    min_date = df["timestamp"].min().date()
    max_date = df["timestamp"].max().date()
    
    date_range = st.sidebar.date_input(
        "Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
    
    # Apply date filters
    if len(date_range) == 2:
        start_date, end_date = date_range
        df_filtered = df[(df["timestamp"].dt.date >= start_date) & (df["timestamp"].dt.date <= end_date)]
    else:
        df_filtered = df.copy()

    # Calculate statistics
    total_events = len(df_filtered)
    nlp_events = len(df_filtered[df_filtered["interface"] == "natural_language"])
    cmd_events = len(df_filtered[df_filtered["interface"] == "slash_command"])
    
    unique_users = df_filtered["user"].nunique()
    # Filter out system user from user count if present
    if "system" in df_filtered["user"].values:
        unique_users = max(0, unique_users - 1)
        
    nlp_ratio = (nlp_events / total_events * 100) if total_events > 0 else 0

    # Layout: Top Row Summary Cards
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="metric-card"><div class="metric-val">{total_events}</div><div class="metric-label">Total Events (N)</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-card"><div class="metric-val">{nlp_events}</div><div class="metric-label">NLP Actions</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="metric-card"><div class="metric-val">{cmd_events}</div><div class="metric-label">Slash Commands</div></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="metric-card"><div class="metric-val">{nlp_ratio:.1f}%</div><div class="metric-label">NLP Adoption Ratio</div></div>', unsafe_allow_html=True)

    st.markdown("---")

    # Layout: Row 1 - Main adoption comparison
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.subheader("💡 Topic Driving Interface Comparison")
        st.write("Quantitative comparison of `/drive-topic` slash command usage vs. NLP-triggered channel creation.")
        
        drive_df = df_filtered[df_filtered["functionality"] == "drive-topic"]
        if not drive_df.empty:
            drive_counts = drive_df["interface"].value_counts().reset_index()
            drive_counts.columns = ["Interface", "Count"]
            
            fig1 = px.bar(
                drive_counts, 
                x="Interface", 
                y="Count", 
                color="Interface",
                color_discrete_map={"natural_language": "#17a2b8", "slash_command": "#007bff"},
                labels={"Interface": "Trigger Type", "Count": "Invocations"},
                template="plotly_white"
            )
            fig1.update_layout(showlegend=False)
            st.plotly_chart(fig1, use_container_width=True)
        else:
            st.info("No topic driving events logged in this range.")

    with col_chart2:
        st.subheader("🔍 Player Search Interface Comparison")
        st.write("Quantitative comparison of `/search-interest` slash command usage vs. NLP-triggered search matchmaking.")
        
        search_df = df_filtered[df_filtered["functionality"] == "search-interest"]
        if not search_df.empty:
            search_counts = search_df["interface"].value_counts().reset_index()
            search_counts.columns = ["Interface", "Count"]
            
            fig2 = px.bar(
                search_counts, 
                x="Interface", 
                y="Count", 
                color="Interface",
                color_discrete_map={"natural_language": "#17a2b8", "slash_command": "#007bff"},
                labels={"Interface": "Trigger Type", "Count": "Invocations"},
                template="plotly_white"
            )
            fig2.update_layout(showlegend=False)
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No player search events logged in this range.")

    # Layout: Row 2 - Topic channel usage & timelines
    col_chart3, col_chart4 = st.columns(2)

    with col_chart3:
        st.subheader("💬 Topic Channels Message Activity")
        st.write("Analysis of messages sent inside user-driven-topics channels (Human Users vs. Persona Agent Webhooks).")
        
        msg_df = df_filtered[df_filtered["event_type"] == "channel_message"].copy()
        if not msg_df.empty:
            # Parse detail fields
            msg_df["is_bot"] = msg_df["details"].apply(lambda d: d.get("is_bot", False) if isinstance(d, dict) else False)
            msg_df["sender_type"] = msg_df["is_bot"].apply(lambda b: "Simulated Agent (Bot)" if b else "Real User (Human)")
            
            msg_counts = msg_df.groupby(["channel", "sender_type"]).size().reset_index(name="Message Count")
            
            fig3 = px.bar(
                msg_counts,
                x="Message Count",
                y="channel",
                color="sender_type",
                orientation="h",
                color_discrete_map={"Real User (Human)": "#28a745", "Simulated Agent (Bot)": "#fd7e14"},
                labels={"channel": "Driven Channel", "sender_type": "Participant Type"},
                template="plotly_white"
            )
            fig3.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("No driven topic channel messages logged in this range.")

    with col_chart4:
        st.subheader("📈 Adoption Timeline Trend")
        st.write("Daily trend chart comparing natural language (NLP) vs. slash command invocation frequency.")
        
        df_ts = df_filtered[df_filtered["event_type"].isin(["command_used", "nlp_triggered"])].copy()
        if not df_ts.empty:
            df_ts["date"] = df_ts["timestamp"].dt.date
            ts_counts = df_ts.groupby(["date", "interface"]).size().reset_index(name="Invocations")
            
            fig4 = px.line(
                ts_counts,
                x="date",
                y="Invocations",
                color="interface",
                color_discrete_map={"natural_language": "#17a2b8", "slash_command": "#007bff"},
                labels={"date": "Date", "Invocations": "Daily Count", "interface": "Interface"},
                template="plotly_white"
            )
            fig4.update_traces(mode="lines+markers")
            fig4.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig4, use_container_width=True)
        else:
            st.info("No command or NLP trigger timeline events logged in this range.")

    st.markdown("---")

    # Raw Data Explorer
    st.subheader("🔍 Raw Log Inspector")
    with st.expander("Click to browse metrics log data table ($N$)"):
        df_display = df_filtered.copy()
        # Convert timestamp to string for clean display
        df_display["timestamp"] = df_display["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
        
        st.dataframe(df_display, use_container_width=True)
        
        # Download button
        csv = df_filtered.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Export Log Data as CSV",
            data=csv,
            file_name=f"bot_metrics_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )
