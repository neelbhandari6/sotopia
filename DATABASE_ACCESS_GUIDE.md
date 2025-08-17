# 🗄️ Enhanced Database Access Guide

This comprehensive guide explains how to access, query, and export user study conversation data from the Redis database, including advanced intervention dimension analysis.

## 📍 **Database Location**

The user study data is saved to a **Redis database** using the same system as agent-agent simulations.

### **Database URL**
- **Default**: `redis://localhost:6379`
- **Environment Variable**: `REDIS_OM_URL`
- **Current Setting**: Check with `echo $REDIS_OM_URL`

## 🚀 **Quick Access Methods**

### **1. Enhanced Database Script** (🌟 Recommended)
```bash
cd /usr2/mingqia2/sotopia

# Comprehensive database summary
python scripts/enhanced_database_access.py --summary

# Export high transparency episodes to CSV
python scripts/enhanced_database_access.py --filter interventions.transparency=high --format csv

# View specific episode details
python scripts/enhanced_database_access.py --view-episode EPISODE_ID_HERE

# Get episodes from last 7 days
python scripts/enhanced_database_access.py --recent-days 7 --format json

# Filter by multiple criteria
python scripts/enhanced_database_access.py --filter interventions.transparency=high interventions.warmth=low scenario=hiring_scenario_1 --format csv
```

**Advanced Features:**
- ✅ Filter by intervention dimensions (transparency, warmth, expertise, adaptability, theory_of_mind)
- ✅ Filter by scenario, agent, date range, conversation length
- ✅ Enhanced CSV/JSON exports with agent attributes
- ✅ Detailed episode viewing with conversation analysis
- ✅ Comprehensive statistics and intervention breakdowns

### **2. Streamlit Interface** (User-Friendly)
Access through the user study web interface:
- **💾 Save to Database** - Saves conversations with full intervention data
- **📊 Database Summary** - View statistics and episode counts
- **🔎 Browse Episodes** - Select and view individual conversations
- **💾 Export Database** - Download comprehensive CSV/JSON exports

### **3. Legacy Scripts** (Still Available)
```bash
# Original browser (basic functionality)
python scripts/browse_database.py

# Original export script
python scripts/access_user_study_data.py --format csv
```

### **4. Advanced Python Access**
```python
# Enhanced database utilities
from ui.database_utils import (
    get_user_study_episodes, 
    get_episodes_by_intervention,
    get_intervention_statistics,
    export_episodes_to_enhanced_csv
)

# Get episodes with specific interventions
high_transparency_episodes = get_episodes_by_intervention('transparency', 'high')

# Get episodes with complex filtering
filter_criteria = {
    'interventions': {'transparency': 'high', 'warmth': 'low'},
    'min_turns': 5,
    'date_from': '2024-07-01'
}
filtered_episodes = get_user_study_episodes(filter_by=filter_criteria)

# Get comprehensive statistics
stats = get_intervention_statistics(filtered_episodes)
print(f"Total episodes: {stats['total_episodes']}")
print(f"Intervention breakdown: {stats['intervention_distributions']}")
```

## 🔧 **Setting Up Redis Database Connection**

### **Docker Redis with RedisJSON (Recommended Setup)**
```bash
# Use port 6380 to avoid conflicts (no sudo needed)
docker run -d -p 6380:6379 --name sotopia-redis-json redis/redis-stack-server:latest

# Set environment variable to new port
export REDIS_OM_URL='redis://localhost:6380'

# Test connection
redis-cli -p 6380 ping

# Verify RedisJSON is loaded
redis-cli -p 6380 MODULE LIST
```

### **Complete Setup & Launch Workflow**
```bash
# 1. Start Redis with RedisJSON
docker run -d -p 6380:6379 --name sotopia-redis-json redis/redis-stack-server:latest

# 2. Set environment variable
export REDIS_OM_URL='redis://localhost:6380'

# 3. Navigate to project and activate environment
cd /usr2/mingqia2/sotopia
source .venv/bin/activate

# 4. Test database connection
python -c "
from sotopia.database import EpisodeLog
print('✅ Database connection successful!')
episodes = EpisodeLog.find().all()
print(f'Found {len(episodes)} existing episodes')
"

# 5. Launch sotopia interface
streamlit run ui/app.py
```

### **Environment Variable Persistence**
```bash
# Make environment variable persistent
echo 'export REDIS_OM_URL="redis://localhost:6380"' >> ~/.bashrc
source ~/.bashrc

# Verify it's set
echo $REDIS_OM_URL
```

## 📊 **Enhanced Data Structure**

### **User Study Episodes** (New Format)
Each user study conversation is now saved as an enhanced `EpisodeLog` with comprehensive intervention and agent data:

```json
{
  "pk": "episode_id",
  "environment": "scenario_name", 
  "agents": ["ai_agent_name", "human_participant"],
  "tag": "user_study_20240730_143502_abc12345",
  "models": ["transparency_high", "warmth_low", "expertise_high", "adaptability_high", "theory_of_mind_high", "human"],
  "messages": [
    [["Human", "speak", "Hello, how are you?"]],
    [["AI_Agent", "speak", "I'm doing well, thank you!"]]
  ],
  "reasoning": {
    "study_type": "user_study_human_ai_conversation",
    "session_id": "user_study_20240730_143502_abc12345",
    "timestamp": "2024-07-30T14:35:02.123456",
    "interventions": {
      "transparency": "high",
      "warmth": "low", 
      "expertise": "high",
      "adaptability": "high",
      "theory_of_mind": "high"
    },
    "scenario_id": "hiring_scenario_competitive", 
    "agent_id": "hiring_agent_0",
    "agent_attributes": {
      "name": "Sarah Johnson",
      "occupation": "Marketing Manager",
      "age": "28",
      "decision_making_style": "Analytical and data-driven...",
      "big_five": "High openness, moderate conscientiousness...",
      "mbti": "INTJ"
    },
    "conversation_stats": {
      "total_turns": 12,
      "human_messages": 6,
      "ai_messages": 6,
      "avg_message_length": 78.5
    },
    "survey_responses": {
      "transparency": 4,
      "warmth": 3,
      "theory_of_mind": 5,
      "adaptability": 4,
      "expertise": 4,
      "goals": 6,
      "satisfaction": 5,
      "conflict_resolve": 4,
      "believability": 5,
      "transactivity": 3,
      "truthfulness": 6
    },
    "prolific_data": {
      "PROLIFIC_PID": "abc123def456",
      "STUDY_ID": "study_789",
      "SESSION_ID": "session_101112"
    }
  },
  "rewards": [0.0, 0.0]
}
```

### **Enhanced Key Fields**
- **`reasoning`**: Now structured JSON with comprehensive study metadata
- **`interventions`**: All five intervention dimensions stored systematically  
- **`agent_attributes`**: Complete AI agent profile information
- **`conversation_stats`**: Automatically calculated conversation metrics
- **`survey_responses`**: Post-study survey data with manipulation checks and outcome measures
- **`prolific_data`**: Prolific participant IDs and study metadata
- **`models`**: Now includes all intervention dimensions for easier querying
- **`session_id`**: Unique identifier for tracking individual study sessions

## 📋 **Survey Data Access**

### **Survey Data Structure**
The post-study survey captures participant perceptions and is stored in `reasoning.survey_responses`:

```json
{
  "survey_responses": {
    "transparency": 4,        // Manipulation check: AI explained reasoning (1-5 scale)
    "warmth": 3,             // Manipulation check: AI was friendly/caring (1-5 scale)  
    "theory_of_mind": 5,     // Manipulation check: AI understood perspective (1-5 scale)
    "adaptability": 4,       // Manipulation check: AI was flexible (1-5 scale)
    "expertise": 4,          // Manipulation check: AI was well-informed (1-5 scale)
    "goals": 6,              // Outcome: Success in achieving goals (1-7 scale)
    "satisfaction": 5,       // Outcome: Satisfaction with negotiation (1-7 scale)
    "conflict_resolve": 4,   // Outcome: Success resolving conflicts (1-7 scale)
    "believability": 5,      // Outcome: AI seemed natural/realistic (1-7 scale)
    "transactivity": 3,      // Outcome: AI engaged with user points (1-5 scale)
    "truthfulness": 6        // Outcome: AI was truthful (1-7 scale)
  }
}
```

### **Survey Question Details**

**Manipulation Checks (1-5 Likert Scale):**
1. **transparency**: "The AI clearly explained its reasoning and decision-making process"
2. **warmth**: "The AI communicated in a friendly and caring manner"  
3. **theory_of_mind**: "The AI seemed to understand my perspective and intentions"
4. **adaptability**: "The AI was flexible in its approach to our conversations"
5. **expertise**: "The AI seemed well-informed about the topics we discussed"

**Interaction Outcomes:**
1. **goals**: "How successful were you in achieving your goals?" (1-7 scale)
2. **satisfaction**: "How satisfied are you with the outcome?" (1-7 scale)
3. **conflict_resolve**: "How successfully did you resolve conflicts?" (1-7 scale)
4. **believability**: "How natural/realistic did the AI seem?" (1-7 scale)
5. **transactivity**: "How well did the AI engage with your points?" (1-5 scale)
6. **truthfulness**: "How truthful was the AI?" (1-7 scale)

### **Accessing Survey Data**

**Method 1: Enhanced CSV Export (Recommended for Analysis)**
```bash
# Access via web interface (researcher mode - without p=true parameter)
# 1. Go to user study page
# 2. Scroll to "View Saved Data" section  
# 3. Choose "CSV (for analysis)"
# 4. Click "💾 Export Now"
# 5. Download CSV file

# CSV includes survey columns:
# survey_transparency, survey_warmth, survey_theory_of_mind, survey_adaptability, survey_expertise
# survey_goals, survey_satisfaction, survey_conflict_resolve, survey_believability, survey_transactivity, survey_truthfulness
# prolific_pid, prolific_study_id, prolific_session_id
```

**Method 2: Enhanced Database Script**
```bash
# Export all episodes with survey data
python scripts/enhanced_database_access.py --format csv --output survey_data.csv

# Filter by survey responses (requires JSON export for complex filtering)
python scripts/enhanced_database_access.py --format json --output survey_data.json
```

**Method 3: Python API**
```python
from ui.database_utils import get_user_study_episodes, parse_episode_reasoning

# Get all episodes with survey data
episodes = get_user_study_episodes()

# Extract survey responses
for episode in episodes:
    episode_data = parse_episode_reasoning(episode)
    survey_data = episode_data.get('survey_responses', {})
    prolific_data = episode_data.get('prolific_data', {})
    
    if survey_data:  # Only episodes with completed surveys
        print(f"Episode {episode.pk}:")
        print(f"  Manipulation Checks: transparency={survey_data.get('transparency')}, warmth={survey_data.get('warmth')}")
        print(f"  Outcomes: goals={survey_data.get('goals')}, satisfaction={survey_data.get('satisfaction')}")
        print(f"  Prolific ID: {prolific_data.get('PROLIFIC_PID', 'N/A')}")
```

**Method 4: JSON Export (Complete Data)**
```bash
# Access via web interface
# 1. Choose "JSON (complete data)"  
# 2. Survey data will be in: episodes[].study_data.survey_responses
# 3. Prolific data will be in: episodes[].study_data.prolific_data
```

### **Survey Data Analysis Tips**

**CSV Analysis (Excel/R/Python):**
```r
# R example
data <- read.csv("user_study_enhanced_YYYYMMDD_HHMMSS.csv")

# Analyze manipulation checks vs interventions
library(dplyr)
data %>% 
  group_by(transparency, warmth) %>%
  summarise(
    mean_transparency_check = mean(survey_transparency, na.rm=TRUE),
    mean_warmth_check = mean(survey_warmth, na.rm=TRUE),
    mean_satisfaction = mean(survey_satisfaction, na.rm=TRUE)
  )
```

**Python Analysis:**
```python
import pandas as pd

# Load data
df = pd.read_csv("user_study_enhanced_YYYYMMDD_HHMMSS.csv")

# Get episode-level data (remove duplicates from message-level format)
episodes_df = df.drop_duplicates(subset=['episode_id'])

# Analyze intervention effectiveness
intervention_analysis = episodes_df.groupby(['transparency', 'warmth']).agg({
    'survey_transparency': 'mean',
    'survey_warmth': 'mean', 
    'survey_goals': 'mean',
    'survey_satisfaction': 'mean'
}).round(2)

print(intervention_analysis)
```

### **Prolific Integration**
When participants come from Prolific, their IDs are automatically captured and stored:

```json
{
  "prolific_data": {
    "PROLIFIC_PID": "participant_unique_id",
    "STUDY_ID": "your_study_id",
    "SESSION_ID": "session_identifier"
  }
}
```

**Accessing Prolific Data:**
- Available in CSV export as: `prolific_pid`, `prolific_study_id`, `prolific_session_id`
- Enables linking Sotopia data with Prolific demographics and payment
- Shown to participants in completion message for verification

### **Intervention Dimensions**
The system now tracks five intervention dimensions:
1. **`transparency`** - High/Low AI thinking transparency
2. **`warmth`** - High/Low social warmth in responses  
3. **`expertise`** - High/Low domain expertise display
4. **`adaptability`** - High/Low adaptation to user preferences
5. **`theory_of_mind`** - High/Low understanding of user mental state

### **Backward Compatibility**
- Legacy episodes with old format are still accessible
- Database utilities automatically handle both formats
- Exports include data from both old and new formats

## 🔍 **Enhanced Querying Examples**

### **Basic Episode Retrieval**
```python
from ui.database_utils import get_user_study_episodes, get_intervention_statistics

# Get all user study episodes
episodes = get_user_study_episodes()

# Get statistics
stats = get_intervention_statistics(episodes)
print(f"Found {stats['total_episodes']} episodes")
print(f"Intervention distributions: {stats['intervention_distributions']}")
```

### **Advanced Filtering**
```python
# Filter by specific intervention combination
high_transparency_low_warmth = get_user_study_episodes(filter_by={
    'interventions': {
        'transparency': 'high',
        'warmth': 'low'
    }
})

# Filter by scenario and conversation length
hiring_long_conversations = get_user_study_episodes(filter_by={
    'scenario': 'hiring_scenario_competitive',
    'min_turns': 10,
    'max_turns': 25
})

# Filter by date range
recent_episodes = get_user_study_episodes(filter_by={
    'date_from': '2024-07-01',
    'date_to': '2024-07-31'
})
```

### **Quick Access Functions**
```python
from ui.database_utils import (
    get_episodes_by_intervention,
    get_episodes_by_scenario,
    get_episodes_by_agent,
    get_recent_episodes
)

# Get all high transparency episodes
high_transparency = get_episodes_by_intervention('transparency', 'high')

# Get all hiring scenario episodes  
hiring_episodes = get_episodes_by_scenario('hiring_scenario_competitive')

# Get episodes from last 7 days
recent = get_recent_episodes(days=7)
```

### **Analyze Conversations**
```python
for episode in user_studies:
    print(f"Episode {episode.pk}:")
    print(f"  Turns: {len(episode.messages)}")
    print(f"  Environment: {episode.environment}")
    
    # Show conversation
    for turn_idx, turn_messages in enumerate(episode.messages, 1):
        for speaker, action_type, content in turn_messages:
            print(f"  Turn {turn_idx} - {speaker}: {content}")
```

## 📈 **Data Analysis**

### **Export for Analysis**
The CSV export format is ready for analysis in:
- **Excel**: Open the CSV file directly
- **R**: `data <- read.csv("user_study_data.csv")`
- **Python/Pandas**: `df = pd.read_csv("user_study_data.csv")`
- **SPSS**: Import CSV with intervention columns

### **Enhanced CSV Export Columns**
The enhanced CSV export now includes comprehensive data:

**Study Metadata:**
- `episode_id`, `session_id`, `timestamp`, `tag`
- `environment`, `ai_agent`

**Intervention Dimensions:**
- `transparency`, `warmth`, `expertise`, `adaptability`, `theory_of_mind`

**AI Agent Attributes:**
- `agent_name`, `agent_occupation`, `agent_age`
- `decision_making_style`, `big_five`, `mbti`

**Conversation Metrics:**
- `total_turns`, `human_messages`, `ai_messages`, `avg_message_length`

**Survey Data (Post-Study):**
- `survey_transparency`, `survey_warmth`, `survey_theory_of_mind`, `survey_adaptability`, `survey_expertise`
- `survey_goals`, `survey_satisfaction`, `survey_conflict_resolve`, `survey_believability`, `survey_transactivity`, `survey_truthfulness`

**Prolific Integration:**
- `prolific_pid`, `prolific_study_id`, `prolific_session_id`

**Message-Level Data:**
- `turn_number`, `speaker`, `action_type`, `content`, `content_length`

**Analysis-Ready Format:**
- Each row represents one message
- Episode-level data repeated for each message (ideal for statistical analysis)
- Compatible with R, Python pandas, SPSS, Excel

## ❗ **Troubleshooting**

### **"Connection refused" Error**
```bash
# Check if Redis is running
sudo systemctl status redis-server

# Start Redis if not running
sudo systemctl start redis-server

# Or use Docker
docker run -d -p 6379:6379 redis:latest
```

### **"No episodes found" Message**
- Make sure user study conversations have been saved through the Streamlit interface
- Check if you're connected to the correct Redis database
- Verify `REDIS_OM_URL` environment variable

### **Permission Errors**
```bash
# Make scripts executable
chmod +x scripts/browse_database.py
chmod +x scripts/access_user_study_data.py
```

## 🔐 **Security Notes**

- Redis runs without authentication by default (localhost only)
- For production, enable Redis authentication
- Backup your Redis data regularly: `redis-cli BGSAVE`
- Consider using Redis persistence: `appendonly yes` in redis.conf

## 📝 **Data Backup**

### **Export All Data**
```bash
# Export all data to JSON
python scripts/access_user_study_data.py --all --format json --output backup.json

# Redis data dump
redis-cli BGSAVE
```

### **Regular Backups**
Set up a cron job to automatically backup user study data:
```bash
# Add to crontab: backup daily at 2 AM
0 2 * * * cd /usr2/mingqia2/sotopia && python scripts/access_user_study_data.py --format json --output /backup/user_study_$(date +\%Y\%m\%d).json
```


Quick reference for future use:
  docker run -d -p 6380:6379 --name sotopia-redis-json
  redis/redis-stack-server:latest
  export REDIS_OM_URL='redis://localhost:6380'
  cd /usr2/mingqia2/sotopia
  source .venv/bin/activate
  streamlit run ui/app.py