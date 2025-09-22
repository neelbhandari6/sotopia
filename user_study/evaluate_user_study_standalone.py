#!/usr/bin/env python3
"""
Standalone script to evaluate conversation logs using BOTH JobNegotiationDimensions and SotopiaDimensions
with proper point calculation rubrics included - NO Redis required.

This script processes user_study_hiring_episodes.jsonl and evaluates each episode with both dimension sets
in a single run, including the specific point calculation rubrics.

Usage:
    python evaluate_user_study_standalone.py --input user_study_hiring_episodes.jsonl --output user_study_scores_dual.jsonl
"""

import json
import asyncio
import argparse
import time
import random
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field, validator

# Import only what we need from Sotopia - no Redis dependencies
from sotopia.generation_utils import PydanticOutputParser, agenerate


# Define evaluation dimensions directly in this script (copied from reproduce_data)
class SotopiaDimensions(BaseModel):
    deal_made: Tuple[str, int] = Field(
        ...,
        description="Please provide a comprehensive analysis on whether the agents have reached an agreement (Hint: pay more attention to the last few rounds to determine whether they have made an agreement). Remember a verbal agreement is sufficient and necessary. In the 'reasoning' field, provide a comprehensive account of the logic or thought process that led you to your conclusion. Further, provide an integer score in [0, 1] the 'score' field. 0 represents no agreement, 1 represents agreement.",
    )

    point: Tuple[str, int] = Field(
        ...,
        description="Please first reiterate the rubics for the point evaluation, then provide a comprehensive analysis on agent's performance measured by points. In 'reasoning' field you should first find out if the agents are willing to go ahead with the current offer (CHECK YOUR EVALUATION IN DEAL_MADE DIMENSION), if your answer is yes (i.e. your score is 1), then use the rubics presented in corresponding agents' goals to determine the points they got (USE LINEAR COMBINATION OF THE NEAREST LEVEL if there are no matching level). If no (i.e. your score is 0) then first list the score levels and use the averaged score of all levels IN CURRENT NEGOTIATION (NOT THE NEXT ONE). In 'score' field, provide your calculated average points. [Example] In the conversation the candidate is not satisfied with the offer of $150000, then the points should **NOT** be based on this number, but **the averaged score of all levels** in the current negotiation. Also be careful that there are multiple dimensions and you have to get the average separately and then add them up.",
    )

    transactivity: Tuple[str, int] = Field(
        ...,
        description="Analyze the provided social interaction episode between the given pair/team, focusing on identifying instances of transactive exchanges. Evaluate the level of transactivity by considering the following aspects: elaboration, building upon ideas, questioning, argumentation. Analyze whether these transactive patterns persist consistently across the entire interaction or if there are notable variations throughout the exchange. In the 'reasoning' field, provide a comprehensive account of the logic and thought process that led to your conclusion. Consider how the observed instances of transactivity contribute to or detract from the overall quality and depth of the interaction. In the 'score' field, provide an integer score ranging from 0 to 10, where a higher score indicates a higher level of transactivity."
    )

    verbal_equity: Tuple[str, int] = Field(
        ...,
        description="Analyze the script and measure the level of verbal equity reflected in the interaction between the agents. And then analyze the extent to which the interaction shows a balanced distribution of speaking opportunities among team members. In the 'reasoning' field, provide a comprehensive account of the logic or thought process that led you to your conclusion. Further, provide an integer score ranging from 0 and 10 in the 'score' field. A higher score indicates a higher level of verbal equity."
    )

    @validator("point", allow_reuse=True)
    def int_validator(cls, v: Tuple[str, int]) -> Tuple[str, int]:
        assert isinstance(v[1], int)
        return v

    @validator("deal_made", allow_reuse=True)
    def zero_or_one_validator(cls, v: Tuple[str, int]) -> Tuple[str, int]:
        assert v[1] == 0 or v[1] == 1
        return v

    @validator("transactivity", "verbal_equity", allow_reuse=True)
    def zero_to_ten_validator(cls, v: Tuple[str, int]) -> Tuple[str, int]:
        assert v[1] >= 0 and v[1] <= 10
        return v


class JobNegotiationDimensions(BaseModel):
    # Satisfaction questions
    satisfaction_1: Tuple[str, int] = Field(
        ...,
        description="You are asked to complete a survey question: How satisfied are you with your overall experience during this interaction? Please first share your thoughts on why you rated this way, and then rate your level of agreement on a scale from 1 to 5, in which 1: Strongly Disagree, 2: Disagree, 3: Neutral, 4: Agree, 5: Strongly Agree."
    )
    satisfaction_2: Tuple[str, int] = Field(
        ...,
        description="You are asked to complete a survey question: How satisfied are you with your interlocutor's performance during this interaction? Please first share your thoughts on why you rated this way, and then rate your level of agreement on a scale from 1 to 5, in which 1: Strongly Disagree, 2: Disagree, 3: Neutral, 4: Agree, 5: Strongly Agree."
    )
    satisfaction_3: Tuple[str, int] = Field(
        ...,
        description="You are asked to complete a survey question: How satisfied are you with your own performance during this interaction? Please first share your thoughts on why you rated this way, and then rate your level of agreement on a scale from 1 to 5, in which 1: Strongly Disagree, 2: Disagree, 3: Neutral, 4: Agree, 5: Strongly Agree."
    )

    # Effort / Frustration questions
    effort_score: Tuple[str, int] = Field(
        ...,
        description="You are asked to complete a survey question: How hard did you have to work to accomplish your level of performance during the interaction? Please first share your thoughts on why you rated this way, and then rate your level of agreement on a scale from 1 to 5, in which 1: Very Little Effort, 2: Little Effort, 3: Moderate Effort, 4: Much Effort, 5: Extreme Effort."
    )
    frustration_score: Tuple[str, int] = Field(
        ...,
        description="You are asked to complete a survey question: How insecure, discouraged, irritated, stressed, and annoyed were you during the interaction? Please first share your thoughts on why you rated this way, and then rate your level of agreement on a scale from 1 to 5, in which 1: Not at all, 2: A little, 3: Moderately, 4: Quite a bit, 5: Extremely."
    )

    # Personal perception questions
    trustworthy_score: Tuple[str, int] = Field(
        ...,
        description="You are asked to complete a survey question: I believe that the interlocutor is trustworthy. Please first share your thoughts on why you rated this way, and then rate your level of agreement on a scale from 1 to 5, in which 1: Strongly Disagree, 2: Disagree, 3: Neutral, 4: Agree, 5: Strongly Agree."
    )
    honest_score: Tuple[str, int] = Field(
        ...,
        description="You are asked to complete a survey question: I believe that the interlocutor is honest. Please first share your thoughts on why you rated this way, and then rate your level of agreement on a scale from 1 to 5, in which 1: Strongly Disagree, 2: Disagree, 3: Neutral, 4: Agree, 5: Strongly Agree."
    )
    dependable_score: Tuple[str, int] = Field(
        ...,
        description="You are asked to complete a survey question: I believe that the interlocutor is dependable. Please first share your thoughts on why you rated this way, and then rate your level of agreement on a scale from 1 to 5, in which 1: Strongly Disagree, 2: Disagree, 3: Neutral, 4: Agree, 5: Strongly Agree."
    )
    reliable_score: Tuple[str, int] = Field(
        ...,
        description="You are asked to complete a survey question: I believe that the interlocutor is reliable. Please first share your thoughts on why you rated this way, and then rate your level of agreement on a scale from 1 to 5, in which 1: Strongly Disagree, 2: Disagree, 3: Neutral, 4: Agree, 5: Strongly Agree."
    )

    @validator("satisfaction_1", "satisfaction_2", "satisfaction_3",
               "effort_score", "frustration_score",
               "trustworthy_score", "honest_score", "dependable_score", "reliable_score",
               allow_reuse=True)
    def one_to_five_validator(cls, v: Tuple[str, int]) -> Tuple[str, int]:
        assert v[1] >= 1 and v[1] <= 5
        return v


class EvaluationForTwoAgents(BaseModel):
    agent_1_evaluation: Any  # Will be JobNegotiationDimensions or SotopiaDimensions
    agent_2_evaluation: Any


# Point calculation rubrics from the scenario files
HIRING_SCENARIOS = {
    "job_interview_competitive": {
        "hiring_manager_goals": """You are the Hiring Manager. The job candidate has already received a job offer from your company, and now you will be discussing the final agreement.
Salary: the job candidate's salary can range from $100,000 to $120,000. There are 5 different amounts you and the job candidate can agree on, and each is associated with a different number of points for you. $120,000 gets you 0 points, $115,000 gets you 1500 points, $110,000 gets you 3000 points, $105,000 gets you 4500 points, and $100,000 gets you 6000 points.
Starting Date: the job candidate's starting date can range from June 1 to August 1. There are 5 different dates you and the job candidate can agree on, and each is associated with a different number of points for you. June 1 gets you 0 points, June 15 gets you 600 points, July 1 gets you 1200 points, July 15 gets you 1800 points, and August 1 gets you 2400 points.
These are the only choices you have, and you cannot offer other bonuses. The maximum points you can get is 8400, and the minimum is 0.""",

        "candidate_goals": """You are the job candidate for the company. A position has already been offered, and you will be negotiating with the hiring manager on the following concerns.
Salary: Your salary can range from $100,000 to $120,000. There are 5 different amounts you can agree on, each associated with a different number of points for you. $120,000 gives you 6000 points, $115,000 gives you 4500 points, $110,000 gives you 3000 points, $105,000 gives you 1500 points, and $100,000 gives you 0 points.
Starting Date: Your starting date can range from June 1 to August 1. There are 5 different dates you can agree on, each associated with a different number of points for you. June 1 gives you 2400 points, June 15 gives you 1800 points, July 1 gives you 1200 points, July 15 gives you 600 points, and August 1 gives you 0 points.
These are the only choices you have and you cannot request for other bonuses. The maximum points you can get is 8400, and the minimum is 0."""
    },

    "job_interview_cooperative": {
        "hiring_manager_goals": """You are the Hiring Manager. The job candidate has already received a job offer from your company, and now you will be discussing the final agreement.
Salary: the job candidate's salary can range from $100,000 to $120,000. There are 5 different amounts you and the job candidate can agree on, and each is associated with a different number of points for you. $120,000 gets you 0 points, $115,000 gets you 1500 points, $110,000 gets you 3000 points, $105,000 gets you 4500 points, and $100,000 gets you 6000 points.
Starting Date: the job candidate's starting date can range from June 1 to August 1. There are 5 different dates you and the job candidate can agree on, and each is associated with a different number of points for you. June 1 gets you 0 points, June 15 gets you 600 points, July 1 gets you 1200 points, July 15 gets you 1800 points, and August 1 gets you 2400 points.
These are the only choices you have, and you cannot offer other bonuses. The maximum points you can get is 8400, and the minimum is 0.""",

        "candidate_goals": """You are the job candidate for the company. A position has already been offered, and you will be negotiating with the hiring manager on the following concerns.
Salary: Your salary can range from $100,000 to $120,000. There are 5 different amounts you can agree on, each associated with a different number of points for you. $120,000 gives you 6000 points, $115,000 gives you 4500 points, $110,000 gives you 3000 points, $105,000 gives you 1500 points, and $100,000 gives you 0 points.
Starting Date: Your starting date can range from June 1 to August 1. There are 5 different dates you can agree on, each associated with a different number of points for you. June 1 gives you 800 points, June 15 gives you 600 points, July 1 gives you 400 points, July 15 gives you 200 points, and August 1 gives you 0 points.
These are the only choices you have and you cannot request for other bonuses. The maximum points you can get is 6800, and the minimum is 0."""
    }
}


def create_conversation_history_with_goals(messages: List[Dict], scenario_id: str) -> str:
    """Create a formatted conversation history with goal contexts for LLM evaluation"""

    # Get the appropriate scenario goals
    scenario_goals = HIRING_SCENARIOS.get(scenario_id, HIRING_SCENARIOS["job_interview_competitive"])

    # Create conversation history
    history_lines = ["=== AGENT GOALS AND POINT RUBRICS ==="]
    history_lines.append("")
    history_lines.append("HIRING MANAGER (AI Agent) GOALS:")
    history_lines.append(scenario_goals["hiring_manager_goals"])
    history_lines.append("")
    history_lines.append("JOB CANDIDATE (Human Participant) GOALS:")
    history_lines.append(scenario_goals["candidate_goals"])
    history_lines.append("")
    history_lines.append("=== CONVERSATION LOG ===")
    history_lines.append("")

    # Add conversation messages
    for msg in messages:
        speaker = msg["speaker"]
        content = msg["content"]

        if msg.get("action_type") == "leave":
            history_lines.append(f"{speaker} left the conversation.")
        else:
            history_lines.append(f"{speaker}: {content}")

    return "\n".join(history_lines)


async def evaluate_with_dimension_set(
    episode_data: Dict,
    dimension_name: str,
    dimension_class,
    model_name: str = "gpt-4o",
    max_retries: int = 3
) -> Dict[str, Any]:
    """
    Evaluate a single episode with a specific dimension set using direct LLM call with retry logic
    """

    # Convert messages to evaluation format with goals and point rubrics
    messages = episode_data["messages"]
    scenario_id = episode_data.get("scenario_id", "job_interview_competitive")

    # Create history that includes both conversation AND the point calculation rubrics
    history = create_conversation_history_with_goals(messages, scenario_id)

    # Create the evaluation format class dynamically
    class TwoAgentEval(BaseModel):
        agent_1_evaluation: dimension_class
        agent_2_evaluation: dimension_class

    last_error = None

    for attempt in range(max_retries + 1):
        try:
            # Run the LLM evaluation directly using EXACT same template as original EpisodeLLMEvaluator
            response = await agenerate(
                model_name=model_name,
                template="""{history},
                        Based on previous interactions, evaluate how well participants achieve their goals.
                        Please following the format:
                        {format_instructions}
                    """,
                input_values=dict(history=history),
                output_parser=PydanticOutputParser[TwoAgentEval](pydantic_object=TwoAgentEval),
                temperature=0.0,
                structured_output=model_name.startswith("custom/structured"),
            )

            # Process results into readable format
            processed_results = {
                "dimension_set": dimension_name,
                "agent_1_scores": {},  # AI/Hiring Manager
                "agent_2_scores": {},  # Human/Candidate
            }

            # Extract scores for each agent and dimension
            for dimension in response.agent_1_evaluation.dict().keys():
                processed_results["agent_1_scores"][dimension] = {
                    "score": response.agent_1_evaluation.dict()[dimension][1],
                    "reasoning": response.agent_1_evaluation.dict()[dimension][0]
                }
                processed_results["agent_2_scores"][dimension] = {
                    "score": response.agent_2_evaluation.dict()[dimension][1],
                    "reasoning": response.agent_2_evaluation.dict()[dimension][0]
                }

            # If we get here, the evaluation succeeded
            if attempt > 0:
                print(f"  ✓ Retry {attempt} succeeded for {dimension_name}")
            return processed_results

        except Exception as e:
            last_error = e

            if attempt < max_retries:
                # Calculate exponential backoff with jitter
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                print(f"  ⚠ Attempt {attempt + 1} failed for {dimension_name}: {str(e)[:100]}...")
                print(f"    Retrying in {wait_time:.1f} seconds...")
                await asyncio.sleep(wait_time)
            else:
                # Final attempt failed
                print(f"  ✗ All {max_retries + 1} attempts failed for {dimension_name}")

    # All retries exhausted
    return {
        "dimension_set": dimension_name,
        "error": f"Failed after {max_retries + 1} attempts. Last error: {str(last_error)}",
        "attempts": max_retries + 1
    }


async def evaluate_episode_dual_dimensions(
    episode_data: Dict,
    model_name: str = "gpt-4o",
    max_retries: int = 3
) -> Dict[str, Any]:
    """
    Evaluate a single episode using BOTH JobNegotiationDimensions and SotopiaDimensions with retry logic
    """

    episode_id = episode_data["episode_id"]
    scenario_id = episode_data.get("scenario_id", "job_interview_competitive")

    print(f"Evaluating episode {episode_id} ({scenario_id}) with both dimension sets...")

    # Evaluate with both dimension sets
    job_results = await evaluate_with_dimension_set(
        episode_data,
        "JobNegotiationDimensions",
        JobNegotiationDimensions,
        model_name,
        max_retries
    )

    # Add delay between evaluations to respect rate limits
    await asyncio.sleep(1)

    sotopia_results = await evaluate_with_dimension_set(
        episode_data,
        "SotopiaDimensions",
        SotopiaDimensions,
        model_name,
        max_retries
    )

    # Combine results
    combined_results = {
        "episode_id": episode_id,
        "scenario_id": scenario_id,
        "conversation_length": episode_data.get("conv_length", len(episode_data["messages"])),
        "evaluation_model": model_name,
        "point_rubrics_included": True,
        "scenario_goals": HIRING_SCENARIOS.get(scenario_id, HIRING_SCENARIOS["job_interview_competitive"]),
        "evaluations": {
            "job_negotiation_dimensions": job_results,
            "sotopia_dimensions": sotopia_results
        }
    }

    # Check for errors
    if "error" in job_results:
        print(f"✗ Error in JobNegotiationDimensions for episode {episode_id}: {job_results['error']}")
    if "error" in sotopia_results:
        print(f"✗ Error in SotopiaDimensions for episode {episode_id}: {sotopia_results['error']}")

    if "error" not in job_results and "error" not in sotopia_results:
        print(f"✓ Successfully evaluated episode {episode_id} with both dimension sets")

        # Show point scores if available from sotopia dimensions (includes points)
        if "point" in sotopia_results["agent_1_scores"]:
            ai_points = sotopia_results["agent_1_scores"]["point"]["score"]
            human_points = sotopia_results["agent_2_scores"]["point"]["score"]
            print(f"  Points: AI={ai_points}, Human={human_points}")

    return combined_results


async def evaluate_jsonl_file_dual_dimensions(
    input_file: str,
    output_file: str,
    model_name: str = "gpt-4o",
    max_episodes: int = None,
    max_retries: int = 3
):
    """
    Evaluate all episodes in a JSONL file with both dimension sets and save results with retry logic
    """

    print(f"Loading episodes from {input_file}...")
    episodes = []

    with open(input_file, 'r') as f:
        for i, line in enumerate(f):
            if max_episodes and i >= max_episodes:
                break
            episodes.append(json.loads(line.strip()))

    print(f"Found {len(episodes)} episodes to evaluate with BOTH dimension sets")
    print(f"Retry configuration: {max_retries + 1} attempts per evaluation")

    # Check scenarios present in the data
    scenarios = set(ep.get("scenario_id", "unknown") for ep in episodes)
    print(f"Scenarios found: {sorted(scenarios)}")

    # Evaluate each episode with both dimension sets
    results = []
    for i, episode in enumerate(episodes):
        print(f"\n--- Evaluating episode {i+1}/{len(episodes)} ---")
        result = await evaluate_episode_dual_dimensions(
            episode,
            model_name=model_name,
            max_retries=max_retries
        )
        results.append(result)

        # Add delay between episodes to respect rate limits
        if i < len(episodes) - 1:
            await asyncio.sleep(2)

    # Save results
    print(f"\nSaving results to {output_file}...")
    with open(output_file, 'w') as f:
        for result in results:
            f.write(json.dumps(result, indent=None) + '\n')

    print(f"✓ Evaluation complete! Results saved to {output_file}")

    # Print summary statistics
    successful_job_evaluations = [r for r in results if "error" not in r["evaluations"]["job_negotiation_dimensions"]]
    successful_sotopia_evaluations = [r for r in results if "error" not in r["evaluations"]["sotopia_dimensions"]]

    print(f"\n=== Summary ===")
    print(f"Total episodes: {len(episodes)}")
    print(f"Successfully evaluated with JobNegotiationDimensions: {len(successful_job_evaluations)}")
    print(f"Successfully evaluated with SotopiaDimensions: {len(successful_sotopia_evaluations)}")


def main():
    parser = argparse.ArgumentParser(description="Standalone evaluation using BOTH JobNegotiationDimensions and SotopiaDimensions with point calculation rubrics and retry logic - NO Redis required")
    parser.add_argument("--input", required=True, help="Input JSONL file with conversation logs")
    parser.add_argument("--output", required=True, help="Output JSONL file for evaluation results")
    parser.add_argument("--model", default="gpt-4o", help="LLM model for evaluation (default: gpt-4o)")
    parser.add_argument("--max-episodes", type=int, help="Maximum number of episodes to evaluate")
    parser.add_argument("--max-retries", type=int, default=3, help="Maximum number of retry attempts per evaluation (default: 3)")

    args = parser.parse_args()

    print(f"Starting STANDALONE dual-dimension evaluation with retry logic (NO Redis required):")
    print(f"  Input file: {args.input}")
    print(f"  Output file: {args.output}")
    print(f"  Model: {args.model}")
    print(f"  Dimensions: BOTH JobNegotiationDimensions AND SotopiaDimensions")
    print(f"  Point rubrics: Included for both competitive and cooperative scenarios")
    print(f"  Retry attempts: {args.max_retries + 1} attempts per evaluation")
    if args.max_episodes:
        print(f"  Max episodes: {args.max_episodes}")

    # Run the evaluation
    asyncio.run(evaluate_jsonl_file_dual_dimensions(
        input_file=args.input,
        output_file=args.output,
        model_name=args.model,
        max_episodes=args.max_episodes,
        max_retries=args.max_retries
    ))


if __name__ == "__main__":
    main()