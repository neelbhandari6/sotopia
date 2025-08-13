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


def save_conversation_to_redis(conversation_history: list, interventions: dict, scenario_choice: str, agent_choice: str) -> str:
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
                "personality_and_values": agent_profile_data.get('personality_and_values', ''),
                "decision_making_style": agent_profile_data.get('decision_making_style', ''),
                "big_five": agent_profile_data.get('big_five', ''),
                "mbti": agent_profile_data.get('mbti', ''),
            },
            "conversation_stats": {
                "total_turns": len(conversation_history),
                "human_messages": len([msg for msg in conversation_history if msg.get('speaker') == 'Human']),
                "ai_messages": len([msg for msg in conversation_history if msg.get('speaker') != 'Human']),
                "avg_message_length": sum(len(msg.get('content', '')) for msg in conversation_history) / len(conversation_history) if conversation_history else 0
            }
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
        
        # Load data from local files
        st.session_state.scenarios = load_local_scenarios()
        st.session_state.agent_dict = load_local_agents()
        st.session_state.agent_model_dict = get_models_local()
        
        # All five intervention dimensions from URL parameters (support both long and short forms)
        st.session_state.interventions = {
            "transparency": st.query_params.get("transparency", st.query_params.get("t", "low")).lower(),  # t or transparency
            "warmth": st.query_params.get("warmth", st.query_params.get("w", "low")).lower(),              # w or warmth  
            "expertise": st.query_params.get("expertise", st.query_params.get("e", "high")).lower(),       # e or expertise
            "adaptability": st.query_params.get("adaptability", st.query_params.get("a", "high")).lower(), # a or adaptability
            "theory_of_mind": st.query_params.get("theory_of_mind", st.query_params.get("tom", "high")).lower() # tom or theory_of_mind
        }
        
        # Pre-configured study settings
        st.session_state.scenario_choice = st.query_params.get("scenario", st.query_params.get("s", list(st.session_state.scenarios.keys())[0]))
        
        # Auto-select agent based on intervention dimensions (NEW LOGIC)
        if st.query_params.get("ai_agent") or st.query_params.get("agent"):
            # Manual agent selection via URL
            st.session_state.agent_choice_1 = st.query_params.get("ai_agent", st.query_params.get("agent", list(st.session_state.agent_dict.keys())[0]))
        else:
            # Auto-select agent based on intervention dimensions
            st.session_state.agent_choice_1 = find_matching_agent(st.session_state.interventions, st.session_state.agent_dict)
        
        st.session_state.max_turns = 20  # Maximum conversation turns
        
        # Backward compatibility for transparency
        st.session_state.show_ai_thinking = st.session_state.interventions["transparency"] == "high"


def display_user_role_simple() -> None:
    """Display the user's scenario and goal"""
    if st.session_state.scenario_choice in st.session_state.scenarios:
        current_scenario = st.session_state.scenarios[st.session_state.scenario_choice]
        
        # Debug info (can be removed later)
        if st.sidebar.checkbox("Show Debug Info", value=False):
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
                # Use markdown instead of st.info to preserve formatting
                st.markdown(f"""
                <div style="background-color: #d1ecf1; border: 1px solid #bee5eb; border-radius: 0.375rem; padding: 0.75rem; margin: 1rem 0;">
                    {clean_goal}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.warning("No task goal found - this scenario may not be suitable for user studies")
        else:
            st.warning("No goal information available for this scenario")
        
        # Show AI agent basic information
        if st.session_state.agent_choice_1 in st.session_state.agent_dict:
            ai_agent = st.session_state.agent_dict[st.session_state.agent_choice_1]
            st.markdown("### 🤖 **AI Conversation Partner**")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Age**: {ai_agent.get('age', 'Unknown')}")
            with col2:
                st.markdown(f"**Occupation**: {ai_agent.get('occupation', 'Unknown')}")
            
            # Show intervention dimensions and selected agent (for verification)
            with st.expander("🔧 Agent Selection Details (Debug)", expanded=False):
                st.markdown("**URL Intervention Dimensions:**")
                st.json(st.session_state.interventions)
                st.markdown("**Selected Agent Profile:**")
                st.markdown(f"Agent Key: `{st.session_state.agent_choice_1}`")
                personality_snippet = ai_agent.get('personality_and_values', '')[:300] + "..."
                st.markdown(f"Personality: {personality_snippet}")
            
            st.markdown("You will be conversing with this AI agent. The conversation will begin when you send your first message.")


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


def simple_user_study_interface() -> None:
    """Simple user study interface with manual conversation flow"""
    initialize_simple_session_state()
    
    # Page header
    st.title("🔬 Human-AI Conversation Study")
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
    
    # Always show human input area
    st.markdown("### 💬 **Your Message**")
    
    human_input = st.text_area(
        "Type your message:", 
        placeholder="Type what you want to say...",
        height=100,
        key=f"human_input_{st.session_state.turn_number}"
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
                        st.success(f"Conversation completed! Maximum turns ({st.session_state.max_turns}) reached. Thank you for participating!")
                        
                        # Automatically save to database when max turns reached
                        try:
                            session_id = save_conversation_to_redis(
                                st.session_state.conversation_history,
                                st.session_state.interventions,
                                st.session_state.scenario_choice,
                                st.session_state.agent_choice_1
                            )
                            if session_id:
                                st.session_state.saved_session_id = session_id
                                st.info("💾 Conversation automatically saved to database.")
                        except Exception as e:
                            st.error(f"Warning: Could not auto-save to database: {str(e)}")
                    
                    st.rerun()
                else:
                    st.error("Please enter a message")
        
        with col2:
            if st.button("End Conversation", type="secondary"):
                st.session_state.study_active = False
                st.success("Conversation ended. Thank you for participating!")
                
                # Automatically save to database when user ends conversation
                try:
                    session_id = save_conversation_to_redis(
                        st.session_state.conversation_history,
                        st.session_state.interventions,
                        st.session_state.scenario_choice,
                        st.session_state.agent_choice_1
                    )
                    if session_id:
                        st.session_state.saved_session_id = session_id
                        st.info("💾 Conversation automatically saved to database.")
                except Exception as e:
                    st.error(f"Warning: Could not auto-save to database: {str(e)}")
    
    # Show conversation stats
    if st.session_state.conversation_history:
        st.markdown("---")
        turn_count = len(st.session_state.conversation_history)  # Each message = 1 turn
        st.markdown(f"**Conversation turns**: {turn_count}/{st.session_state.max_turns}")
    
    # Show auto-save confirmation (conversation already saved automatically)
    if not st.session_state.study_active and st.session_state.conversation_history:
        if st.session_state.get('saved_session_id'):
            st.success("✅ Conversation automatically saved to database!")
            st.markdown(f"**Session ID:** `{st.session_state.saved_session_id}`")
        
        # Database viewing section (only for researchers, not participants)
        participant_mode = st.query_params.get("participant", "false").lower() == "true"
        
        if not participant_mode:
            st.markdown("---")
            st.markdown("### 🔍 **View Saved Data**")
            st.markdown("Explore previously saved conversations and database contents:")
            
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
                        "personality_and_values": agent_profile_data.get('personality_and_values', ''),
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