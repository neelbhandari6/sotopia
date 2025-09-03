#!/usr/bin/env python3
"""
Survey Questions Module for User Studies

This module contains all survey questions and rendering logic for pre-study
and post-study surveys, including AI experience, attitude, and outcome measures.
"""

import streamlit as st
from typing import Dict, Any


# AI Experience Questions
AI_EXPERIENCE_QUESTIONS = {
    # AI Usage Frequency
    101: {
        "text": "How often do you use conversational AI systems (like ChatGPT, Claude, etc.)?",
        "type": "single_choice",
        "options": ["Daily", "Several times per week", "Weekly", "Monthly", "Rarely", "Never"]
    },
    
    # AI Usage Purposes (Multi-select)
    102: {
        "text": "What do you primarily use conversational AI for? (Select all that apply)",
        "type": "multi_choice",
        "options": [
            "Getting information/answers to questions",
            "Help with work/professional tasks", 
            "Creative writing or brainstorming",
            "Learning new topics",
            "Problem-solving assistance",
            "Entertainment/casual conversation",
            "Technical/coding help",
            "Other"
        ]
    },
    
    # AI Comfort Level
    103: {
        "text": "How comfortable are you with conversational AI systems?",
        "type": "scale",
        "scale_labels": ["Very uncomfortable", "Very comfortable"],
        "scale_range": [1, 7]
    }
}


# AI Attitude Questions (5-point Likert scale)
AI_ATTITUDE_QUESTIONS = {
    201: {
        "text": "I understand what conversational AI can and cannot do.",
        "type": "likert_5"
    },
    202: {
        "text": "I think critically about information provided by conversational AI.",
        "type": "likert_5"
    },
    203: {
        "text": "I trust conversational AI to provide accurate information.",
        "type": "likert_5"
    },
    204: {
        "text": "Conversational AI systems perform consistently well.",
        "type": "likert_5"
    },
    205: {
        "text": "I believe conversational AI systems have users' best interests in mind.",
        "type": "likert_5"
    },
    206: {
        "text": "I can rely on conversational AI to be truthful.",
        "type": "likert_5"
    }
}


# Trust and Negotiation Background Questions
TRUST_NEGOTIATION_QUESTIONS = {
    301: {
        "text": "I generally trust other people.",
        "type": "likert_5"
    },
    302: {
        "text": "I feel comfortable with negotiating.",
        "type": "likert_5"
    }
}


def render_question(q_num: int, question_data: Dict[str, Any], session_key: str = "assessment_responses") -> None:
    """Render a survey question based on its type and store response in session state"""
    st.markdown(f"**{question_data['text']}**")
    
    q_type = question_data.get('type', 'personality')
    
    if q_type == 'personality' or q_type == 'likert_5':
        # 5-point Likert scale
        if q_type == 'personality':
            response_options = [
                "1 - Very Inaccurate",
                "2 - Moderately Inaccurate", 
                "3 - Neither Accurate nor Inaccurate",
                "4 - Moderately Accurate",
                "5 - Very Accurate"
            ]
        else:  # likert_5
            response_options = [
                "1 - Strongly disagree",
                "2 - Disagree", 
                "3 - Neutral",
                "4 - Agree",
                "5 - Strongly agree"
            ]
        
        current_response = st.session_state[session_key].get(q_num, None)
        response = st.radio(
            f"Response for question {q_num}",
            options=response_options,
            index=current_response - 1 if current_response is not None else None,
            key=f"question_{q_num}",
            label_visibility="collapsed",
            horizontal=True
        )
        
        if response is not None:
            numeric_response = int(response.split(" - ")[0])
            st.session_state[session_key][q_num] = numeric_response
            
    elif q_type == 'single_choice':
        current_response = st.session_state[session_key].get(q_num, None)
        response = st.radio(
            f"Response for question {q_num}",
            options=question_data['options'],
            index=question_data['options'].index(current_response) if current_response in question_data['options'] else None,
            key=f"question_{q_num}",
            label_visibility="collapsed"
        )
        
        if response is not None:
            st.session_state[session_key][q_num] = response
            
    elif q_type == 'multi_choice':
        current_responses = st.session_state[session_key].get(q_num, [])
        if not isinstance(current_responses, list):
            current_responses = []
        
        st.write("Select all that apply:")
        responses = []
        for option in question_data['options']:
            checked = st.checkbox(
                option,
                value=option in current_responses,
                key=f"question_{q_num}_{option}"
            )
            if checked:
                responses.append(option)
        
        st.session_state[session_key][q_num] = responses
            
    elif q_type == 'scale':
        scale_min, scale_max = question_data['scale_range']
        current_response = st.session_state[session_key].get(q_num, scale_min)
        
        response = st.slider(
            f"{question_data['scale_labels'][0]} → {question_data['scale_labels'][1]}",
            min_value=scale_min,
            max_value=scale_max,
            value=current_response,
            key=f"question_{q_num}"
        )
        
        st.session_state[session_key][q_num] = response


def count_completed_responses(responses_dict: Dict[int, Any]) -> int:
    """Count completed responses in a survey section"""
    count = 0
    for response in responses_dict.values():
        if isinstance(response, list):
            if len(response) > 0:
                count += 1
        elif response is not None and response != "":
            count += 1
    return count


def display_post_study_survey() -> Dict[str, Any]:
    """Display post-study survey and return responses"""
    st.markdown("---")
    st.markdown("## 📋 **Post-Study Survey**")
    st.markdown("Please answer the following questions about your interaction with the AI agent.")
    
    survey_responses = {}
    
    # Initialize slider interaction tracking in session state
    if "slider_interactions" not in st.session_state:
        st.session_state.slider_interactions = {}
    
    # Add instruction for users about slider interaction
    st.info("📌 **Note**: For slider questions, you can either move the slider to your preferred position or leave it at the middle position (4) if that represents your view.")
    
    # Manipulation Checks Section
    st.markdown("### **Agent Perceptions**")
    st.markdown("*Think about the AI agent you just interacted with. Please rate how well each statement describes the AI:*")
    st.markdown("**1 = Strongly disagree, 2 = Disagree, 3 = Neutral, 4 = Agree, 5 = Strongly agree**")
    
    # Transparency check
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("**The AI clearly explained its reasoning and decision-making process.**")
    with col2:
        survey_responses['transparency'] = st.selectbox(
            "", 
            options=[1, 2, 3, 4, 5], 
            format_func=lambda x: {1:"Strongly disagree", 2:"Disagree", 3:"Neutral", 4:"Agree", 5:"Strongly agree"}[x],
            key="transparency_check",
            label_visibility="collapsed"
        )
    
    # Warmth check
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("**The AI communicated in a friendly and caring manner.**")
    with col2:
        survey_responses['warmth'] = st.selectbox(
            "", 
            options=[1, 2, 3, 4, 5], 
            format_func=lambda x: {1:"Strongly disagree", 2:"Disagree", 3:"Neutral", 4:"Agree", 5:"Strongly agree"}[x],
            key="warmth_check",
            label_visibility="collapsed"
        )
    
    # Theory of mind check
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("**The AI seemed to understand my perspective and intentions.**")
    with col2:
        survey_responses['theory_of_mind'] = st.selectbox(
            "", 
            options=[1, 2, 3, 4, 5], 
            format_func=lambda x: {1:"Strongly disagree", 2:"Disagree", 3:"Neutral", 4:"Agree", 5:"Strongly agree"}[x],
            key="tom_check",
            label_visibility="collapsed"
        )
    
    # Adaptability check
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("**The AI was flexible in its approach to our conversations.**")
    with col2:
        survey_responses['adaptability'] = st.selectbox(
            "", 
            options=[1, 2, 3, 4, 5], 
            format_func=lambda x: {1:"Strongly disagree", 2:"Disagree", 3:"Neutral", 4:"Agree", 5:"Strongly agree"}[x],
            key="adaptability_check",
            label_visibility="collapsed"
        )
    
    # Expertise check
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("**The AI seemed well-informed about the topics we discussed.**")
    with col2:
        survey_responses['expertise'] = st.selectbox(
            "", 
            options=[1, 2, 3, 4, 5], 
            format_func=lambda x: {1:"Strongly disagree", 2:"Disagree", 3:"Neutral", 4:"Agree", 5:"Strongly agree"}[x],
            key="expertise_check",
            label_visibility="collapsed"
        )
    
    st.markdown("---")
    
    # Interaction Outcome Section
    st.markdown("### **Interaction Outcome**")
    
    # Goals achievement
    st.markdown("**How successful were you in achieving your goals in this scenario?**")
    def mark_goals_interaction():
        st.session_state.slider_interactions["goals"] = True
    
    survey_responses['goals'] = st.slider(
        "", 
        min_value=1, max_value=7, value=4,
        format="%d",
        help="1 = Completely unsuccessful, 7 = Completely successful",
        key="goals_slider",
        label_visibility="collapsed",
        on_change=mark_goals_interaction
    )
    
    # Satisfaction
    st.markdown("**How satisfied are you with the outcome of this negotiation?**")
    def mark_satisfaction_interaction():
        st.session_state.slider_interactions["satisfaction"] = True
    
    survey_responses['satisfaction'] = st.slider(
        "", 
        min_value=1, max_value=7, value=4,
        format="%d",
        help="1 = Completely dissatisfied, 7 = Completely satisfied",
        key="satisfaction_slider",
        label_visibility="collapsed",
        on_change=mark_satisfaction_interaction
    )
    
    # Conflict resolution
    st.markdown("**How successfully did you resolve any conflicts that arose?**")
    def mark_conflict_interaction():
        st.session_state.slider_interactions["conflict_resolve"] = True
    
    survey_responses['conflict_resolve'] = st.slider(
        "", 
        min_value=1, max_value=7, value=4,
        format="%d",
        help="1 = Very unsuccessfully, 7 = Very successfully",
        key="conflict_slider",
        label_visibility="collapsed",
        on_change=mark_conflict_interaction
    )
    
    st.markdown("---")
    
    # AI Perception Section
    st.markdown("### **AI Agent Perception**")
    
    # Believability
    st.markdown("**How natural and realistic did the AI agent seem during your interaction?**")
    def mark_believability_interaction():
        st.session_state.slider_interactions["believability"] = True
    
    survey_responses['believability'] = st.slider(
        "", 
        min_value=1, max_value=7, value=4,
        format="%d",
        help="1 = Very unnatural, 7 = Very natural",
        key="believability_slider",
        label_visibility="collapsed",
        on_change=mark_believability_interaction
    )
    
    # Transactivity
    st.markdown("**How well did you feel the AI agent built upon and engaged with your points and ideas during the interaction?**")
    def mark_transactivity_interaction():
        st.session_state.slider_interactions["transactivity"] = True
    
    survey_responses['transactivity'] = st.slider(
        "", 
        min_value=1, max_value=7, value=4,
        format="%d",
        help="1 = Not at all, 7 = Extremely well",
        key="transactivity_slider",
        label_visibility="collapsed",
        on_change=mark_transactivity_interaction
    )
    
    # Truthfulness
    st.markdown("**How truthful was the AI agent during your interaction?**")
    def mark_truthfulness_interaction():
        st.session_state.slider_interactions["truthfulness"] = True
    
    survey_responses['truthfulness'] = st.slider(
        "", 
        min_value=1, max_value=7, value=4,
        format="%d",
        help="1 = Very untruthful, 7 = Very truthful",
        key="truthfulness_slider",
        label_visibility="collapsed",
        on_change=mark_truthfulness_interaction
    )
    
    st.markdown("---")
    
    # Optional feedback
    st.markdown("### **Additional Feedback (Optional)**")
    survey_responses['additional_feedback'] = st.text_area(
        "Is there anything else you'd like to share about your experience with the AI agent?",
        key="additional_feedback",
        height=100
    )
    
    return survey_responses