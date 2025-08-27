import streamlit as st
import json
import re
import csv
import os
import asyncio
from datetime import datetime

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not installed, skip loading .env file
    pass
from typing import Any
from uuid import uuid4
from ui.rendering import (
    get_scenarios,
    get_agents,
    get_models,
)
from sotopia.database import EpisodeLog, AgentProfile, EnvironmentProfile
from sotopia.transparency_hook import make_transparency_agent
from sotopia.messages import Observation, AgentAction

# Import utility modules
from ui.consent_form_content import CONSENT_FORM_TEXT
from ui.scenario_display_utils import (
    clean_and_format_goal_text,
    add_text_formatting,
    format_job_negotiation_text,
    format_non_job_text,
    create_styled_container,
    generate_inline_salary_chart,
    generate_inline_date_chart,
    generate_negotiation_tables
)

# Import survey modules
from ui.surveys.personality import (
    PERSONALITY_QUESTIONS,
    calculate_personality_scores,
    classify_personality,
    PersonalityAssessmentTracker
)
from ui.surveys.questions import (
    AI_EXPERIENCE_QUESTIONS,
    AI_ATTITUDE_QUESTIONS, 
    TRUST_NEGOTIATION_QUESTIONS,
    render_question,
    display_post_study_survey,
    count_completed_responses
)

# Assignment tracking disabled (personality-based balancing removed)

def get_scenario_occupation(scenario_codename: str) -> str:
    """Get appropriate agent occupation based on scenario context"""
    if scenario_codename.startswith('[ai-liedar]'):
        if 'public_image_paraphrase' in scenario_codename:  # travel_restrictions
            return "Health Representative"
        elif 'benefits_need_paraphrase' in scenario_codename:  # laptop_shopping
            return "Sales Assistant"
        elif 'emotion_paraphrase' in scenario_codename:  # business_collab
            return "Personal Assistant"
        else:
            return "Assistant"  # Generic fallback for other ai-liedar scenarios
    elif 'job_interview' in scenario_codename:
        return "Hiring Manager"
    else:
        return "Assistant"  # Generic fallback



def load_local_scenarios() -> dict[str, dict[Any, Any]]:
    """Load scenarios from local JSON files"""
    scenarios = {}
    # Use path relative to the git repo root
    current_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(os.path.dirname(current_dir))  # Go up from ui/pages to repo root
    base_path = os.path.join(repo_root, "reproduce_data", "scenarios_agents")
    
    # Load job interview scenarios
    hiring_scenarios = [
        "job_scenarios_bot_0922_salary_start_date_equal_competitive.json",
        "job_scenarios_bot_0922_salary_start_date_equal_cooperative.json"
    ]
    
    for filename in hiring_scenarios:
        file_path = os.path.join(base_path, "hiring", "scenarios", filename)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                scenario_list = json.load(f)
                for scenario in scenario_list:
                    scenarios[scenario["codename"]] = scenario
        except Exception as e:
            st.error(f"Error loading {filename}: {str(e)}")
    
    # Load AI liedar scenarios
    liedar_scenarios = [
        "ai_liedar_job_env.json",
        "ai_liedar_job_env_2.json", 
        "ai_liedar_job_env_3.json"
    ]
    
    for filename in liedar_scenarios:
        file_path = os.path.join(base_path, "liedar", "scenarios", filename)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                scenario_list = json.load(f)
                for scenario in scenario_list:
                    scenarios[scenario["codename"]] = scenario
        except Exception as e:
            st.error(f"Error loading {filename}: {str(e)}")
    
    return scenarios


def load_local_agents() -> dict[str, dict[Any, Any]]:
    """Load agents from local JSON files"""
    agents = {}
    # Use path relative to the git repo root
    current_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(os.path.dirname(current_dir))  # Go up from ui/pages to repo root
    base_path = os.path.join(repo_root, "reproduce_data", "scenarios_agents")
    
    # Load hiring agents
    try:
        with open(os.path.join(base_path, "hiring", "agent_profiles", "human_agent_agreeable.json"), 'r', encoding='utf-8') as f:
            agent_list = json.load(f)
            for i, agent in enumerate(agent_list):
                # Create unique identifiers for agents
                if 'agent_id' not in agent:
                    agent['agent_id'] = f"hiring_agent_{i}"
                # Create more descriptive keys for the agents
                personality_type = "Unknown"
                if "personality_and_values" in agent:
                    personality = agent["personality_and_values"]
                    if "High Transparency" in personality:
                        personality_type += "_HighT"
                    elif "Low Transparency" in personality:
                        personality_type += "_LowT"
                    if "High Warmth" in personality:
                        personality_type += "_HighW"
                    elif "Low Warmth" in personality:
                        personality_type += "_LowW"
                
                key = f"{agent.get('first_name', 'Unknown')} {agent.get('last_name', 'Agent')} ({agent.get('occupation', 'Unknown')}) - {personality_type}"
                agents[key] = agent
    except Exception as e:
        st.error(f"Error loading hiring agents: {str(e)}")
    
    # Load liedar agents  
    try:
        with open(os.path.join(base_path, "liedar", "agent_profile", "ai_liedar_run.json"), 'r', encoding='utf-8') as f:
            agent_list = json.load(f)
            for i, agent in enumerate(agent_list):
                # Create unique identifiers for agents
                if 'agent_id' not in agent:
                    agent['agent_id'] = f"liedar_agent_{i}"
                # Create more descriptive keys for the agents
                personality_type = "Unknown"
                if "personality_and_values" in agent:
                    personality = agent["personality_and_values"]
                    if "High Transparency" in personality:
                        personality_type += "_HighT"
                    elif "Low Transparency" in personality:
                        personality_type += "_LowT"
                    if "High Warmth" in personality:
                        personality_type += "_HighW"
                    elif "Low Warmth" in personality:
                        personality_type += "_LowW"
                        
                key = f"{agent.get('first_name', 'Unknown')} {agent.get('last_name', 'Agent')} ({agent.get('occupation', 'Unknown')}) - {personality_type}"
                agents[key] = agent
    except Exception as e:
        st.error(f"Error loading liedar agents: {str(e)}")
    
    return agents


def get_models_local() -> dict[str, str]:
    """Simple model dictionary for local use"""
    return {
        "human": "human",
        "ai_agent": "ai_agent"
    }


class SimpleAgentProfile:
    """Simple agent profile that doesn't require database connection"""
    def __init__(self, **kwargs):
        self.first_name = kwargs.get('first_name', 'AI')
        self.last_name = kwargs.get('last_name', 'Agent')
        self.age = kwargs.get('age', 22)
        self.occupation = kwargs.get('occupation', 'Assistant')
        self.gender = kwargs.get('gender', 'Unknown')
        self.gender_pronoun = kwargs.get('gender_pronoun', 'They/them')
        self.public_info = kwargs.get('public_info', '')
        self.big_five = kwargs.get('big_five', '')
        self.moral_values = kwargs.get('moral_values', [])
        self.schwartz_personal_values = kwargs.get('schwartz_personal_values', [])
        self.personality_and_values = kwargs.get('personality_and_values', '')
        self.decision_making_style = kwargs.get('decision_making_style', '')
        self.secret = kwargs.get('secret', '')
        self.mbti = kwargs.get('mbti', '')


def create_agent_profile_from_json(agent_data: dict) -> SimpleAgentProfile:
    """Convert JSON agent data to AgentProfile object without database dependency"""
    # Create SimpleAgentProfile with required fields (no database connection needed)
    agent_profile = SimpleAgentProfile(
        first_name=agent_data.get('first_name', 'AI'),
        last_name=agent_data.get('last_name', 'Agent'),
        age=agent_data.get('age', 22),
        occupation=agent_data.get('occupation', 'Assistant'),
        gender=agent_data.get('gender', 'Unknown'),
        gender_pronoun=agent_data.get('gender_pronoun', 'They/them'),
        public_info=agent_data.get('public_info', ''),
        big_five=agent_data.get('big_five', ''),
        moral_values=agent_data.get('moral_values', []),
        schwartz_personal_values=agent_data.get('schwartz_personal_values', []),
        personality_and_values=agent_data.get('personality_and_values', ''),
        decision_making_style=agent_data.get('decision_making_style', ''),
        secret=agent_data.get('secret', ''),
        mbti=agent_data.get('mbti', ''),
    )
    return agent_profile


async def get_ai_response_async(human_message: str, agent_profile_data: dict, transparency: str, turn_number: int, conversation_context: str = "", scenario_context: str = "", model_name: str = "gpt-4o") -> str:
    """Get AI response using the transparency system"""
    try:
        # Convert JSON data to SimpleAgentProfile (no database needed)
        agent_profile = create_agent_profile_from_json(agent_profile_data)
        
        # Create transparency-aware agent with tag
        tag = "high_transparency" if transparency == "high" else "low_transparency"
        print(f"DEBUG: Creating agent with transparency={transparency}, tag={tag}")
        print(f"DEBUG: Agent profile first_name: {agent_profile.first_name}")
        
        agent = make_transparency_agent(agent_profile, model_name, tag)
        print(f"DEBUG: Created agent type: {type(agent)}")
        print(f"DEBUG: Agent has transparency attribute: {hasattr(agent, 'transparency')}")
        if hasattr(agent, 'transparency'):
            print(f"DEBUG: Agent transparency setting: {agent.transparency}")
        
        # Create observation with scenario context and conversation history
        available_actions = ["speak", "non-verbal communication", "leave"]
        
        # Build the full context string with scenario context, conversation history, and current message
        context_parts = []
        if scenario_context:
            context_parts.append(scenario_context.strip())
        if conversation_context:
            context_parts.append(f"Previous conversation:\n{conversation_context}")
        context_parts.append(f"Human: {human_message}")
        
        full_context = "\n\n".join(context_parts)
        
        # Create observation from human message with enhanced context
        observation = Observation(
            last_turn=full_context,
            turn_number=turn_number,
            available_actions=available_actions,
            legal_info=""
        )
        
        # Get agent's action
        action = await agent.aact(observation)
        
        # Handle the action result more robustly
        if action and hasattr(action, 'argument') and action.argument:
            result = action.argument
            # Ensure result is a string, not a dict
            if isinstance(result, dict):
                # If it's a dict, try to extract meaningful text
                result = result.get('description', str(result))
            elif not isinstance(result, str):
                result = str(result)
        else:
            result = "I understand."
            
        print(f"DEBUG ASYNC: Action type: {action.action_type if action else 'None'}")
        print(f"DEBUG ASYNC: Raw argument: {action.argument if action else 'None'}")
        print(f"DEBUG ASYNC: Processed result: {result[:100]}...")
        
        # Return both result and debug info (can't store session state in thread)
        debug_info = {
            'turn_number': turn_number,
            'full_context': full_context,
            'agent_name': agent_profile_data.get('first_name', 'AI'),
            'transparency': transparency,
            'scenario_context': scenario_context,
            'conversation_context': conversation_context,
            'human_message': human_message,
            'ai_response': result
        }
        
        print(f"DEBUG ASYNC: Created debug info for turn {turn_number}")
        return result, debug_info
        
    except Exception as e:
        st.error(f"Error getting AI response: {str(e)}")
        import traceback
        st.error(f"Full traceback: {traceback.format_exc()}")
        # Also log to console for debugging
        print(f"AI Response Error: {str(e)}")
        print(f"Full traceback: {traceback.format_exc()}")
        
        # Return a test response with thinking tags for debugging and empty debug info
        error_debug_info = {
            'turn_number': turn_number,
            'full_context': f"ERROR: {str(e)}",
            'agent_name': agent_profile_data.get('first_name', 'AI') if 'agent_profile_data' in locals() else 'AI',
            'transparency': transparency,
            'scenario_context': scenario_context if 'scenario_context' in locals() else "",
            'conversation_context': conversation_context if 'conversation_context' in locals() else "",
            'human_message': human_message,
            'ai_response': f"ERROR: {str(e)}"
        }
        
        if transparency == "high":
            return "<THINK>I'm having technical difficulties with the AI generation system. The validation error suggests the agent is returning malformed data instead of a proper string response.</THINK>I apologize, but I'm experiencing some technical difficulties right now. Please try again.", error_debug_info
        else:
            return "I'm sorry, I'm having trouble responding right now.", error_debug_info


def get_ai_response(human_message: str, agent_profile_data: dict, transparency: str, turn_number: int, conversation_context: str = "", scenario_context: str = "", model_name: str = "gpt-4o") -> str:
    """Sync wrapper for async AI response function"""
    try:
        # Simplified approach - just use asyncio.run in a thread
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(
                asyncio.run, 
                get_ai_response_async(human_message, agent_profile_data, transparency, turn_number, conversation_context, scenario_context, model_name)
            )
            result_tuple = future.result(timeout=60)  # 60 second timeout
            
            # Handle tuple return (result, debug_info)
            if isinstance(result_tuple, tuple) and len(result_tuple) == 2:
                result, debug_info = result_tuple
                
                # Store debug information in session state (main thread)
                if 'debug_prompt_info' not in st.session_state:
                    st.session_state.debug_prompt_info = []
                
                st.session_state.debug_prompt_info.append(debug_info)
                debug_count = len(st.session_state.debug_prompt_info)
                print(f"DEBUG SYNC: Stored debug info for turn {turn_number}. Total count: {debug_count}")
                
                return result
            else:
                # Fallback for unexpected return format
                print(f"DEBUG SYNC: Unexpected return format: {type(result_tuple)}")
                return str(result_tuple)
            
    except Exception as e:
        st.error(f"Error in get_ai_response: {str(e)}")
        import traceback
        st.error(f"Full traceback: {traceback.format_exc()}")
        print(f"get_ai_response Error: {str(e)}")
        print(f"get_ai_response traceback: {traceback.format_exc()}")
        return "I'm sorry, I'm having trouble responding right now."


def save_conversation_to_redis(conversation_history: list, interventions: dict, scenario_choice: str, agent_choice: str, prolific_params: dict = None, survey_responses: dict = None) -> str:
    """Save conversation data to Redis database as EpisodeLog with enhanced agent attributes"""
    try:
        # Generate unique session ID
        session_id = f"user_study_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid4())[:8]}"
        
        # Format messages for EpisodeLog (turn-based structure)
        formatted_messages = []
        current_turn = []
        
        for message in conversation_history:
            speaker = message.get('speaker', 'Unknown')
            content = message.get('content', '')
            action_type = message.get('action_type', 'speak')
            
            # Format: (agent_name, action_type, content)
            current_turn.append((speaker, action_type, content))
            
            # Each turn contains one message (matching the simulation system)
            formatted_messages.append(current_turn)
            current_turn = []
        
        # Get agent profile data for enhanced storage
        agent_profile_data = st.session_state.agent_dict.get(agent_choice, {})
        
        # Enhanced reasoning with comprehensive intervention data and agent attributes
        enhanced_reasoning = {
            "study_type": "user_study_human_ai_conversation",
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "interventions": interventions,
            "scenario_id": scenario_choice,
            "agent_id": agent_choice,
            "agent_attributes": {
                "name": f"{agent_profile_data.get('first_name', '')} {agent_profile_data.get('last_name', '')}".strip(),
                "occupation": get_scenario_occupation(scenario_choice),
                "age": agent_profile_data.get('age', ''),
                "decision_making_style": agent_profile_data.get('decision_making_style', ''),
                "big_five": agent_profile_data.get('big_five', ''),
                "mbti": agent_profile_data.get('mbti', ''),
            },
            "conversation_stats": {
                "total_turns": len(conversation_history),
                "human_messages": len([msg for msg in conversation_history if msg.get('speaker') == 'Human']),
                "ai_messages": len([msg for msg in conversation_history if msg.get('speaker') != 'Human']),
                "avg_message_length": sum(len(msg.get('content', '')) for msg in conversation_history) / len(conversation_history) if conversation_history else 0
            },
            "prolific_data": prolific_params if prolific_params else {},
            "survey_responses": survey_responses if survey_responses else {},
            "personality_assessment": st.session_state.get("personality_data", {})
        }
        
        # Create structured model tags that include all intervention dimensions
        model_tags = []
        for dimension, value in interventions.items():
            model_tags.append(f"{dimension}_{value}")
        model_tags.append("human")
        
        # Create episode log with enhanced data
        episode_log = EpisodeLog(
            environment=scenario_choice,
            agents=[agent_choice, "human_participant"],  # AI agent + human
            tag=f"user_study_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{session_id.split('_')[-1]}",
            models=model_tags,  # Now includes all intervention dimensions
            messages=formatted_messages,
            reasoning=json.dumps(enhanced_reasoning, indent=2),  # Structured JSON with all details
            rewards=[0.0, 0.0]  # Placeholder rewards
        )
        
        # Save to Redis
        episode_log.save()
        st.success(f"✅ Conversation saved to database with ID: {episode_log.pk}")
        
        # Store EnvAgentCombo for easier querying
        try:
            from sotopia.database import EnvAgentComboStorage
            env_agent_combo = EnvAgentComboStorage(
                env_id=scenario_choice,
                agent_ids=[agent_choice, "human_participant"]
            )
            env_agent_combo.save()
        except Exception as combo_error:
            # Don't fail the main save if EnvAgentCombo fails
            print(f"Warning: Could not save EnvAgentCombo: {combo_error}")
        
        return episode_log.pk
        
    except Exception as e:
        st.error(f"❌ Failed to save to database: {str(e)}")
        import traceback
        st.error(f"Traceback: {traceback.format_exc()}")
        return ""


def export_conversation_to_files(conversation_history: list, interventions: dict, scenario_choice: str, agent_choice: str, session_id: str = None) -> None:
    """Export conversation data to local CSV and JSON files"""
    try:
        if not session_id:
            session_id = f"user_study_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid4())[:8]}"
        
        # Create exports directory if it doesn't exist
        export_dir = "/tmp/sotopia_user_study_exports"
        os.makedirs(export_dir, exist_ok=True)
        
        # Prepare data for export
        export_data = {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "scenario": scenario_choice,
            "ai_agent": agent_choice,
            "interventions": interventions,
            "conversation": conversation_history,
            "total_turns": len(conversation_history),
            "conversation_length_minutes": None  # Could be calculated if we track timestamps
        }
        
        # Export to JSON
        json_file = f"{export_dir}/{session_id}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        # Export to CSV
        csv_file = f"{export_dir}/{session_id}.csv"
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write header
            writer.writerow([
                "session_id", "timestamp", "scenario", "ai_agent", "transparency", 
                "warmth", "expertise", "adaptability", "theory_of_mind",
                "turn_number", "speaker", "action_type", "content"
            ])
            
            # Write conversation data
            for turn_num, message in enumerate(conversation_history, 1):
                writer.writerow([
                    session_id,
                    datetime.now().isoformat(),
                    scenario_choice,
                    agent_choice,
                    interventions.get('transparency', 'low'),
                    interventions.get('warmth', 'low'),
                    interventions.get('expertise', 'high'),
                    interventions.get('adaptability', 'high'),
                    interventions.get('theory_of_mind', 'high'),
                    turn_num,
                    message.get('speaker', 'Unknown'),
                    message.get('action_type', 'speak'),
                    message.get('content', '')
                ])
        
        st.success(f"✅ Conversation exported to files:")
        st.info(f"📄 JSON: {json_file}")
        st.info(f"📊 CSV: {csv_file}")
        
        # Provide download buttons
        with open(json_file, 'r') as f:
            st.download_button(
                label="📥 Download JSON",
                data=f.read(),
                file_name=f"{session_id}.json",
                mime="application/json"
            )
        
        with open(csv_file, 'r') as f:
            st.download_button(
                label="📥 Download CSV", 
                data=f.read(),
                file_name=f"{session_id}.csv",
                mime="text/csv"
            )
            
    except Exception as e:
        st.error(f"❌ Failed to export files: {str(e)}")


def find_matching_agent(interventions: dict, agent_dict: dict) -> str:
    """Find agent profile that matches intervention dimensions (simplified without personality balancing)"""
    
    # Find all agents that match the intervention pattern
    target_transparency = interventions.get("transparency", "low").title()  # "High" or "Low"
    target_warmth = interventions.get("warmth", "low").title()
    target_expertise = interventions.get("expertise", "high").title()  
    target_adaptability = interventions.get("adaptability", "high").title()
    target_theory_of_mind = interventions.get("theory_of_mind", "high").title()
    
    # Build target pattern to match in personality_and_values
    target_pattern = f"{target_transparency} Transparency, {target_warmth} Warmth, {target_adaptability} Adaptability, {target_expertise} Expertise, {target_theory_of_mind} Theory of Mind"
    
    # Find all matching agents
    matching_agents = []
    for agent_key, agent_data in agent_dict.items():
        personality = agent_data.get("personality_and_values", "")
        if target_pattern in personality:
            matching_agents.append(agent_key)
    
    # If no agents match the pattern, fall back to all agents
    if not matching_agents:
        print(f"DEBUG: No matching agents found for pattern: {target_pattern}")
        matching_agents = list(agent_dict.keys())
    
    print(f"DEBUG: Found {len(matching_agents)} matching agents for pattern")
    
    # Simple selection: return first matching agent
    selected_agent = matching_agents[0]
    print(f"DEBUG: Selected agent: {selected_agent}")
    print(f"DEBUG: Target pattern: {target_pattern}")
    
    return selected_agent


def initialize_simple_session_state() -> None:
    """Initialize session state for simple user study"""
    # Initialize API_BASE if not already set
    if "API_BASE" not in st.session_state:
        DEFAULT_BASE = "sotopia-lab--sotopia-fastapi-webapi-serve.modal.run"
        st.session_state.API_BASE = f"https://{DEFAULT_BASE}"
        st.session_state.WS_BASE = f"ws://{DEFAULT_BASE}"
    
    # Initialize API key check
    if "api_key_set" not in st.session_state:
        st.session_state.api_key_set = os.getenv("OPENAI_API_KEY") is not None
    
    if "conversation_history" not in st.session_state:
        st.session_state.conversation_history = []
        st.session_state.turn_number = 0
        st.session_state.study_active = False
        st.session_state.agent_instance = None  # Will hold the agent instance
        st.session_state.survey_completed = False
        st.session_state.survey_responses = {}
        st.session_state.generating_response = False  # Track AI response generation state
        st.session_state.debug_prompt_info = []  # Initialize debug prompt storage
        
        # Load data from local files
        st.session_state.scenarios = load_local_scenarios()
        st.session_state.agent_dict = load_local_agents()
        st.session_state.agent_model_dict = get_models_local()
        
        # All five intervention dimensions from URL parameters (support both long and short forms)
        st.session_state.interventions = {
            "transparency": st.query_params.get("transparency", st.query_params.get("t", "high")).lower(),  # t or transparency
            "warmth": st.query_params.get("warmth", st.query_params.get("w", "high")).lower(),              # w or warmth  
            "expertise": st.query_params.get("expertise", st.query_params.get("e", "high")).lower(),       # e or expertise
            "adaptability": st.query_params.get("adaptability", st.query_params.get("a", "high")).lower(), # a or adaptability
            "theory_of_mind": st.query_params.get("theory_of_mind", st.query_params.get("tom", "high")).lower() # tom or theory_of_mind
        }
        
        # Extract Prolific parameters if available
        st.session_state.prolific_params = {
            "PROLIFIC_PID": st.query_params.get("PROLIFIC_PID"),
            "STUDY_ID": st.query_params.get("STUDY_ID"),
            "SESSION_ID": st.query_params.get("SESSION_ID")
        }
        
        # Scenario mapping for user-friendly URLs
        scenario_mapping = {
            "hiring_competitive": "job_interview_competitive",
            "hiring_cooperative": "job_interview_cooperative", 
            "travel_restrictions": "[ai-liedar] 0612_all_exp2_public_image_paraphrase_0_20",
            "laptop_shopping": "[ai-liedar] 0612_all_exp2_benefits_need_paraphrase_0_13",
            "business_collab": "[ai-liedar] 0612_all_exp2_emotion_paraphrase_0_19"
        }
        
        # Pre-configured study settings with scenario mapping
        scenario_param = st.query_params.get("scenario", st.query_params.get("s", "hiring_competitive"))
        # Map user-friendly name to actual codename, fallback to direct lookup if not in mapping
        st.session_state.scenario_choice = scenario_mapping.get(scenario_param, scenario_param)
        
        # Validate scenario exists, fallback to first available if not found
        if st.session_state.scenario_choice not in st.session_state.scenarios:
            st.session_state.scenario_choice = list(st.session_state.scenarios.keys())[0]
        
        # Check if personality assessment should be used (URL parameter or session state)
        use_personality_assessment = st.query_params.get("survey", "false").lower() == "true"
        personality_classification = None
        
        # Initialize personality_classification in session state
        if "personality_classification" not in st.session_state:
            st.session_state.personality_classification = None
        
        # Generate or get participant ID for personality tracking
        if "participant_id" not in st.session_state:
            st.session_state.participant_id = st.query_params.get("participant_id") or str(uuid4())
        
        # Load existing personality assessment if available
        if PersonalityAssessmentTracker:
            try:
                assessment_data = PersonalityAssessmentTracker.get_assessment(st.session_state.participant_id)
                if assessment_data:
                    # Handle both old and new data formats
                    scores = assessment_data.get("scores") or assessment_data.get("personality_scores")
                    if scores:
                        personality_classification = classify_personality(
                            scores["extroversion"], scores["agreeableness"]
                        )
                        st.session_state.personality_data = {
                            "participant_id": st.session_state.participant_id,
                            "scores": scores,
                            "classification": personality_classification
                        }
                        
                        # Load personality responses if available
                        personality_responses = assessment_data.get("responses") or assessment_data.get("personality_responses")
                        if personality_responses:
                            st.session_state.assessment_responses = personality_responses
                            
                        # Load pre-study responses if available
                        prestudy_responses = assessment_data.get("prestudy_responses")
                        if prestudy_responses:
                            st.session_state.prestudy_responses = prestudy_responses
                        
                        print(f"DEBUG: Loaded existing assessment data for participant {st.session_state.participant_id}")
                        print(f"DEBUG: Personality classification: {personality_classification}")
            except Exception as e:
                print(f"DEBUG: Error loading personality assessment: {e}")
        
        # Auto-select agent based on intervention dimensions only
        st.session_state.agent_choice_1 = find_matching_agent(
            st.session_state.interventions, 
            st.session_state.agent_dict
        )
        
        # Store personality classification for later assignment recording (after survey completion)
        st.session_state.personality_classification = personality_classification or None
        
        # Store assessment requirement for flow control
        st.session_state.requires_personality_assessment = use_personality_assessment
        
        st.session_state.max_turns = 20  # Maximum conversation turns
        
        # Backward compatibility for transparency
        st.session_state.show_ai_thinking = st.session_state.interventions["transparency"] == "high"


def display_user_role_simple() -> None:
    """Display the user's scenario and goal"""
    if st.session_state.scenario_choice in st.session_state.scenarios:
        current_scenario = st.session_state.scenarios[st.session_state.scenario_choice]
        
        # Debug info (only for researchers, not participants)
        participant_mode_debug = st.query_params.get("participant", st.query_params.get("p", "false")).lower() == "true"
        if not participant_mode_debug and st.sidebar.checkbox("Show Debug Info", value=False):
            st.sidebar.write("**Scenario Data Structure:**")
            st.sidebar.json(current_scenario)
        
        # Display your goal (Human user's goal - what they should accomplish)
        st.markdown("### 🎯 **Your Goal**")
        
        if 'agent_goals' in current_scenario and len(current_scenario['agent_goals']) >= 2:
            # Determine correct goal index based on scenario type
            if current_scenario.get('codename', '').startswith('[ai-liedar]'):
                user_goal = current_scenario['agent_goals'][0]  # Human goal for ai-liedar scenarios
            else:
                user_goal = current_scenario['agent_goals'][1]  # Human goal for hiring scenarios
            
            # Clean and format the goal text using utility function
            clean_goal = clean_and_format_goal_text(user_goal)
            
            if clean_goal:
                # Check if this is a job negotiation scenario
                scenario_codename = current_scenario.get('codename', '')
                is_job_negotiation = 'job_interview' in scenario_codename
                
                # Apply common text formatting using utility function
                clean_goal = add_text_formatting(clean_goal)
                
                if is_job_negotiation:
                    # Format text for job negotiation scenarios using utility function
                    formatted_goal = format_job_negotiation_text(clean_goal)
                    
                    # Display formatted text in styled container
                    st.markdown(create_styled_container(formatted_goal), unsafe_allow_html=True)
                    
                    # Display both charts side-by-side below the text
                    st.markdown("#### **Point Values**")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        generate_inline_salary_chart(clean_goal, current_scenario.get('codename', ''))
                    
                    with col2:
                        generate_inline_date_chart(clean_goal, current_scenario.get('codename', ''))
                    
                else:
                    # Format text for non-job scenarios using utility function
                    formatted_goal = format_non_job_text(clean_goal)
                    
                    # Display formatted text in styled container
                    st.markdown(create_styled_container(formatted_goal), unsafe_allow_html=True)
            else:
                st.warning("No task goal found - this scenario may not be suitable for user studies")
        else:
            st.warning("No goal information available for this scenario")
        
        # Add instruction about ending the conversation
        st.markdown("""
        <div style="
            background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
            border: 2px solid #2196f3;
            border-radius: 8px;
            padding: 15px;
            margin: 16px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        ">
            <div style="font-size: 16px; line-height: 1.6; color: #1565c0; text-align: center;">
                <strong>📋 Important:</strong> End the conversation when you feel you have achieved your stated goal or when you believe no further progress can be made.
            </div>
        </div>
        """, unsafe_allow_html=True)
        


def display_conversation_history():
    """Display the conversation history"""
    if st.session_state.conversation_history:
        st.markdown("### 💬 **Conversation**")
        
        for i, message in enumerate(st.session_state.conversation_history):
            speaker = message.get('speaker', 'Unknown')
            content = message.get('content', '')
            action_type = message.get('action_type', 'speak')
            
            if speaker == 'Human':
                with st.chat_message("user"):
                    st.write(f"**You**: {content}")
            else:
                with st.chat_message("assistant"):
                    if st.session_state.show_ai_thinking and '<THINK>' in content:
                        # Show AI thinking if transparency is enabled
                        thinking_match = re.search(r'<THINK>(.*?)</THINK>', content, re.DOTALL)
                        if thinking_match:
                            thinking = thinking_match.group(1).strip()
                            final_response = re.sub(r'<THINK>.*?</THINK>', '', content, flags=re.DOTALL).strip()
                            
                            st.info("🤔 **AI's thinking process:**\n\n" + thinking)
                            st.write(f"**{speaker}**: {final_response}")
                        else:
                            st.write(f"**{speaker}**: {content}")
                    else:
                        # Hide thinking tags
                        clean_content = re.sub(r'<THINK>.*?</THINK>', '', content, flags=re.DOTALL).strip()
                        st.write(f"**{speaker}**: {clean_content}")


def simulate_ai_response(human_message: str) -> str:
    """Get AI response using the actual agent with transparency settings and scenario context"""
    try:
        # Get the selected agent data
        agent_profile_data = st.session_state.agent_dict[st.session_state.agent_choice_1]
        
        # Map transparency intervention to transparency level
        transparency_level = st.session_state.interventions.get("transparency", "low")
        
        # Get model name (you can configure this)
        model_name = "gpt-4o"  # Default model, can be made configurable
        
        # Extract scenario context and AI agent's goal
        scenario_context = ""
        ai_agent_goal = ""
        
        if (st.session_state.scenario_choice in st.session_state.scenarios):
            current_scenario = st.session_state.scenarios[st.session_state.scenario_choice]
            scenario_description = current_scenario.get('scenario', '')
            agent_goals = current_scenario.get('agent_goals', [])
            
            if len(agent_goals) >= 2:
                # Determine correct goal index based on scenario type  
                if current_scenario.get('codename', '').startswith('[ai-liedar]'):
                    ai_agent_goal = agent_goals[1]  # AI goal for ai-liedar scenarios
                else:
                    ai_agent_goal = agent_goals[0]  # AI goal for hiring scenarios
                
                # Clean the AI agent's goal (remove strategy hints but keep extra_info)
                clean_ai_goal = re.sub(r'<strategy_hint>.*?</strategy_hint>', '', ai_agent_goal, flags=re.DOTALL)
                clean_ai_goal = clean_ai_goal.strip()
                
                # Get AI agent's occupation for this scenario
                ai_occupation = get_scenario_occupation(st.session_state.scenario_choice)
                
                # Build scenario context similar to ScriptBackground format
                scenario_context = f"""Here is the context of this interaction:
Scenario: {scenario_description}
Your role: {ai_occupation}
Your goal: {clean_ai_goal}

"""
        
        # Build conversation context from history
        conversation_context = ""
        for msg in st.session_state.conversation_history:
            speaker = msg.get('speaker', 'Unknown')
            content = msg.get('content', '')
            conversation_context += f"{speaker}: {content}\n"
        
        # Get current turn number
        current_turn = st.session_state.turn_number + 1
        
        # Get AI response with enhanced context
        response = get_ai_response(
            human_message=human_message,
            agent_profile_data=agent_profile_data,
            transparency=transparency_level,
            turn_number=current_turn,
            conversation_context=conversation_context.strip(),
            scenario_context=scenario_context,
            model_name=model_name
        )
        
        # Reset loading state before returning
        st.session_state.generating_response = False
        return response
        
    except Exception as e:
        # Reset loading state on error
        st.session_state.generating_response = False
        st.error(f"Error getting AI response: {str(e)}")
        import traceback
        st.error(f"Full traceback: {traceback.format_exc()}")
        return "I apologize, but I'm having trouble responding right now. Please try again."


# display_post_study_survey function imported from ui.surveys.questions


def display_debug_prompts() -> None:
    """Display debug information about prompts sent to AI agent"""
    # Debug logging
    debug_exists = 'debug_prompt_info' in st.session_state
    debug_count = len(st.session_state.debug_prompt_info) if debug_exists else 0
    print(f"DEBUG DISPLAY: debug_prompt_info exists: {debug_exists}, count: {debug_count}")
    
    if not debug_exists or not st.session_state.debug_prompt_info:
        st.info("No debug information available yet. Start a conversation to see prompt details.")
        st.write(f"**Debug status**: Session state has debug_prompt_info: {debug_exists}, Count: {debug_count}")
        return
    
    st.markdown("### 🔍 **Debug: AI Agent Prompts**")
    
    for i, debug_info in enumerate(st.session_state.debug_prompt_info):
        with st.expander(f"Turn {debug_info['turn_number']}: {debug_info['agent_name']} ({debug_info['transparency']} transparency)"):
            
            # Show full context sent to AI
            st.markdown("**Full Context Sent to AI:**")
            st.code(debug_info['full_context'], language="text")
            
            # Show AI response
            st.markdown("**AI Response:**")
            st.write(debug_info['ai_response'])
            
            # Show breakdown
            st.markdown("**Context Breakdown:**")
            col1, col2 = st.columns(2)
            
            with col1:
                if debug_info['scenario_context']:
                    st.markdown("**Scenario Context:**")
                    st.code(debug_info['scenario_context'], language="text")
                
                st.markdown("**Human Message:**")  
                st.code(debug_info['human_message'], language="text")
            
            with col2:
                if debug_info['conversation_context']:
                    st.markdown("**Conversation History:**")
                    st.code(debug_info['conversation_context'], language="text")
                else:
                    st.info("No conversation history yet")


def simple_user_study_interface() -> None:
    """Simple user study interface with manual conversation flow"""
    initialize_simple_session_state()
    
    # Force page to start at top and create clear starting point
    st.markdown("<!-- Page Start -->", unsafe_allow_html=True)
    
    # Add scroll control and ensure page starts at top
    st.markdown("""
    <script>
    // Force scroll to top when page loads
    window.onload = function() {
        window.scrollTo(0, 0);
    };
    // Also scroll to top on any page interaction
    document.addEventListener('DOMContentLoaded', function() {
        window.scrollTo(0, 0);
    });
    </script>
    """, unsafe_allow_html=True)
    
    # Hide sidebar and navigation for participants (do this first!)
    participant_mode = st.query_params.get("participant", st.query_params.get("p", "false")).lower() == "true"
    if participant_mode:
        st.markdown("""
        <style>
        /* Hide sidebar */
        section[data-testid="stSidebar"] {display: none !important;}
        
        /* Hide navigation bar and all related elements */
        nav[data-testid="stNavigation"] {display: none !important;}
        div[data-testid="stPageNavigation"] {display: none !important;}
        div[data-testid="stSidebarNav"] {display: none !important;}
        .st-emotion-cache-1gwvy71 {display: none !important;}
        .st-emotion-cache-16txtl3 {display: none !important;}
        
        /* Hide any header navigation */
        header[data-testid="stHeader"] {display: none !important;}
        
        /* Adjust main content area - wider for better radio button layout */
        .main .block-container {
            padding-left: 2rem !important; 
            padding-right: 2rem !important;
            max-width: 850px !important;
            margin: 0 auto !important;
        }
        
        /* Target all content containers */
        .block-container {
            max-width: 850px !important;
            margin: 0 auto !important;
        }
        
        /* Keep radio buttons in vertical layout but prevent text wrapping within each option */
        div[data-testid="stRadio"] > div {
            flex-direction: column !important;
            align-items: flex-start !important;
        }
        
        /* Ensure radio button text doesn't wrap within each option and left align */
        div[data-testid="stRadio"] label {
            white-space: nowrap !important;
            text-align: left !important;
            justify-content: flex-start !important;
        }
        
        /* Left align the radio button container */
        div[data-testid="stRadio"] {
            text-align: left !important;
        }
        
        /* Make survey question text larger and more prominent */
        .main .block-container p strong {
            font-size: 1.1rem !important;
            font-weight: 600 !important;
            color: #262730 !important;
            margin-bottom: 0.5rem !important;
        }
        
        /* Reduce space between question text and radio buttons */
        .main .block-container p {
            margin-bottom: 0.3rem !important;
        }
        
        /* Reduce space above radio buttons */
        div[data-testid="stRadio"] {
            margin-top: -0.5rem !important;
            margin-bottom: 1rem !important;
        }
        
        /* Ensure info boxes and text are also narrow */
        .stAlert {
            max-width: 100% !important;
        }
        .stApp > div:first-child {margin-left: 0 !important;}
        
        /* Legacy CSS classes */
        .css-1d391kg {display: none !important;}
        .css-1y4p8pa {padding-left: 1rem !important;}
        .css-1lcbmhc {display: none !important;}
        .css-1outpf7 {display: none !important;}
        .css-164nlkn {display: none !important;}
        </style>
        """, unsafe_allow_html=True)
    
    # Apply focused width only for non-participant mode (researchers)
    if not participant_mode:
        st.markdown("""
        <style>
        .main .block-container {
            max-width: 700px !important;
            margin: 0 auto !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
        }
        </style>
        """, unsafe_allow_html=True)
    
    # Show consent form first for participants
    if participant_mode and not st.session_state.get("consent_given", False):
        st.title("📋 Research Study Consent Form")
        
        st.markdown(CONSENT_FORM_TEXT)
        
        consent_given = st.checkbox(
            "**I have read and understood the information above, am 18 years or older, in the United States, and agree to participate in this study.**",
            key="consent_checkbox"
        )
        
        if consent_given:
            if st.button("Continue to Study", type="primary", use_container_width=True):
                st.session_state.consent_given = True
                st.rerun()
        else:
            st.warning("⚠️ You must check the consent box to continue the study.")
            st.button("Continue to Study", disabled=True, use_container_width=True)
        
        st.info("💡 If you do not consent, you may close this window.")
        return  # Stop here until consent is given
    
    # Check if personality assessment is required and not yet completed
    # BUT only block for participants, not researchers
    if (st.session_state.get("requires_personality_assessment", False) and 
        not st.session_state.get("personality_data") and 
        participant_mode):  # Only block participants, not researchers
        
        # Personality assessment functions are now defined above in this file
        
        # Initialize assessment session state if needed
        if "assessment_responses" not in st.session_state:
            st.session_state.assessment_responses = {}
        if "prestudy_responses" not in st.session_state:
            st.session_state.prestudy_responses = {}
        
        st.title("📋 Pre-Study Survey")
        st.info("""
        Before starting the conversation, please complete this brief survey.
        
        Please answer honestly based on your experiences and opinions.
        """)
        
        # render_question function imported from ui.surveys.questions
        
        # Section 1: Personality Questions
        st.markdown("## Part 1: Personality Assessment")
        st.markdown("*For each statement, indicate how accurately it describes you.*")
        
        for q_num in sorted(PERSONALITY_QUESTIONS.keys()):
            question_data = PERSONALITY_QUESTIONS[q_num]
            render_question(q_num, question_data, "assessment_responses")
        
        # Section 2: AI Experience Questions
        st.markdown("## Part 2: AI Experience")
        st.markdown("*Please answer questions about your experience with conversational AI systems.*")
        
        for q_num in sorted(AI_EXPERIENCE_QUESTIONS.keys()):
            question_data = AI_EXPERIENCE_QUESTIONS[q_num]
            render_question(q_num, question_data, "prestudy_responses")
        
        # Section 3: AI Attitude Questions
        st.markdown("## Part 3: AI Attitudes")
        st.markdown("*Please rate your agreement with each statement about conversational AI systems (like ChatGPT, Claude, etc.):*")
        
        for q_num in sorted(AI_ATTITUDE_QUESTIONS.keys()):
            question_data = AI_ATTITUDE_QUESTIONS[q_num]
            render_question(q_num, question_data, "prestudy_responses")
        
        # Section 4: Trust and Negotiation Background
        st.markdown("## Part 4: Trust and Negotiation Background")
        st.markdown("*Please indicate your agreement with the following statements:*")
        
        for q_num in sorted(TRUST_NEGOTIATION_QUESTIONS.keys()):
            question_data = TRUST_NEGOTIATION_QUESTIONS[q_num]
            render_question(q_num, question_data, "prestudy_responses")
        
        # count_completed_responses function imported from ui.surveys.questions
        
        total_questions = (len(PERSONALITY_QUESTIONS) + len(AI_EXPERIENCE_QUESTIONS) + 
                          len(AI_ATTITUDE_QUESTIONS) + len(TRUST_NEGOTIATION_QUESTIONS))
        completed_personality = count_completed_responses(st.session_state.assessment_responses)
        completed_prestudy = count_completed_responses(st.session_state.prestudy_responses)
        completed_questions = completed_personality + completed_prestudy
        
        # Display progress
        progress = completed_questions / total_questions
        st.progress(progress)
        st.markdown(f"**Progress:** {completed_questions}/{total_questions} questions completed")
        
        # Submit button
        if completed_questions == total_questions:
            if st.button("Submit", type="primary", use_container_width=True):
                # Calculate scores
                scores = calculate_personality_scores(st.session_state.assessment_responses)
                classification = classify_personality(scores["extroversion"], scores["agreeableness"])
                
                # Save to session state
                st.session_state.personality_data = {
                    "participant_id": st.session_state.participant_id,
                    "scores": scores,
                    "classification": classification
                }
                
                # Save to database including pre-study responses
                assessment_id = PersonalityAssessmentTracker.save_assessment(
                    st.session_state.participant_id,
                    st.session_state.assessment_responses, 
                    scores,
                    st.session_state.prestudy_responses
                )
                
                if assessment_id:
                    st.success("✅ Assessment completed! Proceeding to the study...")
                    st.rerun()
                else:
                    st.error("Failed to save assessment. Please try again.")
        else:
            st.button("Submit", disabled=True, use_container_width=True)
            remaining = total_questions - completed_questions
            st.warning(f"Please complete all questions. {remaining} question(s) remaining.")
        
        return  # Stop here until assessment is completed (participants only)
    
    # Page header
    st.title("🔬 Human-AI Conversation Study")
    
    # Assignment balance dashboard removed (personality-based balancing disabled)
    
    # Check if in participant mode
    participant_mode = st.query_params.get("participant", st.query_params.get("p", "false")).lower() == "true"
    
    if not participant_mode:
        # Show researcher dashboard first
        st.markdown("## 🔍 **Researcher Dashboard**")
        st.markdown("Quick access to saved conversation data and exports.")
        
        # Database viewing section for researchers
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📊 Database Summary", use_container_width=True):
                try:
                    from ui.database_utils import print_database_summary
                    # Capture output in a string buffer
                    import io
                    import contextlib
                    
                    output_buffer = io.StringIO()
                    with contextlib.redirect_stdout(output_buffer):
                        print_database_summary()
                    
                    summary_text = output_buffer.getvalue()
                    st.text(summary_text)
                    
                except Exception as e:
                    st.error(f"Error accessing database: {str(e)}")
        
        with col2:
            if st.button("🔎 Browse Episodes", use_container_width=True):
                try:
                    from ui.database_utils import get_user_study_episodes, parse_episode_reasoning
                    
                    episodes = get_user_study_episodes()
                    
                    if episodes:
                        st.markdown(f"**Found {len(episodes)} user study episodes:**")
                        
                        # Create a selectbox for episode details
                        episode_options = {}
                        for ep in episodes[-20:]:  # Show last 20 episodes
                            episode_data = parse_episode_reasoning(ep)
                            interventions = episode_data.get('interventions', {})
                            transparency = interventions.get('transparency', 'unknown')
                            turns = len(ep.messages)
                            label = f"{ep.pk[:12]}... | {transparency} | {turns} turns | {ep.tag}"
                            episode_options[label] = ep.pk
                        
                        if episode_options:
                            selected_label = st.selectbox("Select episode to view details:", list(episode_options.keys()))
                            selected_episode_id = episode_options[selected_label]
                            
                            if st.button("View Episode Details"):
                                # Show detailed episode information
                                from ui.database_utils import view_episode_details
                                import io
                                import contextlib
                                
                                output_buffer = io.StringIO()
                                with contextlib.redirect_stdout(output_buffer):
                                    view_episode_details(selected_episode_id)
                                
                                details_text = output_buffer.getvalue()
                                st.text(details_text)
                    else:
                        st.warning("No user study episodes found in database")
                        
                except Exception as e:
                    st.error(f"Error browsing episodes: {str(e)}")
        
        with col3:
            try:
                from ui.database_utils import get_user_study_episodes, export_episodes_to_enhanced_csv, export_episodes_to_enhanced_json
                
                episodes = get_user_study_episodes()
                
                if episodes:
                    st.markdown(f"**Found {len(episodes)} episodes**")
                    
                    # Show export options outside the button
                    export_format = st.radio("Export format:", ["CSV (for analysis)", "JSON (complete data)"], key="export_format_radio")
                    
                    if st.button("💾 Export Now", key="export_db", use_container_width=True):
                        if "CSV" in export_format:
                            filename = export_episodes_to_enhanced_csv(episodes)
                            st.success(f"✅ Exported to CSV: {filename}")
                            
                            # Provide download
                            with open(filename, 'r', encoding='utf-8') as f:
                                st.download_button(
                                    label="📥 Download CSV",
                                    data=f.read(),
                                    file_name=os.path.basename(filename),
                                    mime="text/csv",
                                    key="download_csv"
                                )
                        else:
                            filename = export_episodes_to_enhanced_json(episodes)
                            st.success(f"✅ Exported to JSON: {filename}")
                            
                            # Provide download
                            with open(filename, 'r', encoding='utf-8') as f:
                                st.download_button(
                                    label="📥 Download JSON",
                                    data=f.read(),
                                    file_name=os.path.basename(filename),
                                    mime="application/json",
                                    key="download_json"
                                )
                else:
                    st.warning("No episodes found to export")
                    st.button("💾 Export Database", disabled=True, use_container_width=True)
                    
            except Exception as e:
                st.error(f"Error with database export: {str(e)}")
                st.button("💾 Export Database", disabled=True, use_container_width=True)
        
        st.markdown("## 👥 **User Study Interface**")
        st.markdown("Use the interface below to test the user study flow or conduct actual sessions.")
    
    else:
        st.markdown("Welcome to our research study! Please read your role carefully and engage naturally in the conversation.")
    
    # Display role information
    display_user_role_simple()
    
    st.markdown("---")
    
    # Conversation area - always show input interface
    # Display conversation history if it exists
    if st.session_state.conversation_history:
        display_conversation_history()
        st.markdown("---")
    
    # Debug sections for researchers - moved outside conversation area for better accessibility
    participant_mode = st.query_params.get("participant", st.query_params.get("p", "false")).lower() == "true"
    if not participant_mode:
        col1, col2 = st.columns(2)
        with col1:
            with st.expander("🔧 Agent Selection Details (Debug)", expanded=False):
                st.markdown("**URL Intervention Dimensions:**")
                st.json(st.session_state.interventions)
                st.markdown("**Selected Agent Profile:**")
                st.markdown(f"Agent Key: `{st.session_state.agent_choice_1}`")
                st.markdown(f"Intervention Mapping: {st.session_state.interventions}")
        
        with col2:
            with st.expander("🔍 AI Agent Prompts (Debug)", expanded=False):
                display_debug_prompts()
        
        st.markdown("---")
    
    # Combined AI agent info and conversation input area
    if not st.session_state.conversation_history:
        # Show AI agent info and conversation starter
        if st.session_state.agent_choice_1 in st.session_state.agent_dict:
            ai_agent = st.session_state.agent_dict[st.session_state.agent_choice_1]
            st.markdown("### 💬 **Start the Conversation**")
            # Get dynamic occupation based on scenario
            scenario_occupation = get_scenario_occupation(st.session_state.scenario_choice)
            st.markdown(f"You will be conversing with an AI agent (**{scenario_occupation}**). Type your message below to begin.")
        else:
            st.markdown("### 💬 **Start the Conversation**")
    else:
        st.markdown("### 💬 **Your Response**")
    
    # Disable text input during AI response generation
    placeholder_text = "AI is generating response..." if st.session_state.generating_response else "Type what you want to say..."
    
    human_input = st.text_area(
        label="Your message", 
        placeholder=placeholder_text,
        height=100,
        key=f"human_input_{st.session_state.turn_number}",
        label_visibility="collapsed",
        disabled=st.session_state.generating_response
    )
    
    # Show buttons based on conversation state
    if not st.session_state.conversation_history:
        # Before conversation starts - only show Send Message button
        button_text = "Generating..." if st.session_state.generating_response else "Send Message"
        button_disabled = st.session_state.generating_response
        
        # Show loading indicator if generating
        if st.session_state.generating_response:
            with st.spinner("AI is thinking..."):
                st.empty()  # Placeholder for spinner
        
        # Check if we should be generating a response (state-based approach)
        if st.session_state.get('pending_message_1'):
            # We're in a state where we need to generate AI response
            human_message = st.session_state.pending_message_1
            st.session_state.pending_message_1 = None  # Clear the pending message
            
            # Start the conversation automatically on first message
            st.session_state.study_active = True
            st.session_state.turn_number = 0
            
            # Add human message to history
            st.session_state.conversation_history.append({
                'speaker': 'Human',
                'content': human_message,
                'action_type': 'speak'
            })
            
            # Generate AI response
            ai_response = simulate_ai_response(human_message)
            ai_name = st.session_state.agent_dict[st.session_state.agent_choice_1].get('first_name', 'AI')
            
            st.session_state.conversation_history.append({
                'speaker': ai_name,
                'content': ai_response,
                'action_type': 'speak'
            })
            
            st.session_state.turn_number += 1
            st.session_state.generating_response = False
            st.rerun()
        
        if st.button(button_text, type="primary", use_container_width=True, disabled=button_disabled):
            if human_input.strip():
                # Set up for generation on next run
                st.session_state.pending_message_1 = human_input.strip()
                st.session_state.generating_response = True
                st.rerun()
            else:
                st.error("Please enter a message")
    else:
        # After conversation has started - show both buttons
        
        # Show loading indicator if generating
        if st.session_state.generating_response:
            with st.spinner("AI is thinking..."):
                st.empty()  # Placeholder for spinner
        
        # Check if we should be generating a response (state-based approach)
        if st.session_state.get('pending_message_2'):
            # We're in a state where we need to generate AI response
            human_message = st.session_state.pending_message_2
            st.session_state.pending_message_2 = None  # Clear the pending message
            
            # Check if we've reached max turns (each message = 1 turn)
            if len(st.session_state.conversation_history) >= st.session_state.max_turns:
                st.warning(f"Maximum conversation turns ({st.session_state.max_turns}) reached. Conversation will end.")
                st.session_state.study_active = False
                st.success("Conversation ended due to turn limit. Thank you for participating!")
                st.session_state.generating_response = False
                st.rerun()
                return
            
            # Add human message to history
            st.session_state.conversation_history.append({
                'speaker': 'Human',
                'content': human_message,
                'action_type': 'speak'
            })
            
            # Generate AI response
            ai_response = simulate_ai_response(human_message)
            ai_name = st.session_state.agent_dict[st.session_state.agent_choice_1].get('first_name', 'AI')
            
            st.session_state.conversation_history.append({
                'speaker': ai_name,
                'content': ai_response,
                'action_type': 'speak'
            })
            
            st.session_state.turn_number += 1
            
            # Check if we've now reached max turns after AI response
            if len(st.session_state.conversation_history) >= st.session_state.max_turns:
                st.session_state.study_active = False
                # Note: Don't save here, wait for survey completion
            
            st.session_state.generating_response = False
            st.rerun()
        
        col1, col2 = st.columns([1, 1])
        with col1:
            button_text = "Generating..." if st.session_state.generating_response else "Send Message"
            button_disabled = st.session_state.generating_response
            
            if st.button(button_text, type="primary", disabled=button_disabled):
                if human_input.strip():
                    # Set up for generation on next run
                    st.session_state.pending_message_2 = human_input.strip()
                    st.session_state.generating_response = True
                    st.rerun()
                else:
                    st.error("Please enter a message")
        
        with col2:
            if st.button("End Conversation", type="secondary", disabled=st.session_state.generating_response):
                st.session_state.study_active = False
                # Note: Don't save here, wait for survey completion
    
    # Show conversation stats
    if st.session_state.conversation_history:
        st.markdown("---")
        turn_count = len(st.session_state.conversation_history)  # Each message = 1 turn
        st.markdown(f"**Conversation turns**: {turn_count}/{st.session_state.max_turns}")
    
    # Show post-study survey and completion flow
    if not st.session_state.study_active and st.session_state.conversation_history:
        if not st.session_state.survey_completed:
            # Show survey first
            st.markdown("---")
            survey_responses = display_post_study_survey()
            
            # Validate all questions are answered
            required_selectbox_questions = [
                'transparency', 'warmth', 'theory_of_mind', 'adaptability', 'expertise'
            ]
            required_slider_questions = [
                'goals', 'satisfaction', 'conflict_resolve', 'believability', 'transactivity', 'truthfulness'
            ]
            
            # Check selectbox questions
            missing_selectbox = [q for q in required_selectbox_questions if q not in survey_responses or survey_responses[q] is None]
            
            # Check slider interactions
            missing_sliders = [q for q in required_slider_questions if not st.session_state.slider_interactions.get(q, False)]
            
            missing_questions = missing_selectbox + missing_sliders
            
            if missing_questions:
                if missing_sliders:
                    st.error(f"⚠️ Please move all sliders and complete all questions before submitting. You need to interact with {len(missing_sliders)} slider(s) and complete {len(missing_selectbox)} dropdown(s).")
                else:
                    st.error(f"⚠️ Please complete all survey questions before submitting. Missing: {len(missing_questions)} question(s)")
                st.button("Submit Survey & Complete Study", disabled=True, use_container_width=True)
            else:
                if st.button("Submit Survey & Complete Study", type="primary", use_container_width=True):
                    # Save survey responses
                    st.session_state.survey_responses = survey_responses
                    st.session_state.survey_completed = True
                    
                    # Save everything to database with survey results (ONLY SAVE HAPPENS HERE)
                    try:
                        session_id = save_conversation_to_redis(
                            st.session_state.conversation_history,
                            st.session_state.interventions,
                            st.session_state.scenario_choice,
                            st.session_state.agent_choice_1,
                            st.session_state.get('prolific_params', {}),
                            survey_responses
                        )
                        
                        # Assignment recording removed (personality-based balancing disabled)
                        
                        if session_id:
                            st.session_state.saved_session_id = session_id
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error saving survey results: {str(e)}")
        else:
            # Show completion confirmation after survey
            participant_mode = st.query_params.get("participant", st.query_params.get("p", "false")).lower() == "true"
            if participant_mode:
                # Show Prolific ID for participants
                prolific_pid = st.session_state.get('prolific_params', {}).get('PROLIFIC_PID')
                if prolific_pid:
                    st.success("✅ Study completed successfully! Thank you for your participation.")
                    st.markdown(f"**Your Prolific ID:** `{prolific_pid}`")
                    st.markdown("You may now close this window and return to Prolific to complete your submission.")
                else:
                    st.success("✅ Study completed successfully! Thank you for your participation.")
            else:
                # Show session ID for researchers
                st.success("✅ Study completed and saved to database!")
                st.markdown(f"**Session ID:** `{st.session_state.saved_session_id}`")
        
        
        # Show comprehensive study configuration for transparency (only for researchers)
        if not participant_mode:
            with st.expander("📊 Study Configuration Details"):
                agent_profile_data = st.session_state.agent_dict.get(st.session_state.agent_choice_1, {})
                config_details = {
                    "scenario": st.session_state.scenario_choice,
                    "ai_agent": st.session_state.agent_choice_1,
                    "interventions": st.session_state.interventions,
                    "agent_attributes": {
                        "name": f"{agent_profile_data.get('first_name', '')} {agent_profile_data.get('last_name', '')}".strip(),
                        "occupation": get_scenario_occupation(st.session_state.scenario_choice),
                        "decision_making_style": agent_profile_data.get('decision_making_style', '')
                    },
                    "conversation_stats": {
                        "total_turns": len(st.session_state.conversation_history),
                        "human_messages": len([msg for msg in st.session_state.conversation_history if msg.get('speaker') == 'Human']),
                        "ai_messages": len([msg for msg in st.session_state.conversation_history if msg.get('speaker') != 'Human']),
                    },
                    "conversation_completed": not st.session_state.study_active
                }
                st.json(config_details)


# Run the simple user study interface
simple_user_study_interface()