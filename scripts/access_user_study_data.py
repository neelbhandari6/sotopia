#!/usr/bin/env python3
"""
Script to access and query user study data from the Redis database.

Usage:
    python scripts/access_user_study_data.py [--format csv|json] [--output filename]
"""

import argparse
import json
import csv
import os
from datetime import datetime
from typing import List

# Add the parent directory to the path so we can import sotopia modules
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sotopia.database import EpisodeLog


def get_user_study_episodes() -> List[EpisodeLog]:
    """Retrieve all user study episodes from the database."""
    try:
        # Get all episodes
        all_episodes = EpisodeLog.find().all()
        
        # Filter for user study episodes (tagged with 'user_study')
        user_study_episodes = [
            episode for episode in all_episodes 
            if episode.tag and 'user_study' in episode.tag
        ]
        
        print(f"Found {len(user_study_episodes)} user study episodes out of {len(all_episodes)} total episodes")
        return user_study_episodes
        
    except Exception as e:
        print(f"Error accessing database: {e}")
        print("Make sure Redis is running and REDIS_OM_URL is set correctly")
        return []


def export_to_csv(episodes: List[EpisodeLog], filename: str = None):
    """Export user study data to CSV format."""
    if not filename:
        filename = f"user_study_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Write header
        writer.writerow([
            'episode_id', 'timestamp', 'tag', 'environment', 'agents', 'models',
            'interventions', 'turn_number', 'speaker', 'action_type', 'content',
            'total_turns', 'reasoning'
        ])
        
        # Write data
        for episode in episodes:
            # Extract interventions from reasoning field
            interventions = {}
            if episode.reasoning and 'interventions:' in episode.reasoning:
                try:
                    reasoning_json = episode.reasoning.split('interventions: ')[1]
                    interventions = json.loads(reasoning_json)
                except:
                    pass
            
            # Write each message as a row
            for turn_idx, turn_messages in enumerate(episode.messages):
                for msg_idx, (speaker, action_type, content) in enumerate(turn_messages):
                    writer.writerow([
                        episode.pk,
                        episode.tag,
                        episode.tag,
                        episode.environment,
                        ', '.join(episode.agents),
                        ', '.join(episode.models) if episode.models else '',
                        json.dumps(interventions),
                        turn_idx + 1,
                        speaker,
                        action_type,
                        content,
                        len(episode.messages),
                        episode.reasoning
                    ])
    
    print(f"✅ Data exported to CSV: {filename}")


def export_to_json(episodes: List[EpisodeLog], filename: str = None):
    """Export user study data to JSON format."""
    if not filename:
        filename = f"user_study_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    # Convert episodes to serializable format
    data = []
    for episode in episodes:
        # Extract interventions from reasoning
        interventions = {}
        if episode.reasoning and 'interventions:' in episode.reasoning:
            try:
                reasoning_json = episode.reasoning.split('interventions: ')[1]
                interventions = json.loads(reasoning_json)
            except:
                pass
        
        episode_data = {
            'episode_id': episode.pk,
            'timestamp': episode.tag,
            'environment': episode.environment,
            'agents': episode.agents,
            'models': episode.models,
            'interventions': interventions,
            'messages': episode.messages,
            'reasoning': episode.reasoning,
            'rewards': episode.rewards,
            'total_turns': len(episode.messages)
        }
        data.append(episode_data)
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Data exported to JSON: {filename}")


def print_summary(episodes: List[EpisodeLog]):
    """Print a summary of the user study data."""
    if not episodes:
        print("No user study episodes found.")
        return
    
    print(f"\n📊 User Study Data Summary:")
    print(f"Total episodes: {len(episodes)}")
    
    # Count by interventions
    intervention_counts = {}
    environments = set()
    agents = set()
    
    for episode in episodes:
        environments.add(episode.environment)
        agents.update(episode.agents)
        
        # Try to extract interventions
        if episode.reasoning and 'interventions:' in episode.reasoning:
            try:
                reasoning_json = episode.reasoning.split('interventions: ')[1]
                interventions = json.loads(reasoning_json)
                transparency = interventions.get('transparency', 'unknown')
                key = f"transparency_{transparency}"
                intervention_counts[key] = intervention_counts.get(key, 0) + 1
            except:
                pass
    
    print(f"Unique environments: {len(environments)}")
    print(f"Unique agents: {len(agents)}")
    
    if intervention_counts:
        print(f"\nIntervention distribution:")
        for intervention, count in intervention_counts.items():
            print(f"  {intervention}: {count}")
    
    # Show recent episodes
    print(f"\n📋 Recent episodes:")
    for episode in episodes[-5:]:  # Show last 5
        turn_count = len(episode.messages)
        print(f"  {episode.pk}: {episode.tag} ({turn_count} turns)")


def main():
    parser = argparse.ArgumentParser(description='Access user study data from Redis database')
    parser.add_argument('--format', choices=['csv', 'json', 'summary'], default='summary',
                        help='Output format (default: summary)')
    parser.add_argument('--output', type=str, help='Output filename')
    parser.add_argument('--all', action='store_true', help='Include all episodes, not just user studies')
    
    args = parser.parse_args()
    
    print("🔍 Accessing Redis database...")
    
    if args.all:
        try:
            episodes = EpisodeLog.find().all()
            print(f"Found {len(episodes)} total episodes")
        except Exception as e:
            print(f"Error accessing database: {e}")
            return
    else:
        episodes = get_user_study_episodes()
    
    if not episodes:
        print("No episodes found. Make sure:")
        print("1. Redis is running")
        print("2. User study conversations have been saved")
        print("3. REDIS_OM_URL environment variable is set correctly")
        return
    
    if args.format == 'csv':
        export_to_csv(episodes, args.output)
    elif args.format == 'json':
        export_to_json(episodes, args.output)
    else:
        print_summary(episodes)


if __name__ == "__main__":
    main()