"""
Utility functions for displaying scenarios and goals in the user study interface.
Includes both text formatting and chart generation functionality.
"""
import re
import pandas as pd
import altair as alt
import streamlit as st
from datetime import datetime


# =============================================================================
# TEXT FORMATTING UTILITIES
# =============================================================================

def clean_and_format_goal_text(goal_text: str) -> str:
    """Apply comprehensive text formatting fixes to goal text."""
    # Remove backstory and strategy hints
    clean_goal = re.sub(r'<extra_info>.*?</extra_info>', '', goal_text, flags=re.DOTALL)
    clean_goal = re.sub(r'<strategy_hint>.*?</strategy_hint>', '', clean_goal, flags=re.DOTALL)
    clean_goal = clean_goal.strip()
    
    # Fix specific problematic patterns
    clean_goal = re.sub(r'(\d+),(\d+)gives', r'\1,\2 gives', clean_goal)
    clean_goal = re.sub(r'(\d+)points', r'\1 points', clean_goal)  
    clean_goal = re.sub(r'you(\d+)', r'you \1', clean_goal)
    clean_goal = re.sub(r'(\d+)gives', r'\1 gives', clean_goal)
    clean_goal = re.sub(r'points,(\$)', r'points, \1', clean_goal)
    clean_goal = re.sub(r'([a-z])(\d+)', r'\1 \2', clean_goal)
    clean_goal = re.sub(r'(\d+)([a-z])', r'\1 \2', clean_goal)
    clean_goal = re.sub(r'([a-z])([A-Z])', r'\1 \2', clean_goal)
    
    return clean_goal


def add_text_formatting(text: str) -> str:
    """Add formatting for line breaks and highlighting."""
    # Add line breaks before sentences that start with key phrases
    text = re.sub(r'\s+(Your salary|Your starting date|These are the only)\b', r'<br>\1', text, flags=re.IGNORECASE)
    text = re.sub(r'\.\s+(Do not)', r'. <br>\1', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+(There are \d+ different)', r'<br>\1', text, flags=re.IGNORECASE)
    
    # Highlight [IMPORTANT] tags
    text = re.sub(
        r'\[IMPORTANT\](.*?)(?=\[|$)', 
        r'<div style="background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 8px 12px; margin: 8px 0; border-radius: 4px;"><strong>🚨 IMPORTANT:</strong> \1</div>', 
        text, flags=re.DOTALL
    )
    
    # Highlight "Your goal is to" sentences
    text = re.sub(
        r'(Your goal is to[^.]*\.)', 
        r'<div style="background-color: #e7f3ff; border-left: 4px solid #0d6efd; padding: 8px 12px; margin: 8px 0; border-radius: 4px;"><strong>🎯 \1</strong></div>', 
        text, flags=re.IGNORECASE
    )
    
    # Highlight key action words
    key_words = ['negotiate', 'convince', 'persuade', 'achieve', 'obtain', 'secure', 'maximize', 'minimize']
    for word in key_words:
        text = re.sub(f'\\b({word})\\b', r'<strong style="color: #0d6efd;">\1</strong>', text, flags=re.IGNORECASE)
    
    return text


def format_job_negotiation_text(text: str) -> str:
    """Format text specifically for job negotiation scenarios."""
    # Remove detailed point breakdown sentences and add reference to charts
    text = re.sub(
        r'There are 5 different amounts you can agree on, each associated with a different number of points for you\.\s*([^.]*gives you \d+ points[^.]*\.)',
        r'There are 5 different amounts you can agree on, each associated with a different number of points for you. See the bar chart below for details.',
        text, flags=re.DOTALL
    )
    
    text = re.sub(
        r'There are 5 different dates you can agree on, each associated with a different number of points for you\.\s*([^.]*gives you \d+ points[^.]*\.)',
        r'There are 5 different dates you can agree on, each associated with a different number of points for you. See the bar chart below for details.',
        text, flags=re.DOTALL
    )
    
    # Add section formatting
    text = re.sub(r'\b(Salary|Starting Date|Start Date):', r'<br><strong style="color: #495057; font-size: 18px;">\1:</strong>', text, flags=re.IGNORECASE)
    
    # Clean up whitespace
    text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
    return text.strip()


def format_non_job_text(text: str) -> str:
    """Format text for non-job scenarios."""
    # Section headers
    text = re.sub(r'\b(Salary|Starting Date|Start Date):', r'<strong style="color: #495057; font-size: 18px;">\1:</strong> ', text, flags=re.IGNORECASE)
    
    # Highlight numerical values and dates
    text = re.sub(r'(\$\d{1,3}(?:,\d{3})*|\d{1,3}(?:,\d{3})*\s*points?)', r'<strong style="background-color: #f8f9fa; padding: 2px 4px; border-radius: 3px;">\1</strong>', text)
    text = re.sub(r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}\b', r'<strong style="background-color: #f8f9fa; padding: 2px 4px; border-radius: 3px;">\g<0></strong>', text, flags=re.IGNORECASE)
    
    return text


def create_styled_container(content: str) -> str:
    """Create a styled container with grey background."""
    return f"""
    <div style="
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        border: 2px solid #dee2e6;
        border-radius: 8px;
        padding: 20px;
        margin: 16px 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    ">
        <div style="font-size: 16px; line-height: 1.6; color: #212529;">
            {content}
        </div>
    </div>
    """


# =============================================================================
# CHART GENERATION UTILITIES
# =============================================================================

def parse_salary_data(goal_text: str) -> list:
    """Parse salary information from goal text."""
    salary_data = []
    salary_pattern = r'\$(\d{2,3}),000\s+gives\s+you\s+(\d+)\s*points?'
    salary_matches = re.findall(salary_pattern, goal_text)
    
    for match in salary_matches:
        salary_amount = int(match[0])
        points = int(match[1])
        salary_data.append({
            'Salary': f'${salary_amount},000',
            'Amount': salary_amount,
            'Points': points
        })
    
    salary_data.sort(key=lambda x: x['Amount'])
    return salary_data


def parse_date_data(goal_text: str) -> list:
    """Parse starting date information from goal text."""
    date_data = []
    date_pattern = r'((?:June|July|August)\s+\d{1,2})\s+gives\s+you\s+(\d+)\s*points?'
    date_matches = re.findall(date_pattern, goal_text)
    
    for match in date_matches:
        date_str = match[0]
        points = int(match[1])
        try:
            date_obj = datetime.strptime(f"{date_str} 2024", "%B %d %Y")
        except ValueError:
            date_obj = datetime.now()
        
        date_data.append({
            'Starting Date': date_str,
            'Points': points,
            'date_obj': date_obj
        })
    
    date_data.sort(key=lambda x: x['date_obj'], reverse=True)
    return date_data


def create_salary_chart(salary_data: list, shared_scale: tuple = None) -> alt.Chart:
    """Create salary bar chart with optional shared scale."""
    salary_df = pd.DataFrame(salary_data)
    x_encoding = alt.X('Points:Q', title='Points')
    if shared_scale:
        x_encoding = alt.X('Points:Q', title='Points', scale=alt.Scale(domain=shared_scale))
    
    return alt.Chart(salary_df).mark_bar().encode(
        x=x_encoding,
        y=alt.Y('Salary:N', title='Salary', sort=alt.EncodingSortField(field='Amount', order='ascending')),
        color=alt.Color('Points:Q', scale=alt.Scale(scheme='blues'), legend=None),
        tooltip=['Salary', 'Points']
    ).properties(height=180, width=400)


def create_date_chart(date_data: list, shared_scale: tuple = None) -> alt.Chart:
    """Create date bar chart with optional shared scale."""
    date_df = pd.DataFrame(date_data)
    date_order = [item['Starting Date'] for item in date_data]
    x_encoding = alt.X('Points:Q', title='Points')
    if shared_scale:
        x_encoding = alt.X('Points:Q', title='Points', scale=alt.Scale(domain=shared_scale))
    
    return alt.Chart(date_df).mark_bar().encode(
        x=x_encoding,
        y=alt.Y('Starting Date:N', title='Starting Date', sort=date_order),
        color=alt.Color('Points:Q', scale=alt.Scale(scheme='greens'), legend=None),
        tooltip=['Starting Date', 'Points']
    ).properties(height=180, width=400)


def generate_inline_salary_chart(goal_text: str, scenario_codename: str = None):
    """Generate inline salary bar chart."""
    salary_data = parse_salary_data(goal_text)
    if salary_data:
        st.markdown("##### 💰 **Salary Points**")
        salary_chart = create_salary_chart(salary_data)
        st.altair_chart(salary_chart, use_container_width=True)


def generate_inline_date_chart(goal_text: str, scenario_codename: str = None):
    """Generate inline date bar chart."""
    date_data = parse_date_data(goal_text)
    if date_data:
        st.markdown("##### 📅 **Start Date Points**")
        date_chart = create_date_chart(date_data)
        st.altair_chart(date_chart, use_container_width=True)


def calculate_shared_scale(salary_data: list, date_data: list) -> tuple:
    """Calculate shared x-axis scale based on combined data ranges."""
    all_points = []
    
    # Collect all point values from both datasets
    if salary_data:
        all_points.extend([item['Points'] for item in salary_data])
    if date_data:
        all_points.extend([item['Points'] for item in date_data])
    
    if not all_points:
        return (0, 100)  # Default range if no data
    
    min_points = min(all_points)
    max_points = max(all_points)
    
    # Add some padding (10% on each side)
    padding = (max_points - min_points) * 0.1
    return (max(0, min_points - padding), max_points + padding)


def generate_negotiation_tables(goal_text: str, scenario_codename: str = None):
    """Generate side-by-side bar charts with shared scale for job negotiation scenarios."""
    salary_data = parse_salary_data(goal_text)
    date_data = parse_date_data(goal_text)
    
    if salary_data and date_data:
        # Calculate shared scale based on both datasets
        shared_scale = calculate_shared_scale(salary_data, date_data)
        
        st.markdown("#### **Point Values**")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("##### 💰 **Salary Points**")
            salary_chart = create_salary_chart(salary_data, shared_scale)
            st.altair_chart(salary_chart, use_container_width=True)
        
        with col2:
            st.markdown("##### 📅 **Start Date Points**")
            date_chart = create_date_chart(date_data, shared_scale)
            st.altair_chart(date_chart, use_container_width=True)