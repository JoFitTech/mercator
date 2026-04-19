"""Zentrales Styling-Modul für Mercator (Requirement 5.1)."""

import streamlit as st

def apply_ui_theme():
    """Wendet das globale CSS-Theme auf die Streamlit-App an."""
    st.markdown("""
        <style>
        /* Modernes Mercator Theme */
        
        /* Schriftarten und Grundstil */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }
        
        .mono {
            font-family: 'JetBrains Mono', monospace;
        }
        
        /* Metriken Styling */
        [data-testid="stMetric"] {
            background-color: #ffffff;
            border: 1px solid #e9ecef;
            padding: 1rem;
            border-radius: 0.75rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.02);
            transition: transform 0.2s ease;
        }
        [data-testid="stMetric"]:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            border-color: #dee2e6;
        }
        
        /* Badges & Labels */
        .mercator-badge {
            display: inline-block;
            padding: 0.25rem 0.6rem;
            font-size: 0.75rem;
            font-weight: 500;
            border-radius: 1rem;
            text-transform: uppercase;
            letter-spacing: 0.025em;
        }
        
        /* Custom Header Styling */
        h1, h2, h3 {
            font-weight: 700 !important;
            letter-spacing: -0.02em !important;
            color: #1a1b1e;
        }
        
        /* Sidebar Optimierung */
        [data-testid="stSidebar"] {
            background-color: #f8f9fa;
            border-right: 1px solid #e9ecef;
        }
        
        /* Tabellen Styling */
        .stDataFrame {
            border-radius: 0.5rem;
            overflow: hidden;
        }
        
        /* Utility Classes */
        .text-muted { color: #6c757d; }
        .text-success { color: #22c55e; }
        .text-danger { color: #ef4444; }
        .text-warning { color: #facc15; }
        
        </style>
    """, unsafe_allow_html=True)

def render_state_box(message: str, type: str = "info"):
    """Rendert eine Status-Box in der UI."""
    if type == "info":
        st.info(message)
    elif type == "success":
        st.success(message)
    elif type == "warning":
        st.warning(message)
    elif type == "error":
        st.error(message)
