import random
import re
import sys
from collections import Counter
from typing import cast

import pandas as pd

from sotopia.database import EnvironmentProfile, EpisodeLog
from sotopia.envs.parallel import render_text_for_environment


def check_asymetry(
    epilogs: list[EpisodeLog],
) -> tuple[dict[str, int], dict[str, int]]:
    agent_1_models = []
    agent_2_models = []
    for ep in epilogs:
        assert isinstance(ep.models, list)
        agent_1_models.append(ep.models[1])
        agent_2_models.append(ep.models[2])

    agent_1_models_num = Counter(agent_1_models)
    agent_2_models_num = Counter(agent_2_models)
    return agent_1_models_num, agent_2_models_num


def select_episodes(episodes: list[EpisodeLog]) -> list[EpisodeLog]:
    selected_episodes: list[EpisodeLog] = []
    unique_envs = set([episode.environment for episode in episodes])
    for env in unique_envs:
        env_episodes = [
            episode for episode in episodes if episode.environment == env
        ]
        assert len(env_episodes) > 2
        # make sure we have symetric model pairs
        pair_one = env_episodes[0]
        pair_two = [
            episode
            for episode in env_episodes
            if episode.models != pair_one.models
        ][0]
        env_episodes = [pair_one, pair_two]
        selected_episodes += [random.choice(env_episodes)]
    return selected_episodes


def extract_background(text: str, name: str) -> str | None:
    start_marker = f"{name}'s background: "
    end_marker = "\n"

    start_index = text.find(start_marker)
    if start_index != -1:
        end_index = text.find(end_marker, start_index)
        if end_index != -1:
            substring = text[start_index + len(start_marker) : end_index]
            return substring.strip()
    return None


def extract_goals(input: str, participants: list[str]) -> dict[str, str]:
    # print('new:')
    # print(input)
    # print('end')
    # print()
    goals = {}
    for participant in participants:
        pattern = f"{participant}'s goal: ([^\n]+)"
        match = re.search(pattern, input)

        if match:
            goals[participant] = match.group(1)

            # Extract friend info if available
        friend_match = re.search(
            r"You know the following friends:(.*?)(?=\n\n|$)", input, re.DOTALL
        )
        if friend_match:
            friend_info = friend_match.group(1).strip()
            goals[participant] = (
                goals[participant]
                + " You know the following friends:\n"
                + friend_info
            )

    return goals


def extract_info(
    text: str, participants: list[str]
) -> tuple[str, str, str, str, str, str]:
    # Split the text into lines
    lines = text.strip().split("\n")

    scenario = None

    for line in lines:
        if line.startswith("Scenario:"):
            scenario = line[len("Scenario: ") :]

    if len(participants) == 2:
        beginning_1 = text.find(participants[1])
        end_1 = text.find("Conversation Starts:")
        remainder_1 = text[len(participants[1]) + beginning_1 : end_1]
        background_1 = extract_background(remainder_1, participants[0])
        start_2 = text.find(remainder_1)
        end_2 = text.find(
            "Conversation Starts:", end_1 + len("Conversation Starts:")
        )
        remainder_2 = text[
            start_2 + len(remainder_1) : len("Conversation Starts") + end_2
        ]
        background_2 = extract_background(remainder_2, participants[1])

        episode_start = text[
            (text.find(remainder_2) + len(remainder_2) + 1) : len(text)
        ]
        episode_start.lstrip()
        goals = extract_goals(remainder_1, participants)
        goals2 = extract_goals(remainder_2, participants)
    else:
        raise ValueError("Only 2 participants are supported")
    assert scenario is not None, "Scenario is None"
    assert background_1 is not None, "Background 1 is None"
    assert background_2 is not None, "Background 2 is None"

    return (
        scenario,
        background_1,
        background_2,
        goals[participants[0]],
        goals2[participants[1]],
        episode_start,
    )


# go through each of the 120 episodes from 6_initial_aug3
def episodes_to_csv(episodes: list[EpisodeLog], output_file: str) -> None:
    # make df
    mturk_df = pd.DataFrame(
        data=None,
        columns=[
            "episode_id",
            "scenario",
            "participants",
            "p1_name",
            "p2_name",
            "p1_background",
            "p2_background",
            "p1_goal",
            "p2_goal",
            "episode_part1",
            "episode_part2",
            "episode_part3",
            "episode_part4",
            "episode_part5",
            "episode_part6",
            "episode_part7",
            "episode_part8",
            "episode_part9",
            "episode_part10",
            "episode_part11",
        ],
    )
    for episode in episodes:
        agent_profiles, messages_and_rewards = episode.render_for_humans()
        participant1_name = (
            agent_profiles[0].first_name + " " + agent_profiles[0].last_name
        )
        participant2_name = (
            agent_profiles[1].first_name + " " + agent_profiles[1].last_name
        )
        participants = participant1_name + " and " + participant2_name
        (
            scenario,
            background_1,
            background_2,
            goal_1,
            goal_2,
            episode_start,
        ) = extract_info(
            messages_and_rewards[0], [participant1_name, participant2_name]
        )

        # special fix for mututal friends
        episode_env = EnvironmentProfile.get(episode.environment)
        if episode_env.source == "mutual_friends":
            scenario = render_text_for_environment(episode_env.scenario)

        # print(messages_and_rewards[0])
        # print()

        # we already have episode_start (episode_part1), now get the rest of the episode part 2-11
        episode_list = []
        for i in range(1, len(messages_and_rewards) - 2):
            episode_list.append(messages_and_rewards[i])

        if len(episode_list) < 20:
            episode_list += [""] * (20 - len(episode_list))

        new_row = {}
        new_row = {
            "episode_id": episode.pk,
            "scenario": scenario,
            "participants": participants,
            "p1_name": participant1_name,
            "p2_name": participant2_name,
            "p1_background": background_1,
            "p2_background": background_2,
            "p1_goal": goal_1,
            "p2_goal": goal_2,
            "episode_part1": episode_start,
            "episode_part2": episode_list[0],
            "episode_part3": episode_list[1],
            "episode_part4": episode_list[2],
            "episode_part5": episode_list[3],
            "episode_part6": episode_list[4],
            "episode_part7": episode_list[5],
            "episode_part8": episode_list[6],
            "episode_part9": episode_list[7],
            "episode_part10": episode_list[8],
            "episode_part11": episode_list[9],
            "episode_part12": episode_list[10],
            "episode_part13": episode_list[11],
            "episode_part14": episode_list[12],
            "episode_part15": episode_list[13],
            "episode_part16": episode_list[14],
            "episode_part17": episode_list[15],
            "episode_part18": episode_list[16],
            "episode_part19": episode_list[17],
            "episode_part20": episode_list[18],
            "episode_part21": episode_list[19],
        }

        df_dictionary = pd.DataFrame([new_row])
        mturk_df = pd.concat([mturk_df, df_dictionary], ignore_index=True)

    print(mturk_df.shape)
    mturk_df.to_csv(output_file, index=False)


episodes = EpisodeLog.find(
    EpisodeLog.tag == "aug18_gpt3.5_llama-2-70b-chat_zqi2"
).all()
print("Number of episodes:", len(episodes))
episodes_list: list[EpisodeLog] = cast(list[EpisodeLog], episodes)
selected_episodes = select_episodes(episodes_list)
print("Number of selected episodes:", len(selected_episodes))

agent1_models_count, agent2_models_count = check_asymetry(selected_episodes)
print("agent 1 Models count:", agent1_models_count)
print("agent 2 Models count:", agent2_models_count)

output_file = "annotation/mturk_aug18_gpt3.5_llama2_zqi2.csv"
episodes_to_csv(selected_episodes, output_file)
