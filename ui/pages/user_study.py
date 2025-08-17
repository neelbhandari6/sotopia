import streamlit as st
import json
import re
import csv
import os
import asyncio
from datetime import datetime
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


async def get_ai_response_async(human_message: str, agent_profile_data: dict, transparency: str, turn_number: int, conversation_context: str = "", model_name: str = "gpt-4o") -> str:
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
        
        # Create observation with conversation context
        available_actions = ["speak", "non-verbal communication", "leave"]
        
        # Build the context string that includes conversation history and current message
        full_context = f"{conversation_context}\nHuman: {human_message}" if conversation_context else f"Human: {human_message}"
        
        # Create observation from human message with context
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
        return result
        
    except Exception as e:
        st.error(f"Error getting AI response: {str(e)}")
        import traceback
        st.error(f"Full traceback: {traceback.format_exc()}")
        # Also log to console for debugging
        print(f"AI Response Error: {str(e)}")
        print(f"Full traceback: {traceback.format_exc()}")
        
        # Return a test response with thinking tags for debugging
        if transparency == "high":
            return "<THINK>I'm having technical difficulties with the AI generation system. The validation error suggests the agent is returning malformed data instead of a proper string response.</THINK>I apologize, but I'm experiencing some technical difficulties right now. Please try again."
        else:
            return "I'm sorry, I'm having trouble responding right now."


def get_ai_response(human_message: str, agent_profile_data: dict, transparency: str, turn_number: int, conversation_context: str = "", model_name: str = "gpt-4o") -> str:
    """Sync wrapper for async AI response function"""
    try:
        # Simplified approach - just use asyncio.run in a thread
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(
                asyncio.run, 
                get_ai_response_async(human_message, agent_profile_data, transparency, turn_number, conversation_context, model_name)
            )
            result = future.result(timeout=60)  # 60 second timeout
            print(f"DEBUG SYNC: Got result from async: {result[:100]}...")
            return result
            
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
                "occupation": agent_profile_data.get('occupation', ''),
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
            "survey_responses": survey_responses if survey_responses else {}
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
    """Find agent profile that matches the specified intervention dimensions"""
    target_transparency = interventions.get("transparency", "low").title()  # "High" or "Low"
    target_warmth = interventions.get("warmth", "low").title()
    target_expertise = interventions.get("expertise", "high").title()  
    target_adaptability = interventions.get("adaptability", "high").title()
    target_theory_of_mind = interventions.get("theory_of_mind", "high").title()
    
    # Build target pattern to match in personality_and_values
    target_pattern = f"{target_transparency} Transparency, {target_warmth} Warmth, {target_adaptability} Adaptability, {target_expertise} Expertise, {target_theory_of_mind} Theory of Mind"
    
    # Search through all agents to find matching personality
    for agent_key, agent_data in agent_dict.items():
        personality = agent_data.get("personality_and_values", "")
        if target_pattern in personality:
            print(f"DEBUG: Found matching agent: {agent_key}")
            print(f"DEBUG: Target pattern: {target_pattern}")
            print(f"DEBUG: Agent personality: {personality[:200]}...")
            return agent_key
    
    # If no exact match found, return first available agent
    print(f"DEBUG: No matching agent found for pattern: {target_pattern}")
    print(f"DEBUG: Available agents: {list(agent_dict.keys())}")
    return list(agent_dict.keys())[0]


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
        
        # Auto-select agent based on intervention dimensions
        st.session_state.agent_choice_1 = find_matching_agent(st.session_state.interventions, st.session_state.agent_dict)
        
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
        
        # Display your goal (Agent 2's goal - what they should accomplish)
        st.markdown("### 🎯 **Your Goal**")
        
        if 'agent_goals' in current_scenario and len(current_scenario['agent_goals']) >= 2:
            agent2_goal = current_scenario['agent_goals'][1]
            
            # Remove backstory and strategy hints, keep only the actual goal/task
            clean_goal = re.sub(r'<extra_info>.*?</extra_info>', '', agent2_goal, flags=re.DOTALL)
            clean_goal = re.sub(r'<strategy_hint>.*?</strategy_hint>', '', clean_goal, flags=re.DOTALL)
            clean_goal = clean_goal.strip()
            
            # Comprehensive text formatting fixes
            # Fix specific problematic patterns
            clean_goal = re.sub(r'(\d+),(\d+)gives', r'\1,\2 gives', clean_goal)  # "120,000gives" -> "120,000 gives"
            clean_goal = re.sub(r'(\d+)points', r'\1 points', clean_goal)  # "6000points" -> "6000 points"  
            clean_goal = re.sub(r'you(\d+)', r'you \1', clean_goal)  # "you6000" -> "you 6000"
            clean_goal = re.sub(r'(\d+)gives', r'\1 gives', clean_goal)  # "115000gives" -> "115000 gives"
            clean_goal = re.sub(r'points,(\$)', r'points, \1', clean_goal)  # "points,$" -> "points, $"
            clean_goal = re.sub(r'([a-z])(\d+)', r'\1 \2', clean_goal)  # Add space before numbers
            clean_goal = re.sub(r'(\d+)([a-z])', r'\1 \2', clean_goal)  # Add space after numbers
            clean_goal = re.sub(r'([a-z])([A-Z])', r'\1 \2', clean_goal)  # Add space between cases
            
            if clean_goal:
                # Enhanced formatting with highlighting for important sections
                formatted_goal = clean_goal
                
                # Add proper line breaks and section formatting
                # Break before major sections like "Salary:" and "Starting Date:"
                formatted_goal = re.sub(
                    r'\b(Salary|Starting Date|Start Date):', 
                    r'<br><br><strong style="color: #495057; font-size: 18px;">\1:</strong> ', 
                    formatted_goal, 
                    flags=re.IGNORECASE
                )
                
                # Add line breaks before sentences that start with key phrases
                formatted_goal = re.sub(
                    r'\s+(Your salary|Your starting date|These are the only)\b', 
                    r'<br>\1', 
                    formatted_goal, 
                    flags=re.IGNORECASE
                )
                
                # Add line breaks before "Do not" only when it starts a new sentence (after period)
                formatted_goal = re.sub(
                    r'\.\s+(Do not)', 
                    r'. <br>\1', 
                    formatted_goal, 
                    flags=re.IGNORECASE
                )
                
                # Add line breaks before "There are X different" patterns
                formatted_goal = re.sub(
                    r'\s+(There are \d+ different)', 
                    r'<br>\1', 
                    formatted_goal, 
                    flags=re.IGNORECASE
                )
                
                # Highlight [IMPORTANT] tags with strong visual emphasis
                formatted_goal = re.sub(
                    r'\[IMPORTANT\](.*?)(?=\[|$)', 
                    r'<div style="background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 8px 12px; margin: 8px 0; border-radius: 4px;"><strong>🚨 IMPORTANT:</strong> \1</div>', 
                    formatted_goal, 
                    flags=re.DOTALL
                )
                
                # Highlight "Your goal is to" sentences for specific scenarios
                formatted_goal = re.sub(
                    r'(Your goal is to[^.]*\.)', 
                    r'<div style="background-color: #e7f3ff; border-left: 4px solid #0d6efd; padding: 8px 12px; margin: 8px 0; border-radius: 4px;"><strong>🎯 \1</strong></div>', 
                    formatted_goal, 
                    flags=re.IGNORECASE
                )
                
                # Highlight numerical values (salary, points, etc.) with subtle grey background
                formatted_goal = re.sub(
                    r'(\$\d{1,3}(?:,\d{3})*|\d{1,3}(?:,\d{3})*\s*points?)', 
                    r'<strong style="background-color: #f8f9fa; padding: 2px 4px; border-radius: 3px;">\1</strong>', 
                    formatted_goal
                )
                
                # Highlight dates (June 1, July 15, etc.)
                formatted_goal = re.sub(
                    r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}\b', 
                    r'<strong style="background-color: #f8f9fa; padding: 2px 4px; border-radius: 3px;">\g<0></strong>', 
                    formatted_goal, 
                    flags=re.IGNORECASE
                )
                
                # Highlight key action words
                key_words = ['negotiate', 'convince', 'persuade', 'achieve', 'obtain', 'secure', 'maximize', 'minimize']
                for word in key_words:
                    formatted_goal = re.sub(
                        f'\\b({word})\\b', 
                        r'<strong style="color: #0d6efd;">\1</strong>', 
                        formatted_goal, 
                        flags=re.IGNORECASE
                    )
                
                # Use enhanced styling with better visual hierarchy
                st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                    border: 2px solid #dee2e6;
                    border-radius: 8px;
                    padding: 20px;
                    margin: 16px 0;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                ">
                    <div style="font-size: 16px; line-height: 1.6; color: #212529;">
                        {formatted_goal}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.warning("No task goal found - this scenario may not be suitable for user studies")
        else:
            st.warning("No goal information available for this scenario")
        


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
                            
                            with st.expander("🤔 AI's thinking process"):
                                st.write(thinking)
                            st.write(f"**{speaker}**: {final_response}")
                        else:
                            st.write(f"**{speaker}**: {content}")
                    else:
                        # Hide thinking tags
                        clean_content = re.sub(r'<THINK>.*?</THINK>', '', content, flags=re.DOTALL).strip()
                        st.write(f"**{speaker}**: {clean_content}")


def simulate_ai_response(human_message: str) -> str:
    """Get AI response using the actual agent with transparency settings"""
    try:
        # Get the selected agent data
        agent_profile_data = st.session_state.agent_dict[st.session_state.agent_choice_1]
        
        # Map transparency intervention to transparency level
        transparency_level = st.session_state.interventions.get("transparency", "low")
        
        # Get model name (you can configure this)
        model_name = "gpt-4o"  # Default model, can be made configurable
        
        # if st.session_state.interventions.get("transparency") == "high":
        #     return "<THINK>TEST: This is a manual thinking process to verify the display works.</THINK>Hello! This is a test response."
  
        # Build conversation context from history
        conversation_context = ""
        for msg in st.session_state.conversation_history:
            speaker = msg.get('speaker', 'Unknown')
            content = msg.get('content', '')
            conversation_context += f"{speaker}: {content}\n"
        
        # Get current turn number
        current_turn = st.session_state.turn_number + 1
        
        # Get AI response using the actual agent
        response = get_ai_response(
            human_message=human_message,
            agent_profile_data=agent_profile_data,
            transparency=transparency_level,
            turn_number=current_turn,
            conversation_context=conversation_context.strip(),
            model_name=model_name
        )
        
        return response
        
    except Exception as e:
        st.error(f"Error getting AI response: {str(e)}")
        import traceback
        st.error(f"Full traceback: {traceback.format_exc()}")
        return "I apologize, but I'm having trouble responding right now. Please try again."


def display_post_study_survey() -> dict:
    """Display post-study survey and return responses"""
    st.markdown("---")
    st.markdown("## 📋 **Post-Study Survey**")
    st.markdown("Please answer the following questions about your interaction with the AI agent.")
    
    survey_responses = {}
    
    # Initialize slider interaction tracking in session state
    if "slider_interactions" not in st.session_state:
        st.session_state.slider_interactions = {}
    
    # Add instruction for users about slider interaction
    st.info("📌 **Note**: Please click or drag each slider to indicate your response, even if you want to keep the default middle position.")
    
    # Manipulation Checks Section
    st.markdown("### **Manipulation Checks**")
    st.markdown("*Think about the AI agent you just interacted with. Please rate how well each statement describes the AI:*")
    st.markdown("**1 = Strongly disagree, 2 = Disagree, 3 = Neutral, 4 = Agree, 5 = Strongly agree**")
    
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
    
    # Add a confirmation button for midpoint selection
    col1, col2 = st.columns([3, 1])
    with col1:
        if st.session_state.slider_interactions.get("goals", False):
            st.caption("✅ 1 = Completely unsuccessful → 7 = Completely successful")
        else:
            st.caption("⏸️ 1 = Completely unsuccessful → 7 = Completely successful")
    with col2:
        if not st.session_state.slider_interactions.get("goals", False):
            if st.button("Confirm Selection", key="confirm_goals", help="Click to confirm your slider choice"):
                st.session_state.slider_interactions["goals"] = True
                st.rerun()
    
    st.markdown("**How satisfied are you with the outcome of this negotiation?**")
    def mark_satisfaction_interaction():
        st.session_state.slider_interactions["satisfaction"] = True
    
    survey_responses['satisfaction'] = st.slider(
        "", 
        min_value=1, max_value=7, value=4,
        format="%d",
        help="1 = Very dissatisfied, 7 = Very satisfied",
        key="satisfaction_slider",
        label_visibility="collapsed",
        on_change=mark_satisfaction_interaction
    )
    
    col1, col2 = st.columns([3, 1])
    with col1:
        if st.session_state.slider_interactions.get("satisfaction", False):
            st.caption("✅ 1 = Very dissatisfied → 7 = Very satisfied")
        else:
            st.caption("⏸️ 1 = Very dissatisfied → 7 = Very satisfied")
    with col2:
        if not st.session_state.slider_interactions.get("satisfaction", False):
            if st.button("Confirm Selection", key="confirm_satisfaction", help="Click to confirm your slider choice"):
                st.session_state.slider_interactions["satisfaction"] = True
                st.rerun()
    
    st.markdown("**How successfully did you resolve any conflicts that arose?**")
    def mark_conflict_interaction():
        st.session_state.slider_interactions["conflict_resolve"] = True
    
    survey_responses['conflict_resolve'] = st.slider(
        "", 
        min_value=1, max_value=7, value=4,
        format="%d",
        help="1 = Not at all, 7 = Completely",
        key="conflict_slider",
        label_visibility="collapsed",
        on_change=mark_conflict_interaction
    )
    
    col1, col2 = st.columns([3, 1])
    with col1:
        if st.session_state.slider_interactions.get("conflict_resolve", False):
            st.caption("✅ 1 = Not at all → 7 = Completely")
        else:
            st.caption("⏸️ 1 = Not at all → 7 = Completely")
    with col2:
        if not st.session_state.slider_interactions.get("conflict_resolve", False):
            if st.button("Confirm Selection", key="confirm_conflict", help="Click to confirm your slider choice"):
                st.session_state.slider_interactions["conflict_resolve"] = True
                st.rerun()
    
    st.markdown("**How natural and realistic did the AI agent seem during your interaction?**")
    def mark_believability_interaction():
        st.session_state.slider_interactions["believability"] = True
    
    survey_responses['believability'] = st.slider(
        "", 
        min_value=1, max_value=7, value=4,
        format="%d",
        help="1 = Not at all, 7 = Completely",
        key="believability_slider",
        label_visibility="collapsed",
        on_change=mark_believability_interaction
    )
    
    col1, col2 = st.columns([3, 1])
    with col1:
        if st.session_state.slider_interactions.get("believability", False):
            st.caption("✅ 1 = Not at all → 7 = Completely")
        else:
            st.caption("⏸️ 1 = Not at all → 7 = Completely")
    with col2:
        if not st.session_state.slider_interactions.get("believability", False):
            if st.button("Confirm Selection", key="confirm_believability", help="Click to confirm your slider choice"):
                st.session_state.slider_interactions["believability"] = True
                st.rerun()
    
    st.markdown("**How well did you feel the AI agent built upon and engaged with your points and ideas during the interaction?**")
    def mark_transactivity_interaction():
        st.session_state.slider_interactions["transactivity"] = True
    
    survey_responses['transactivity'] = st.slider(
        "", 
        min_value=1, max_value=5, value=3,
        format="%d",
        help="1 = Mostly ignored, 3 = Surface-level acknowledged, 5 = Meaningfully engaged",
        key="transactivity_slider",
        label_visibility="collapsed",
        on_change=mark_transactivity_interaction
    )
    
    col1, col2 = st.columns([3, 1])
    with col1:
        if st.session_state.slider_interactions.get("transactivity", False):
            st.caption("✅ 1 = Mostly ignored my talking points • 3 = Surface-level acknowledged what I said but didn't engage with my points • 5 = Meaningfully engaged with my points and incorporated them into its talking points")
        else:
            st.caption("⏸️ 1 = Mostly ignored my talking points • 3 = Surface-level acknowledged what I said but didn't engage with my points • 5 = Meaningfully engaged with my points and incorporated them into its talking points")
    with col2:
        if not st.session_state.slider_interactions.get("transactivity", False):
            if st.button("Confirm Selection", key="confirm_transactivity", help="Click to confirm your slider choice"):
                st.session_state.slider_interactions["transactivity"] = True
                st.rerun()
    
    st.markdown("**How truthful was the AI agent during your interaction?**")
    def mark_truthfulness_interaction():
        st.session_state.slider_interactions["truthfulness"] = True
    
    survey_responses['truthfulness'] = st.slider(
        "", 
        min_value=1, max_value=7, value=4,
        format="%d",
        help="1 = Not at all, 7 = Completely",
        key="truthfulness_slider",
        label_visibility="collapsed",
        on_change=mark_truthfulness_interaction
    )
    
    col1, col2 = st.columns([3, 1])
    with col1:
        if st.session_state.slider_interactions.get("truthfulness", False):
            st.caption("✅ 1 = Not at all → 7 = Completely")
        else:
            st.caption("⏸️ 1 = Not at all → 7 = Completely")
    with col2:
        if not st.session_state.slider_interactions.get("truthfulness", False):
            if st.button("Confirm Selection", key="confirm_truthfulness", help="Click to confirm your slider choice"):
                st.session_state.slider_interactions["truthfulness"] = True
                st.rerun()
    
    return survey_responses


def simple_user_study_interface() -> None:
    """Simple user study interface with manual conversation flow"""
    initialize_simple_session_state()
    
    # Hide sidebar for participants
    participant_mode = st.query_params.get("participant", st.query_params.get("p", "false")).lower() == "true"
    if participant_mode:
        st.markdown("""
        <style>
        section[data-testid="stSidebar"] {display: none !important;}
        .css-1d391kg {display: none !important;}
        .css-1y4p8pa {padding-left: 1rem !important;}
        .css-1lcbmhc {display: none !important;}
        .css-1outpf7 {display: none !important;}
        .css-164nlkn {display: none !important;}
        div[data-testid="stSidebarNav"] {display: none !important;}
        </style>
        """, unsafe_allow_html=True)
    
    # Page header
    st.title("🔬 Human-AI Conversation Study")
    
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
        
        st.markdown("---")
        st.markdown("## 👥 **User Study Interface**")
        st.markdown("Use the interface below to test the user study flow or conduct actual sessions.")
    
    else:
        st.markdown("Welcome to our research study! Please read your role carefully and engage naturally in the conversation.")
    
    st.markdown("---")
    
    # Display role information
    display_user_role_simple()
    
    st.markdown("---")
    
    # Conversation area - always show input interface
    # Display conversation history if it exists
    if st.session_state.conversation_history:
        display_conversation_history()
        st.markdown("---")
    
    # Combined AI agent info and conversation input area
    if not st.session_state.conversation_history:
        # Show AI agent info and conversation starter
        if st.session_state.agent_choice_1 in st.session_state.agent_dict:
            ai_agent = st.session_state.agent_dict[st.session_state.agent_choice_1]
            st.markdown("### 💬 **Start the Conversation**")
            st.markdown(f"You will be conversing with an AI agent (**{ai_agent.get('occupation', 'Assistant')}**). Type your message below to begin.")
            
            # Show debug info for researchers only
            participant_mode = st.query_params.get("participant", st.query_params.get("p", "false")).lower() == "true"
            if not participant_mode:
                with st.expander("🔧 Agent Selection Details (Debug)", expanded=False):
                    st.markdown("**URL Intervention Dimensions:**")
                    st.json(st.session_state.interventions)
                    st.markdown("**Selected Agent Profile:**")
                    st.markdown(f"Agent Key: `{st.session_state.agent_choice_1}`")
                    st.markdown(f"Intervention Mapping: {st.session_state.interventions}")
        else:
            st.markdown("### 💬 **Start the Conversation**")
    else:
        st.markdown("### 💬 **Your Response**")
    
    human_input = st.text_area(
        label="", 
        placeholder="Type what you want to say...",
        height=100,
        key=f"human_input_{st.session_state.turn_number}",
        label_visibility="collapsed"
    )
    
    # Show buttons based on conversation state
    if not st.session_state.conversation_history:
        # Before conversation starts - only show Send Message button
        if st.button("Send Message", type="primary", use_container_width=True):
            if human_input.strip():
                # Start the conversation automatically on first message
                st.session_state.study_active = True
                st.session_state.turn_number = 0
                
                # Add human message to history
                st.session_state.conversation_history.append({
                    'speaker': 'Human',
                    'content': human_input.strip(),
                    'action_type': 'speak'
                })
                
                # Generate AI response
                ai_response = simulate_ai_response(human_input.strip())
                ai_name = st.session_state.agent_dict[st.session_state.agent_choice_1].get('first_name', 'AI')
                
                st.session_state.conversation_history.append({
                    'speaker': ai_name,
                    'content': ai_response,
                    'action_type': 'speak'
                })
                
                st.session_state.turn_number += 1
                st.rerun()
            else:
                st.error("Please enter a message")
    else:
        # After conversation has started - show both buttons
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Send Message", type="primary"):
                if human_input.strip():
                    # Check if we've reached max turns (each message = 1 turn)
                    if len(st.session_state.conversation_history) >= st.session_state.max_turns:
                        st.warning(f"Maximum conversation turns ({st.session_state.max_turns}) reached. Conversation will end.")
                        st.session_state.study_active = False
                        st.success("Conversation ended due to turn limit. Thank you for participating!")
                        st.rerun()
                        return
                    
                    # Add human message to history
                    st.session_state.conversation_history.append({
                        'speaker': 'Human',
                        'content': human_input.strip(),
                        'action_type': 'speak'
                    })
                    
                    # Generate AI response
                    ai_response = simulate_ai_response(human_input.strip())
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
                        
                        # Silently save conversation data (survey will trigger final save)
                        try:
                            session_id = save_conversation_to_redis(
                                st.session_state.conversation_history,
                                st.session_state.interventions,
                                st.session_state.scenario_choice,
                                st.session_state.agent_choice_1,
                                st.session_state.get('prolific_params', {}),
                                None  # No survey responses yet
                            )
                            if session_id:
                                st.session_state.saved_session_id = session_id
                        except Exception as e:
                            st.error(f"Warning: Could not save conversation data: {str(e)}")
                    
                    st.rerun()
                else:
                    st.error("Please enter a message")
        
        with col2:
            if st.button("End Conversation", type="secondary"):
                st.session_state.study_active = False
                
                # Silently save conversation data (survey will trigger final save)
                try:
                    session_id = save_conversation_to_redis(
                        st.session_state.conversation_history,
                        st.session_state.interventions,
                        st.session_state.scenario_choice,
                        st.session_state.agent_choice_1,
                        st.session_state.get('prolific_params', {}),
                        None  # No survey responses yet
                    )
                    if session_id:
                        st.session_state.saved_session_id = session_id
                except Exception as e:
                    st.error(f"Warning: Could not save conversation data: {str(e)}")
    
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
                    
                    # Save everything to database with survey results
                    try:
                        session_id = save_conversation_to_redis(
                            st.session_state.conversation_history,
                            st.session_state.interventions,
                            st.session_state.scenario_choice,
                            st.session_state.agent_choice_1,
                            st.session_state.get('prolific_params', {}),
                            survey_responses
                        )
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
                        "occupation": agent_profile_data.get('occupation', ''),
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