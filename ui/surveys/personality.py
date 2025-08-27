#!/usr/bin/env python3
"""
Personality Assessment Module for User Studies

This module contains the Big Five personality assessment questionnaire,
scoring functions, and classification logic for balanced assignment.
"""

import json
import streamlit as st
from datetime import datetime
from typing import Dict, Any

try:
    from sotopia.database import EpisodeLog
except ImportError:
    # Fallback for when database is not available
    EpisodeLog = None


# Big Five Personality Assessment Questions
PERSONALITY_QUESTIONS = {
    # Extroversion items (E)
    1: {"text": "I am the life of the party.", "dimension": "extroversion", "reverse": False},
    6: {"text": "I don't talk a lot.", "dimension": "extroversion", "reverse": True},
    11: {"text": "I feel comfortable around people.", "dimension": "extroversion", "reverse": False},
    16: {"text": "I keep in the background.", "dimension": "extroversion", "reverse": True},
    21: {"text": "I start conversations.", "dimension": "extroversion", "reverse": False},
    26: {"text": "I have little to say.", "dimension": "extroversion", "reverse": True},
    31: {"text": "I talk to a lot of different people at parties.", "dimension": "extroversion", "reverse": False},
    36: {"text": "I don't like to draw attention to myself.", "dimension": "extroversion", "reverse": True},
    41: {"text": "I don't mind being the center of attention.", "dimension": "extroversion", "reverse": False},
    46: {"text": "I am quiet around strangers.", "dimension": "extroversion", "reverse": True},
    
    # Agreeableness items (A)
    2: {"text": "I feel little concern for others.", "dimension": "agreeableness", "reverse": True},
    7: {"text": "I am interested in people.", "dimension": "agreeableness", "reverse": False},
    12: {"text": "I insult people.", "dimension": "agreeableness", "reverse": True},
    17: {"text": "I sympathize with others' feelings.", "dimension": "agreeableness", "reverse": False},
    22: {"text": "I am not interested in other people's problems.", "dimension": "agreeableness", "reverse": True},
    27: {"text": "I have a soft heart.", "dimension": "agreeableness", "reverse": False},
    32: {"text": "I am not really interested in others.", "dimension": "agreeableness", "reverse": True},
    37: {"text": "I take time out for others.", "dimension": "agreeableness", "reverse": False},
    42: {"text": "I feel others' emotions.", "dimension": "agreeableness", "reverse": False},
    47: {"text": "I make people feel at ease.", "dimension": "agreeableness", "reverse": False},
}


def calculate_personality_scores(responses: Dict[int, int]) -> Dict[str, int]:
    """Calculate Big Five personality scores using the provided formulas."""
    # Extroversion calculation: E = 20 + (1) - (6) + (11) - (16) + (21) - (26) + (31) - (36) + (41) - (46)
    extroversion = (20 + 
                   responses.get(1, 3) - responses.get(6, 3) + 
                   responses.get(11, 3) - responses.get(16, 3) + 
                   responses.get(21, 3) - responses.get(26, 3) + 
                   responses.get(31, 3) - responses.get(36, 3) + 
                   responses.get(41, 3) - responses.get(46, 3))
    
    # Agreeableness calculation: A = 14 - (2) + (7) - (12) + (17) - (22) + (27) - (32) + (37) + (42) + (47)
    agreeableness = (14 - responses.get(2, 3) + responses.get(7, 3) - 
                    responses.get(12, 3) + responses.get(17, 3) - 
                    responses.get(22, 3) + responses.get(27, 3) - 
                    responses.get(32, 3) + responses.get(37, 3) + 
                    responses.get(42, 3) + responses.get(47, 3))
    
    return {
        "extroversion": extroversion,
        "agreeableness": agreeableness
    }


def classify_personality(extroversion: int, agreeableness: int) -> Dict[str, str]:
    """Classify personality into quartiles for balanced assignment."""
    # Define quartile cutoffs (these may need adjustment based on population data)
    ext_cutoff = 30  # Median split for extroversion
    agree_cutoff = 42  # Median split for agreeableness
    
    ext_level = "high" if extroversion >= ext_cutoff else "low"
    agree_level = "high" if agreeableness >= agree_cutoff else "low"
    
    personality_type = f"{ext_level}_ext_{agree_level}_agree"
    
    return {
        "extroversion_level": ext_level,
        "agreeableness_level": agree_level,
        "personality_type": personality_type,
        "extroversion_score": extroversion,
        "agreeableness_score": agreeableness
    }


class PersonalityAssessmentTracker:
    """Track personality assessment data in Redis"""
    
    @staticmethod
    def save_assessment(participant_id: str, responses: Dict[int, int], scores: Dict[str, int], prestudy_responses: Dict[int, any] = None) -> str:
        """Save personality assessment and pre-study responses to Redis database"""
        if not EpisodeLog:
            st.error("Database connection not available")
            return ""
            
        try:
            assessment_data = {
                "participant_id": participant_id,
                "timestamp": datetime.now().isoformat(),
                "personality_responses": responses,
                "personality_scores": scores,
                "prestudy_responses": prestudy_responses or {},
                "assessment_type": "personality_and_prestudy"
            }
            
            # Create a temporary episode log to store assessment data
            assessment_log = EpisodeLog(
                environment="personality_assessment",
                agents=[participant_id],
                tag=f"personality_assessment_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{participant_id[:8]}",
                models=["personality_assessment"],
                messages=[],  # No conversation messages for assessment
                reasoning=json.dumps(assessment_data, indent=2),
                rewards=[0.0]
            )
            
            assessment_log.save()
            return assessment_log.pk
            
        except Exception as e:
            st.error(f"Error saving personality assessment: {str(e)}")
            return ""
    
    @staticmethod
    def get_assessment(participant_id: str) -> Dict[str, Any]:
        """Retrieve existing personality assessment for a participant"""
        if not EpisodeLog:
            return {}
            
        try:
            # Find assessment episodes for this participant
            all_episodes = EpisodeLog.find().all()
            for episode in all_episodes:
                if (episode.environment == "personality_assessment" and 
                    participant_id in episode.agents):
                    try:
                        assessment_data = json.loads(episode.reasoning)
                        if assessment_data.get("participant_id") == participant_id:
                            return assessment_data
                    except json.JSONDecodeError:
                        continue
            return {}
        except Exception as e:
            print(f"Error retrieving personality assessment: {e}")
            return {}