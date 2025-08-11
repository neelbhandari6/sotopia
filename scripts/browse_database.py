#!/usr/bin/env python3
"""
Interactive script to browse the Redis database and view user study data.
"""

import os
import sys
import json
from datetime import datetime

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sotopia.database import EpisodeLog, AgentProfile, EnvironmentProfile


def check_database_connection():
    """Check if we can connect to the Redis database."""
    try:
        # Try a more basic connection test first
        import redis
        redis_url = os.getenv("REDIS_OM_URL", "redis://localhost:6379")
        client = redis.from_url(redis_url)
        client.ping()
        print("✅ Redis server connection successful")
        
        # Try to get episodes with error handling
        try:
            episodes = EpisodeLog.find().all()
            print(f"✅ Found {len(episodes)} episodes in database")
            return True
        except Exception as e:
            print(f"⚠️  Redis connected but database query failed: {e}")
            print("This might be a new database or schema issue.")
            # Still return True since Redis is working
            return True
            
    except Exception as e:
        print(f"❌ Failed to connect to Redis: {e}")
        print("\nTo fix this:")
        print("1. Make sure Redis is running:")
        print("   sudo systemctl start redis-server")
        print("   # or")
        print("   docker run -p 6379:6379 redis:latest")
        print("2. Set REDIS_OM_URL environment variable:")
        print("   export REDIS_OM_URL='redis://localhost:6379'")
        return False


def list_all_episodes():
    """List all episodes in the database."""
    try:
        episodes = EpisodeLog.find().all()
        if not episodes:
            print("\n📋 No episodes found in database")
            print("This could mean:")
            print("- No conversations have been saved yet")
            print("- Database is empty/new")
            print("- Schema migration needed")
            return []
            
        print(f"\n📋 Found {len(episodes)} total episodes:")
        
        user_study_count = 0
        for i, episode in enumerate(episodes[-10:], 1):  # Show last 10
            try:
                is_user_study = episode.tag and 'user_study' in episode.tag
                if is_user_study:
                    user_study_count += 1
                
                marker = "🔬" if is_user_study else "🤖"
                message_count = len(episode.messages) if episode.messages else 0
                print(f"{marker} {episode.pk}: {episode.tag} ({message_count} turns)")
            except Exception as e:
                print(f"⚠️ Error reading episode {i}: {e}")
        
        print(f"\nUser study episodes: {user_study_count}")
        print(f"Agent-agent episodes: {len(episodes) - user_study_count}")
        
        return episodes
    except Exception as e:
        print(f"Error listing episodes: {e}")
        print("Try running database migrations or check if the database schema is initialized")
        return []


def view_episode_details(episode_id: str):
    """View detailed information about a specific episode."""
    try:
        episode = EpisodeLog.get(episode_id)
        
        print(f"\n📄 Episode Details: {episode.pk}")
        print(f"Tag: {episode.tag}")
        print(f"Environment: {episode.environment}")
        print(f"Agents: {', '.join(episode.agents)}")
        print(f"Models: {', '.join(episode.models) if episode.models else 'None'}")
        print(f"Total turns: {len(episode.messages)}")
        print(f"Reasoning: {episode.reasoning}")
        
        # Show conversation
        print(f"\n💬 Conversation:")
        for turn_idx, turn_messages in enumerate(episode.messages, 1):
            print(f"\nTurn {turn_idx}:")
            for speaker, action_type, content in turn_messages:
                print(f"  {speaker} ({action_type}): {content}")
        
        return episode
        
    except Exception as e:
        print(f"Error retrieving episode {episode_id}: {e}")
        return None


def search_user_study_episodes():
    """Search and display user study episodes."""
    try:
        episodes = EpisodeLog.find().all()
        user_studies = [ep for ep in episodes if ep.tag and 'user_study' in ep.tag]
        
        if not user_studies:
            print("No user study episodes found.")
            return []
        
        print(f"\n🔬 Found {len(user_studies)} user study episodes:")
        
        for episode in user_studies:
            # Try to extract intervention info
            interventions = "Unknown"
            if episode.reasoning and 'interventions:' in episode.reasoning:
                try:
                    reasoning_json = episode.reasoning.split('interventions: ')[1]
                    interventions_dict = json.loads(reasoning_json)
                    interventions = f"T:{interventions_dict.get('transparency', '?')}"
                except:
                    pass
            
            print(f"  {episode.pk}: {episode.tag}")
            print(f"    Environment: {episode.environment}")
            print(f"    Turns: {len(episode.messages)}, Interventions: {interventions}")
        
        return user_studies
        
    except Exception as e:
        print(f"Error searching user studies: {e}")
        return []


def main():
    print("🔍 Sotopia Database Browser")
    print("=" * 40)
    
    if not check_database_connection():
        return
    
    while True:
        print("\nOptions:")
        print("1. List all episodes")
        print("2. Search user study episodes")
        print("3. View episode details")
        print("4. Database info")
        print("5. Exit")
        
        choice = input("\nEnter your choice (1-5): ").strip()
        
        if choice == '1':
            list_all_episodes()
        
        elif choice == '2':
            search_user_study_episodes()
        
        elif choice == '3':
            episode_id = input("Enter episode ID: ").strip()
            if episode_id:
                view_episode_details(episode_id)
        
        elif choice == '4':
            print(f"\n📊 Database Information:")
            try:
                episodes = EpisodeLog.find().all()
                agents = AgentProfile.find().all()
                environments = EnvironmentProfile.find().all()
                
                print(f"Total episodes: {len(episodes)}")
                print(f"Total agents: {len(agents)}")
                print(f"Total environments: {len(environments)}")
                
                # Check Redis URL
                redis_url = os.getenv("REDIS_OM_URL", "redis://localhost:6379")
                print(f"Redis URL: {redis_url}")
                
            except Exception as e:
                print(f"Error getting database info: {e}")
        
        elif choice == '5':
            print("Goodbye! 👋")
            break
        
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    main()