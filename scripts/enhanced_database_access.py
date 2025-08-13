#!/usr/bin/env python3
"""
Enhanced script for accessing and analyzing user study data from the Redis database.

This script provides comprehensive querying, filtering, and export capabilities
for user study conversation data, including detailed intervention analysis.

Usage:
    python scripts/enhanced_database_access.py [options]
    
Examples:
    # Show summary of all user studies
    python scripts/enhanced_database_access.py --summary
    
    # Export high transparency episodes
    python scripts/enhanced_database_access.py --filter interventions.transparency=high --format csv
    
    # View specific episode details
    python scripts/enhanced_database_access.py --view-episode EPISODE_ID
    
    # Get episodes from last 3 days
    python scripts/enhanced_database_access.py --recent-days 3 --format json
"""

import argparse
import os
import sys
from typing import Dict, Any, List

# Add the parent directory to the path so we can import sotopia modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our enhanced database utilities
from ui.database_utils import (
    get_user_study_episodes,
    get_intervention_statistics,
    export_episodes_to_enhanced_csv,
    export_episodes_to_enhanced_json,
    print_database_summary,
    view_episode_details,
    get_episodes_by_intervention,
    get_episodes_by_scenario,
    get_episodes_by_agent,
    get_recent_episodes
)


def parse_filter_args(filter_strings: List[str]) -> Dict[str, Any]:
    """Parse filter arguments from command line."""
    filters = {}
    
    for filter_str in filter_strings:
        if '=' not in filter_str:
            print(f"Warning: Invalid filter format '{filter_str}'. Use key=value format.")
            continue
        
        key, value = filter_str.split('=', 1)
        
        # Handle nested keys like 'interventions.transparency'
        if '.' in key:
            parent_key, child_key = key.split('.', 1)
            if parent_key not in filters:
                filters[parent_key] = {}
            filters[parent_key][child_key] = value
        else:
            # Handle special value types
            if value.lower() in ('true', 'false'):
                filters[key] = value.lower() == 'true'
            elif value.isdigit():
                filters[key] = int(value)
            else:
                filters[key] = value
    
    return filters


def main():
    parser = argparse.ArgumentParser(
        description='Enhanced access to user study data in Redis database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Filter Examples:
  --filter interventions.transparency=high
  --filter scenario=hiring_scenario_1
  --filter min_turns=5 max_turns=20
  --filter date_from=2024-07-01 date_to=2024-07-31

Export Examples:
  --format csv --output my_study_data.csv
  --format json --output full_study_export.json
        """
    )
    
    # Main actions (mutually exclusive)
    action_group = parser.add_mutually_exclusive_group()
    action_group.add_argument('--summary', action='store_true',
                             help='Show comprehensive database summary')
    action_group.add_argument('--view-episode', metavar='EPISODE_ID',
                             help='View detailed information about specific episode')
    action_group.add_argument('--recent-days', type=int, metavar='N',
                             help='Get episodes from last N days')
    
    # Filtering options
    parser.add_argument('--filter', action='append', metavar='KEY=VALUE',
                        help='Filter episodes (can be used multiple times)')
    parser.add_argument('--intervention', metavar='DIMENSION=VALUE',
                        help='Filter by intervention dimension (e.g., transparency=high)')
    parser.add_argument('--scenario', metavar='NAME',
                        help='Filter by scenario name')
    parser.add_argument('--agent', metavar='NAME',
                        help='Filter by AI agent name')
    
    # Export options
    parser.add_argument('--format', choices=['csv', 'json'], 
                        help='Export format')
    parser.add_argument('--output', metavar='FILENAME',
                        help='Output filename (auto-generated if not specified)')
    
    # Display options
    parser.add_argument('--stats-only', action='store_true',
                        help='Show only statistics, not episode list')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Verbose output')
    
    args = parser.parse_args()
    
    # Check if Redis is accessible
    print("🔍 Checking Redis database connection...")
    
    # Handle specific actions
    if args.summary:
        print_database_summary()
        return
    
    if args.view_episode:
        view_episode_details(args.view_episode)
        return
    
    # Build filter criteria
    filter_criteria = {}
    
    if args.filter:
        filter_criteria.update(parse_filter_args(args.filter))
    
    if args.intervention:
        dimension, value = args.intervention.split('=', 1)
        if 'interventions' not in filter_criteria:
            filter_criteria['interventions'] = {}
        filter_criteria['interventions'][dimension] = value
    
    if args.scenario:
        filter_criteria['scenario'] = args.scenario
    
    if args.agent:
        filter_criteria['agent'] = args.agent
    
    if args.recent_days:
        episodes = get_recent_episodes(args.recent_days)
        print(f"📅 Found {len(episodes)} episodes from last {args.recent_days} days")
    else:
        # Get episodes with filters
        if args.verbose and filter_criteria:
            print(f"🔍 Applying filters: {filter_criteria}")
        
        episodes = get_user_study_episodes(filter_by=filter_criteria if filter_criteria else None)
    
    if not episodes:
        print("❌ No episodes found matching criteria.")
        return
    
    # Show statistics
    if not args.stats_only:
        stats = get_intervention_statistics(episodes)
        print(f"\n📊 Found {stats['total_episodes']} episodes:")
        
        if 'intervention_distributions' in stats and stats['intervention_distributions']:
            print("🧪 Intervention breakdown:")
            for dimension, counts in stats['intervention_distributions'].items():
                print(f"  {dimension}: {dict(counts)}")
        
        print(f"💬 Conversation length: avg {stats['conversation_length_stats']['average']:.1f} turns")
        print()
    
    # Export if requested
    if args.format:
        if args.format == 'csv':
            filename = export_episodes_to_enhanced_csv(episodes, args.output)
            print(f"✅ Exported {len(episodes)} episodes to CSV: {filename}")
        elif args.format == 'json':
            filename = export_episodes_to_enhanced_json(episodes, args.output)
            print(f"✅ Exported {len(episodes)} episodes to JSON: {filename}")
        return
    
    # Display episode list (if not exporting and not stats-only)
    if not args.stats_only:
        print("📋 Episodes:")
        for i, episode in enumerate(episodes):
            if args.verbose:
                from ui.database_utils import parse_episode_reasoning
                episode_data = parse_episode_reasoning(episode)
                interventions = episode_data.get('interventions', {})
                transparency = interventions.get('transparency', '?')
                warmth = interventions.get('warmth', '?')
                print(f"  {i+1:2d}. {episode.pk[:16]}... | T:{transparency} W:{warmth} | "
                      f"{len(episode.messages)} turns | {episode.environment} | {episode.tag}")
            else:
                print(f"  {i+1:2d}. {episode.pk[:16]}... | {len(episode.messages)} turns | {episode.tag}")
        
        if len(episodes) > 10:
            print(f"\n... showing first {min(10, len(episodes))} of {len(episodes)} episodes")
            print("Use --format csv/json to export all data, or --view-episode <id> for details")


if __name__ == "__main__":
    main()