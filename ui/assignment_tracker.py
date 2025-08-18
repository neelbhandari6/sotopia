"""
Assignment Tracking System for Balanced Personality-Based Agent Assignment

This module handles tracking and balancing agent assignments across personality types
and intervention conditions to ensure equal exposure for research validity.
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict, Counter

# Removed PersonalityAssignmentTracker Redis OM model
# Now using direct Redis JSON storage for simpler, more reliable assignment tracking


class BalancedAssignmentManager:
    """
    Manages balanced assignment of agents based on personality types and interventions.
    """
    
    @staticmethod
    def get_intervention_combination_key(interventions: Dict[str, str]) -> str:
        """Create a standardized key for intervention combinations"""
        # Sort interventions for consistent key generation
        sorted_interventions = sorted(interventions.items())
        return "_".join([f"{k}_{v}" for k, v in sorted_interventions])
    
    @staticmethod
    def get_personality_type_key(extroversion_level: str, agreeableness_level: str) -> str:
        """Create standardized personality type key"""
        return f"{extroversion_level}_ext_{agreeableness_level}_agree"
    
    @staticmethod
    def _get_tracker_key(personality_type: str, intervention_combination: str) -> str:
        """Generate Redis key for a tracker"""
        return f"assignment_tracker:{personality_type}:{intervention_combination}"
    
    @staticmethod
    def get_least_assigned_agent(
        available_agents: List[str], 
        personality_type: str, 
        intervention_combination: str
    ) -> str:
        """
        Get the agent that has been assigned least frequently for this 
        personality type + intervention combination.
        """
        try:
            import redis
            import json
            import os
            
            redis_url = os.getenv("REDIS_OM_URL", "redis://localhost:6379")
            r = redis.Redis.from_url(redis_url)
            
            # Get tracker data
            tracker_key = BalancedAssignmentManager._get_tracker_key(personality_type, intervention_combination)
            tracker_data = r.execute_command('JSON.GET', tracker_key)
            
            agent_assignments = {}
            if tracker_data:
                data = json.loads(tracker_data)
                agent_assignments = data.get('agent_assignments', {})
            
            # Count assignments for available agents
            agent_counts = {}
            for agent in available_agents:
                agent_counts[agent] = agent_assignments.get(agent, 0)
            
            # Find agent(s) with minimum assignments
            min_count = min(agent_counts.values()) if agent_counts else 0
            least_assigned_agents = [
                agent for agent, count in agent_counts.items() 
                if count == min_count
            ]
            
            # If multiple agents tied, return first one (could add randomization here)
            return least_assigned_agents[0]
            
        except Exception as e:
            print(f"Error getting least assigned agent: {e}")
            # Fallback to first available agent
            return available_agents[0] if available_agents else ""
    
    @staticmethod
    def record_assignment(
        agent_id: str, 
        personality_type: str, 
        intervention_combination: str,
        participant_id: str = ""
    ) -> bool:
        """
        Record an agent assignment and update the tracker.
        """
        try:
            import redis
            import json
            import os
            
            redis_url = os.getenv("REDIS_OM_URL", "redis://localhost:6379")
            r = redis.Redis.from_url(redis_url)
            
            # Get tracker key
            tracker_key = BalancedAssignmentManager._get_tracker_key(personality_type, intervention_combination)
            
            # Get existing data or create new
            tracker_data = r.execute_command('JSON.GET', tracker_key)
            if tracker_data:
                data = json.loads(tracker_data)
            else:
                data = {
                    "personality_type": personality_type,
                    "intervention_combination": intervention_combination,
                    "agent_assignments": {},
                    "total_assignments": 0,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }
            
            # Update assignment counts
            if agent_id not in data["agent_assignments"]:
                data["agent_assignments"][agent_id] = 0
            data["agent_assignments"][agent_id] += 1
            data["total_assignments"] += 1
            data["updated_at"] = datetime.now().isoformat()
            
            # Save updated data
            r.execute_command('JSON.SET', tracker_key, '$', json.dumps(data))
            
            print(f"Recorded assignment: {agent_id} for {personality_type} + {intervention_combination}")
            print(f"Updated counts: {data['agent_assignments']}")
            
            return True
            
        except Exception as e:
            print(f"Error recording assignment: {e}")
            return False
    
    @staticmethod
    def get_assignment_statistics() -> Dict[str, Any]:
        """
        Get comprehensive statistics about current assignment balance.
        """
        try:
            return BalancedAssignmentManager._get_stats_from_redis()
        except Exception as e:
            print(f"Error getting assignment statistics: {e}")
            return {
                "total_trackers": 0,
                "personality_types": [],
                "intervention_combinations": [], 
                "assignment_balance": {},
                "total_assignments": 0,
                "error": str(e),
                "status": "error"
            }
    
    @staticmethod  
    def _get_stats_from_redis() -> Dict[str, Any]:
        """Get statistics by reading Redis data directly (fallback method)"""
        import redis
        import json
        import os
        
        redis_url = os.getenv("REDIS_OM_URL", "redis://localhost:6379")
        r = redis.Redis.from_url(redis_url)
        
        # Get all assignment tracker keys
        keys = r.keys('assignment_tracker:*')
        
        stats = {
            "total_trackers": 0,  # Will count only valid records
            "personality_types": set(),
            "intervention_combinations": set(), 
            "assignment_balance": {},
            "total_assignments": 0,
            "excluded_count": 0  # Track how many were excluded
        }
        
        for key in keys:
            try:
                # Read JSON data directly
                raw_data = r.execute_command('JSON.GET', key)
                if raw_data:
                    data = json.loads(raw_data)
                    
                    personality_type = data.get('personality_type', 'unknown')
                    intervention_combination = data.get('intervention_combination', 'unknown')
                    total_assignments = data.get('total_assignments', 0)
                    agent_assignments = data.get('agent_assignments', {})
                    updated_at = data.get('updated_at', '')
                    
                    # Only count records with valid personality data
                    if personality_type and personality_type != 'unknown' and personality_type != 'None':
                        stats["total_trackers"] += 1
                        stats["personality_types"].add(personality_type)
                        stats["intervention_combinations"].add(intervention_combination)
                        stats["total_assignments"] += total_assignments
                        
                        # Store balance info
                        balance_key = f"{personality_type}__{intervention_combination}"
                        if balance_key in stats["assignment_balance"]:
                            # Merge with existing data (should not happen, but just in case)
                            existing = stats["assignment_balance"][balance_key]
                            existing["total"] += total_assignments
                            for agent, count in agent_assignments.items():
                                if agent in existing["agent_assignments"]:
                                    existing["agent_assignments"][agent] += count
                                else:
                                    existing["agent_assignments"][agent] = count
                        else:
                            stats["assignment_balance"][balance_key] = {
                                "personality_type": personality_type,
                                "intervention_combination": intervention_combination,
                                "agent_assignments": agent_assignments.copy(),
                                "total": total_assignments,
                                "updated_at": updated_at
                            }
                    else:
                        # Count excluded records for debugging
                        stats["excluded_count"] += 1
                        print(f"Excluding assignment record with personality_type: {personality_type}")
                        
            except Exception as e:
                print(f"Error reading assignment tracker record: {e}")
        
        # Convert sets to lists for JSON serialization
        stats["personality_types"] = list(stats["personality_types"])
        stats["intervention_combinations"] = list(stats["intervention_combinations"])
        
        # Add summary info
        if stats["excluded_count"] > 0:
            print(f"Assignment dashboard: Included {stats['total_assignments']} assignments with personality data, excluded {stats['excluded_count']} without")
        
        return stats
    
    @staticmethod
    def find_matching_agent_with_balancing(
        interventions: Dict[str, str],
        personality_classification: Dict[str, str],
        agent_dict: Dict[str, Dict[str, Any]]
    ) -> str:
        """
        Find agent that matches interventions AND ensures balanced assignment
        across personality types.
        """
        try:
            # Get intervention and personality keys
            intervention_key = BalancedAssignmentManager.get_intervention_combination_key(interventions)
            personality_key = personality_classification.get("personality_type", "unknown")
            
            print(f"Finding balanced agent for personality: {personality_key}, interventions: {intervention_key}")
            
            # Find agents that match the intervention pattern
            matching_agents = []
            target_transparency = interventions.get("transparency", "low").title()
            target_warmth = interventions.get("warmth", "low").title()
            target_expertise = interventions.get("expertise", "high").title()
            target_adaptability = interventions.get("adaptability", "high").title()
            target_theory_of_mind = interventions.get("theory_of_mind", "high").title()
            
            target_pattern = f"{target_transparency} Transparency, {target_warmth} Warmth, {target_adaptability} Adaptability, {target_expertise} Expertise, {target_theory_of_mind} Theory of Mind"
            
            for agent_key, agent_data in agent_dict.items():
                personality = agent_data.get("personality_and_values", "")
                if target_pattern in personality:
                    matching_agents.append(agent_key)
            
            if not matching_agents:
                print(f"No agents match intervention pattern: {target_pattern}")
                # Fallback to first available agent
                matching_agents = list(agent_dict.keys())[:1]
            
            print(f"Found {len(matching_agents)} matching agents: {matching_agents}")
            
            # Get the least assigned agent among matching ones
            selected_agent = BalancedAssignmentManager.get_least_assigned_agent(
                matching_agents, personality_key, intervention_key
            )
            
            print(f"Selected agent: {selected_agent}")
            return selected_agent
            
        except Exception as e:
            print(f"Error in balanced agent matching: {e}")
            # Fallback to original logic
            return list(agent_dict.keys())[0] if agent_dict else ""


def export_assignment_balance_report(filename: Optional[str] = None) -> str:
    """
    Export a comprehensive report of assignment balance across personality types.
    """
    if not filename:
        filename = f"assignment_balance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    try:
        stats = BalancedAssignmentManager.get_assignment_statistics()
        
        # Add summary analysis
        report = {
            "export_info": {
                "timestamp": datetime.now().isoformat(),
                "export_type": "assignment_balance_report"
            },
            "summary": stats,
            "balance_analysis": analyze_assignment_balance(stats),
            "recommendations": generate_balance_recommendations(stats)
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"Assignment balance report exported to: {filename}")
        return filename
        
    except Exception as e:
        print(f"Error exporting assignment balance report: {e}")
        return ""


def analyze_assignment_balance(stats: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze how balanced the current assignments are"""
    analysis = {
        "balance_score": 0.0,
        "imbalance_detected": False,
        "personality_balance": {},
        "intervention_balance": {}
    }
    
    try:
        if not stats["assignment_balance"]:
            return analysis
        
        # Analyze balance across personality types
        personality_totals = defaultdict(int)
        for combo_data in stats["assignment_balance"].values():
            personality_totals[combo_data["personality_type"]] += combo_data["total"]
        
        if personality_totals:
            max_assignments = max(personality_totals.values())
            min_assignments = min(personality_totals.values())
            balance_ratio = min_assignments / max_assignments if max_assignments > 0 else 1.0
            
            analysis["balance_score"] = balance_ratio
            analysis["imbalance_detected"] = balance_ratio < 0.8  # Threshold for imbalance
            analysis["personality_balance"] = dict(personality_totals)
        
        return analysis
        
    except Exception as e:
        print(f"Error analyzing assignment balance: {e}")
        return analysis


def generate_balance_recommendations(stats: Dict[str, Any]) -> List[str]:
    """Generate recommendations for improving assignment balance"""
    recommendations = []
    
    try:
        analysis = analyze_assignment_balance(stats)
        
        if analysis["imbalance_detected"]:
            recommendations.append("⚠️ Assignment imbalance detected across personality types")
            
            # Find under-represented personality types
            personality_counts = analysis["personality_balance"]
            if personality_counts:
                max_count = max(personality_counts.values())
                for personality, count in personality_counts.items():
                    if count < max_count * 0.8:
                        recommendations.append(f"📈 Recruit more participants with {personality} personality type")
        
        if not stats["assignment_balance"]:
            recommendations.append("📊 No assignment data available yet - start collecting data to track balance")
        else:
            recommendations.append("✅ Assignment tracking is active and collecting data")
        
        return recommendations
        
    except Exception as e:
        print(f"Error generating balance recommendations: {e}")
        return ["❌ Error analyzing balance - check system logs"]


if __name__ == "__main__":
    # Test the assignment system
    print("Testing Balanced Assignment Manager...")
    
    # Test getting statistics
    stats = BalancedAssignmentManager.get_assignment_statistics()
    print(f"Current assignment statistics: {json.dumps(stats, indent=2)}")
    
    # Test exporting report
    report_file = export_assignment_balance_report()
    print(f"Report exported to: {report_file}")