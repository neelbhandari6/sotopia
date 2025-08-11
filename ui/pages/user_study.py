import streamlit as st
import json
import re
import csv
import os
from datetime import datetime
from typing import Any
from uuid import uuid4
from ui.rendering import (
    get_scenarios,
    get_agents,
    get_models,
)
from sotopia.database import EpisodeLog, AgentProfile, EnvironmentProfile


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


def save_conversation_to_redis(conversation_history: list, interventions: dict, scenario_choice: str, agent_choice: str) -> str:
    """Save conversation data to Redis database as EpisodeLog"""
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
        
        # Get scenario and agent info
        scenarios = get_scenarios()
        agents = get_agents()
        
        scenario_info = scenarios.get(scenario_choice, {})
        agent_info = agents.get(agent_choice, {})
        
        # Create episode log
        episode_log = EpisodeLog(
            environment=scenario_choice,
            agents=[agent_choice, "human_participant"],  # AI agent + human
            tag=f"user_study_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            models=[f"intervention_{interventions.get('transparency', 'low')}", "human"],
            messages=formatted_messages,
            reasoning=f"User study with interventions: {json.dumps(interventions)}",
            rewards=[0.0, 0.0]  # Placeholder rewards
        )
        
        # Save to Redis
        episode_log.save()
        st.success(f"✅ Conversation saved to database with ID: {episode_log.pk}")
        return episode_log.pk
        
    except Exception as e:
        st.error(f"❌ Failed to save to database: {str(e)}")
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


def initialize_simple_session_state() -> None:
    """Initialize session state for simple user study"""
    # Initialize API_BASE if not already set
    if "API_BASE" not in st.session_state:
        DEFAULT_BASE = "sotopia-lab--sotopia-fastapi-webapi-serve.modal.run"
        st.session_state.API_BASE = f"https://{DEFAULT_BASE}"
        st.session_state.WS_BASE = f"ws://{DEFAULT_BASE}"
    
    if "conversation_history" not in st.session_state:
        st.session_state.conversation_history = []
        st.session_state.turn_number = 0
        st.session_state.study_active = False
        
        # Load data from local files
        st.session_state.scenarios = load_local_scenarios()
        st.session_state.agent_dict = load_local_agents()
        st.session_state.agent_model_dict = get_models_local()
        
        # Pre-configured study settings (support both long and short forms)
        st.session_state.scenario_choice = st.query_params.get("scenario", st.query_params.get("s", list(st.session_state.scenarios.keys())[0]))
        st.session_state.agent_choice_1 = st.query_params.get("ai_agent", st.query_params.get("agent", list(st.session_state.agent_dict.keys())[0]))
        st.session_state.max_turns = 20  # Maximum conversation turns
        
        # All five intervention dimensions from URL parameters (support both long and short forms)
        st.session_state.interventions = {
            "transparency": st.query_params.get("transparency", st.query_params.get("t", "low")).lower(),  # t or transparency
            "warmth": st.query_params.get("warmth", st.query_params.get("w", "low")).lower(),              # w or warmth  
            "expertise": st.query_params.get("expertise", st.query_params.get("e", "high")).lower(),       # e or expertise
            "adaptability": st.query_params.get("adaptability", st.query_params.get("a", "high")).lower(), # a or adaptability
            "theory_of_mind": st.query_params.get("theory_of_mind", st.query_params.get("tom", "high")).lower() # tom or theory_of_mind
        }
        
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
                    st.write(f"**You** ({action_type}): {content}")
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
    """Simulate AI response (placeholder - in real implementation this would call the LLM)"""
    # This is a placeholder. In the actual implementation, this would:
    # 1. Send the human message to the AI agent
    # 2. Get the AI's response using the selected agent personality and transparency setting
    # 3. Return the formatted response
    
    ai_name = st.session_state.agent_dict[st.session_state.agent_choice_1].get('first_name', 'AI')
    
    if st.session_state.show_ai_thinking:
        return f"<THINK>The human just said: '{human_message}'. I should respond appropriately based on my personality and the scenario context.</THINK>Thank you for sharing that with me. I understand your perspective on this matter."
    else:
        return "Thank you for sharing that with me. I understand your perspective on this matter."


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
                    
                    st.rerun()
                else:
                    st.error("Please enter a message")
        
        with col2:
            if st.button("End Conversation", type="secondary"):
                st.session_state.study_active = False
                st.success("Conversation ended. Thank you for participating!")
    
    # Show conversation stats
    if st.session_state.conversation_history:
        st.markdown("---")
        turn_count = len(st.session_state.conversation_history)  # Each message = 1 turn
        st.markdown(f"**Conversation turns**: {turn_count}/{st.session_state.max_turns}")
    
    # Data saving section (show when conversation has ended and there's data to save)
    if not st.session_state.study_active and st.session_state.conversation_history:
        st.markdown("---")
        st.markdown("### 💾 **Save Conversation Data**")
        st.markdown("Your conversation data can be saved for research purposes:")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("💾 Save to Database", type="primary", use_container_width=True):
                session_id = save_conversation_to_redis(
                    st.session_state.conversation_history,
                    st.session_state.interventions,
                    st.session_state.scenario_choice,
                    st.session_state.agent_choice_1
                )
                if session_id:
                    st.session_state.saved_session_id = session_id
        
        with col2:
            if st.button("📂 Export to Files", type="secondary", use_container_width=True):
                export_session_id = st.session_state.get('saved_session_id', None)
                export_conversation_to_files(
                    st.session_state.conversation_history,
                    st.session_state.interventions,
                    st.session_state.scenario_choice,
                    st.session_state.agent_choice_1,
                    export_session_id
                )
        
        # Show intervention summary for transparency
        with st.expander("📊 Study Configuration Details"):
            st.json({
                "scenario": st.session_state.scenario_choice,
                "ai_agent": st.session_state.agent_choice_1,
                "interventions": st.session_state.interventions,
                "total_turns": len(st.session_state.conversation_history),
                "conversation_completed": not st.session_state.study_active
            })


# Run the simple user study interface
simple_user_study_interface()