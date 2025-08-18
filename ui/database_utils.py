"""
Database utility functions for user study data management.

This module provides comprehensive functions for querying, viewing, and exporting 
user study conversation data from the Redis database.
"""

import json
import csv
import os
from datetime import datetime
from typing import List, Dict, Optional, Any
from collections import defaultdict, Counter

from sotopia.database import EpisodeLog, EnvAgentComboStorage


def get_user_study_episodes(filter_by: Optional[Dict[str, Any]] = None) -> List[EpisodeLog]:
    """
    Retrieve user study episodes from the database with optional filtering.
    
    Args:
        filter_by: Optional dictionary with filter criteria:
            - 'interventions': Dict with intervention dimensions to match
            - 'scenario': Scenario name to filter by
            - 'agent': Agent name to filter by  
            - 'date_from': Start date (YYYY-MM-DD format)
            - 'date_to': End date (YYYY-MM-DD format)
            - 'min_turns': Minimum number of conversation turns
            - 'max_turns': Maximum number of conversation turns
    
    Returns:
        List of EpisodeLog objects matching the criteria
    """
    try:
        # Get all episodes
        all_episodes = EpisodeLog.find().all()
        
        # Filter for user study episodes (tagged with 'user_study')
        user_study_episodes = [
            episode for episode in all_episodes 
            if episode.tag and 'user_study' in episode.tag
        ]
        
        # Apply additional filters if specified
        if filter_by:
            filtered_episodes = []
            
            for episode in user_study_episodes:
                # Parse episode reasoning for detailed info
                episode_data = parse_episode_reasoning(episode)
                
                # Check filters
                if not matches_filter(episode, episode_data, filter_by):
                    continue
                    
                filtered_episodes.append(episode)
            
            user_study_episodes = filtered_episodes
        
        print(f"Found {len(user_study_episodes)} user study episodes matching criteria")
        return user_study_episodes
        
    except Exception as e:
        print(f"Error accessing database: {e}")
        return []


def parse_episode_reasoning(episode: EpisodeLog) -> Dict[str, Any]:
    """Parse the JSON reasoning field from an episode log."""
    try:
        if episode.reasoning:
            # Try parsing as JSON first (new format)
            try:
                return json.loads(episode.reasoning)
            except json.JSONDecodeError:
                # Fall back to old format parsing
                if 'interventions:' in episode.reasoning:
                    reasoning_json = episode.reasoning.split('interventions: ')[1]
                    interventions = json.loads(reasoning_json)
                    return {"interventions": interventions}
        return {}
    except Exception:
        return {}


def matches_filter(episode: EpisodeLog, episode_data: Dict[str, Any], filter_by: Dict[str, Any]) -> bool:
    """Check if an episode matches the specified filter criteria."""
    
    # Filter by interventions
    if 'interventions' in filter_by:
        episode_interventions = episode_data.get('interventions', {})
        for key, value in filter_by['interventions'].items():
            if episode_interventions.get(key) != value:
                return False
    
    # Filter by scenario
    if 'scenario' in filter_by:
        if episode.environment != filter_by['scenario']:
            return False
    
    # Filter by agent
    if 'agent' in filter_by:
        if filter_by['agent'] not in episode.agents:
            return False
    
    # Filter by date range
    if 'date_from' in filter_by or 'date_to' in filter_by:
        # Extract date from tag or timestamp
        episode_date = extract_date_from_episode(episode, episode_data)
        if episode_date:
            if 'date_from' in filter_by:
                if episode_date < datetime.strptime(filter_by['date_from'], '%Y-%m-%d').date():
                    return False
            if 'date_to' in filter_by:
                if episode_date > datetime.strptime(filter_by['date_to'], '%Y-%m-%d').date():
                    return False
    
    # Filter by conversation length
    turn_count = len(episode.messages)
    if 'min_turns' in filter_by and turn_count < filter_by['min_turns']:
        return False
    if 'max_turns' in filter_by and turn_count > filter_by['max_turns']:
        return False
    
    return True


def extract_date_from_episode(episode: EpisodeLog, episode_data: Dict[str, Any]) -> Optional[datetime.date]:
    """Extract date from episode data."""
    try:
        # Try from structured timestamp first
        if 'timestamp' in episode_data:
            return datetime.fromisoformat(episode_data['timestamp']).date()
        
        # Try from tag
        if episode.tag and 'user_study_' in episode.tag:
            # Extract date from tag like "user_study_20240730_143502"
            parts = episode.tag.split('_')
            if len(parts) >= 3:
                date_str = parts[2]  # "20240730"
                if len(date_str) == 8 and date_str.isdigit():
                    return datetime.strptime(date_str, '%Y%m%d').date()
        
        return None
    except Exception:
        return None


def get_intervention_statistics(episodes: List[EpisodeLog]) -> Dict[str, Any]:
    """Calculate statistics about intervention dimensions across episodes."""
    
    intervention_stats = defaultdict(Counter)
    agent_stats = Counter()
    scenario_stats = Counter()
    conversation_lengths = []
    
    for episode in episodes:
        episode_data = parse_episode_reasoning(episode)
        interventions = episode_data.get('interventions', {})
        
        # Count intervention combinations
        for dimension, value in interventions.items():
            intervention_stats[dimension][value] += 1
        
        # Count agents and scenarios
        for agent in episode.agents:
            if agent != 'human_participant':
                agent_stats[agent] += 1
        scenario_stats[episode.environment] += 1
        
        # Track conversation lengths
        conversation_lengths.append(len(episode.messages))
    
    # Calculate conversation length statistics
    if conversation_lengths:
        avg_length = sum(conversation_lengths) / len(conversation_lengths)
        min_length = min(conversation_lengths)
        max_length = max(conversation_lengths)
    else:
        avg_length = min_length = max_length = 0
    
    return {
        'total_episodes': len(episodes),
        'intervention_distributions': dict(intervention_stats),
        'agent_usage': dict(agent_stats),
        'scenario_usage': dict(scenario_stats),
        'conversation_length_stats': {
            'average': avg_length,
            'minimum': min_length,
            'maximum': max_length,
            'distribution': Counter(conversation_lengths)
        }
    }


def export_episodes_to_enhanced_csv(episodes: List[EpisodeLog], filename: Optional[str] = None) -> str:
    """Export episodes to CSV with comprehensive intervention and agent data."""
    
    if not filename:
        filename = f"user_study_enhanced_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Write comprehensive header including survey responses and personality data
        writer.writerow([
            'episode_id', 'session_id', 'timestamp', 'tag', 'environment', 'ai_agent',
            'transparency', 'warmth', 'expertise', 'adaptability', 'theory_of_mind',
            'agent_name', 'agent_occupation', 'agent_age',
            'decision_making_style', 'big_five', 'mbti',
            'total_turns', 'human_messages', 'ai_messages', 'avg_message_length',
            'survey_transparency', 'survey_warmth', 'survey_theory_of_mind', 'survey_adaptability', 'survey_expertise',
            'survey_goals', 'survey_satisfaction', 'survey_conflict_resolve', 'survey_believability', 'survey_transactivity', 'survey_truthfulness',
            'prolific_pid', 'prolific_study_id', 'prolific_session_id',
            'personality_participant_id', 'personality_extroversion_score', 'personality_agreeableness_score', 
            'personality_extroversion_level', 'personality_agreeableness_level', 'personality_type',
            'turn_number', 'speaker', 'action_type', 'content', 'content_length'
        ])
        
        # Write data for each episode
        for episode in episodes:
            episode_data = parse_episode_reasoning(episode)
            interventions = episode_data.get('interventions', {})
            agent_attrs = episode_data.get('agent_attributes', {})
            conv_stats = episode_data.get('conversation_stats', {})
            survey_data = episode_data.get('survey_responses', {})
            prolific_data = episode_data.get('prolific_data', {})
            
            # Get AI agent name (not human_participant)
            ai_agent = next((agent for agent in episode.agents if agent != 'human_participant'), 'unknown')
            
            # Write each message as a row
            for turn_idx, turn_messages in enumerate(episode.messages):
                for speaker, action_type, content in turn_messages:
                    writer.writerow([
                        episode.pk,
                        episode_data.get('session_id', ''),
                        episode_data.get('timestamp', ''),
                        episode.tag,
                        episode.environment,
                        ai_agent,
                        interventions.get('transparency', ''),
                        interventions.get('warmth', ''),
                        interventions.get('expertise', ''),
                        interventions.get('adaptability', ''),
                        interventions.get('theory_of_mind', ''),
                        agent_attrs.get('name', ''),
                        agent_attrs.get('occupation', ''),
                        agent_attrs.get('age', ''),
                        agent_attrs.get('decision_making_style', ''),
                        agent_attrs.get('big_five', ''),
                        agent_attrs.get('mbti', ''),
                        conv_stats.get('total_turns', len(episode.messages)),
                        conv_stats.get('human_messages', 0),
                        conv_stats.get('ai_messages', 0),
                        conv_stats.get('avg_message_length', 0),
                        survey_data.get('transparency', ''),
                        survey_data.get('warmth', ''),
                        survey_data.get('theory_of_mind', ''),
                        survey_data.get('adaptability', ''),
                        survey_data.get('expertise', ''),
                        survey_data.get('goals', ''),
                        survey_data.get('satisfaction', ''),
                        survey_data.get('conflict_resolve', ''),
                        survey_data.get('believability', ''),
                        survey_data.get('transactivity', ''),
                        survey_data.get('truthfulness', ''),
                        prolific_data.get('PROLIFIC_PID', ''),
                        prolific_data.get('STUDY_ID', ''),
                        prolific_data.get('SESSION_ID', ''),
                        episode_data.get('personality_assessment', {}).get('participant_id', ''),
                        episode_data.get('personality_assessment', {}).get('scores', {}).get('extroversion', ''),
                        episode_data.get('personality_assessment', {}).get('scores', {}).get('agreeableness', ''),
                        episode_data.get('personality_assessment', {}).get('classification', {}).get('extroversion_level', ''),
                        episode_data.get('personality_assessment', {}).get('classification', {}).get('agreeableness_level', ''),
                        episode_data.get('personality_assessment', {}).get('classification', {}).get('personality_type', ''),
                        turn_idx + 1,
                        speaker,
                        action_type,
                        content,
                        len(content)
                    ])
    
    return filename


def export_episodes_to_enhanced_json(episodes: List[EpisodeLog], filename: Optional[str] = None) -> str:
    """Export episodes to JSON with full structured data."""
    
    if not filename:
        filename = f"user_study_enhanced_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    # Convert episodes to comprehensive format
    data = {
        'export_info': {
            'timestamp': datetime.now().isoformat(),
            'total_episodes': len(episodes),
            'export_type': 'user_study_enhanced'
        },
        'statistics': get_intervention_statistics(episodes),
        'episodes': []
    }
    
    for episode in episodes:
        episode_data = parse_episode_reasoning(episode)
        
        enhanced_episode = {
            'episode_id': episode.pk,
            'basic_info': {
                'tag': episode.tag,
                'environment': episode.environment,
                'agents': episode.agents,
                'models': episode.models
            },
            'study_data': episode_data,
            'conversation': {
                'messages': episode.messages,
                'total_turns': len(episode.messages),
                'message_details': []
            },
            'metadata': {
                'rewards': episode.rewards,
                'raw_reasoning': episode.reasoning
            }
        }
        
        # Add detailed message analysis
        for turn_idx, turn_messages in enumerate(episode.messages):
            for msg_idx, (speaker, action_type, content) in enumerate(turn_messages):
                enhanced_episode['conversation']['message_details'].append({
                    'turn': turn_idx + 1,
                    'message_in_turn': msg_idx + 1,
                    'speaker': speaker,
                    'action_type': action_type,
                    'content': content,
                    'content_length': len(content),
                    'is_human': speaker == 'Human',
                    'is_ai': speaker != 'Human' and speaker != 'Environment'
                })
        
        data['episodes'].append(enhanced_episode)
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    return filename


def print_database_summary():
    """Print comprehensive summary of the user study database."""
    
    print("🔍 Analyzing Redis database...")
    episodes = get_user_study_episodes()
    
    if not episodes:
        print("❌ No user study episodes found in database.")
        print("Make sure:")
        print("  1. Redis is running and accessible")
        print("  2. User study conversations have been saved")
        print("  3. REDIS_OM_URL environment variable is set correctly")
        return
    
    stats = get_intervention_statistics(episodes)
    
    print(f"\n📊 Database Summary:")
    print(f"{'='*50}")
    print(f"Total Episodes: {stats['total_episodes']}")
    
    print(f"\n🧪 Intervention Distributions:")
    for dimension, counts in stats['intervention_distributions'].items():
        print(f"  {dimension.title()}:")
        for value, count in counts.items():
            print(f"    {value}: {count}")
    
    print(f"\n🤖 AI Agent Usage:")
    for agent, count in stats['agent_usage'].items():
        print(f"  {agent}: {count}")
    
    print(f"\n🎭 Scenario Usage:")
    for scenario, count in stats['scenario_usage'].items():
        print(f"  {scenario}: {count}")
    
    print(f"\n💬 Conversation Statistics:")
    conv_stats = stats['conversation_length_stats']
    print(f"  Average length: {conv_stats['average']:.1f} turns")
    print(f"  Range: {conv_stats['minimum']} - {conv_stats['maximum']} turns")
    
    print(f"\n📋 Recent Episodes:")
    for episode in episodes[-5:]:
        episode_data = parse_episode_reasoning(episode)
        interventions = episode_data.get('interventions', {})
        transparency = interventions.get('transparency', 'unknown')
        turn_count = len(episode.messages)
        print(f"  {episode.pk[:16]}... | {transparency} transparency | {turn_count} turns | {episode.tag}")


def view_episode_details(episode_id: str):
    """Display detailed information about a specific episode."""
    
    try:
        episode = EpisodeLog.get(episode_id)
        episode_data = parse_episode_reasoning(episode)
        
        print(f"\n📝 Episode Details: {episode_id}")
        print(f"{'='*60}")
        
        # Basic info
        print(f"Tag: {episode.tag}")
        print(f"Environment: {episode.environment}")
        print(f"Agents: {', '.join(episode.agents)}")
        print(f"Models: {', '.join(episode.models) if episode.models else 'None'}")
        
        # Study data
        if 'interventions' in episode_data:
            print(f"\n🧪 Interventions:")
            for dim, val in episode_data['interventions'].items():
                print(f"  {dim}: {val}")
        
        if 'agent_attributes' in episode_data:
            print(f"\n🤖 Agent Attributes:")
            for attr, val in episode_data['agent_attributes'].items():
                if val:  # Only show non-empty values
                    print(f"  {attr}: {val}")
        
        # Conversation
        print(f"\n💬 Conversation ({len(episode.messages)} turns):")
        for turn_idx, turn_messages in enumerate(episode.messages, 1):
            print(f"\n  Turn {turn_idx}:")
            for speaker, action_type, content in turn_messages:
                content_preview = content[:100] + "..." if len(content) > 100 else content
                print(f"    {speaker} ({action_type}): {content_preview}")
        
        if 'conversation_stats' in episode_data:
            print(f"\n📊 Conversation Statistics:")
            for stat, val in episode_data['conversation_stats'].items():
                print(f"  {stat}: {val}")
        
    except Exception as e:
        print(f"❌ Error retrieving episode {episode_id}: {e}")


# Quick access functions for common queries
def get_episodes_by_intervention(dimension: str, value: str) -> List[EpisodeLog]:
    """Get all episodes with a specific intervention setting."""
    filter_criteria = {'interventions': {dimension: value}}
    return get_user_study_episodes(filter_by=filter_criteria)


def get_episodes_by_scenario(scenario_name: str) -> List[EpisodeLog]:
    """Get all episodes for a specific scenario."""
    return get_user_study_episodes(filter_by={'scenario': scenario_name})


def get_episodes_by_agent(agent_name: str) -> List[EpisodeLog]:
    """Get all episodes with a specific AI agent."""
    return get_user_study_episodes(filter_by={'agent': agent_name})


def get_recent_episodes(days: int = 7) -> List[EpisodeLog]:
    """Get episodes from the last N days."""
    from datetime import timedelta
    
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    
    return get_user_study_episodes(filter_by={
        'date_from': start_date.strftime('%Y-%m-%d'),
        'date_to': end_date.strftime('%Y-%m-%d')
    })