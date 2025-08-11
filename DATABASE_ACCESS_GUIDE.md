# 🗄️ Database Access Guide

This guide explains how to access the Redis database containing user study conversation data.

## 📍 **Database Location**

The user study data is saved to a **Redis database** using the same system as agent-agent simulations.

### **Database URL**
- **Default**: `redis://localhost:6379`
- **Environment Variable**: `REDIS_OM_URL`
- **Current Setting**: Check with `echo $REDIS_OM_URL`

## 🚀 **Quick Access Methods**

### **1. Using the Browser Script** (Recommended)
```bash
cd /usr2/mingqia2/sotopia
python scripts/browse_database.py
```

**Features:**
- Interactive menu-driven interface
- Browse all episodes or filter user studies
- View detailed conversation data
- Check database connection status

### **2. Using the Export Script**
```bash
cd /usr2/mingqia2/sotopia

# View summary
python scripts/access_user_study_data.py

# Export to CSV
python scripts/access_user_study_data.py --format csv --output user_study_data.csv

# Export to JSON
python scripts/access_user_study_data.py --format json --output user_study_data.json

# Export all episodes (not just user studies)
python scripts/access_user_study_data.py --all --format csv
```

### **3. Direct Python Access**
```python
from sotopia.database import EpisodeLog

# Get all user study episodes
episodes = EpisodeLog.find().all()
user_studies = [ep for ep in episodes if ep.tag and 'user_study' in ep.tag]

# View a specific episode
episode = EpisodeLog.get('episode_id_here')
print(episode.messages)  # Conversation data
print(episode.reasoning)  # Intervention settings
```

## 🔧 **Setting Up Redis Access**

### **Option 1: Local Redis Server**
```bash
# Install Redis (Ubuntu/Debian)
sudo apt update
sudo apt install redis-server

# Start Redis
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Set environment variable
export REDIS_OM_URL='redis://localhost:6379'
```

### **Option 2: Docker Redis**
```bash
# Run Redis in Docker
docker run -d -p 6379:6379 --name sotopia-redis redis:latest

# Set environment variable
export REDIS_OM_URL='redis://localhost:6379'
```

### **Option 3: Remote Redis**
If using a remote Redis server:
```bash
export REDIS_OM_URL='redis://your-redis-host:6379'
# or with authentication:
export REDIS_OM_URL='redis://:password@your-redis-host:6379'
```

## 📊 **Data Structure**

### **User Study Episodes**
Each user study conversation is saved as an `EpisodeLog` with:

```json
{
  "pk": "episode_id",
  "environment": "scenario_name",
  "agents": ["ai_agent_name", "human_participant"],
  "tag": "user_study_20240730_143502",
  "models": ["intervention_high", "human"],
  "messages": [
    [["Human", "speak", "Hello, how are you?"]],
    [["AI_Agent", "speak", "I'm doing well, thank you!"]]
  ],
  "reasoning": "User study with interventions: {\"transparency\": \"high\", \"warmth\": \"low\", ...}",
  "rewards": [0.0, 0.0]
}
```

### **Key Fields**
- **`messages`**: Turn-by-turn conversation data
- **`reasoning`**: Contains intervention settings as JSON
- **`tag`**: Identifies user study episodes (contains "user_study")
- **`agents`**: AI agent + "human_participant"
- **`models`**: Intervention type + "human"

## 🔍 **Querying Data**

### **Find User Study Episodes**
```python
from sotopia.database import EpisodeLog

# All user studies
user_studies = [
    ep for ep in EpisodeLog.find().all() 
    if ep.tag and 'user_study' in ep.tag
]

# By date (if tag contains timestamp)
import datetime
today = datetime.date.today().strftime('%Y%m%d')
today_studies = [
    ep for ep in user_studies 
    if today in ep.tag
]
```

### **Extract Intervention Data**
```python
import json

for episode in user_studies:
    if 'interventions:' in episode.reasoning:
        interventions_json = episode.reasoning.split('interventions: ')[1]
        interventions = json.loads(interventions_json)
        print(f"Episode {episode.pk}: {interventions}")
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

### **CSV Columns**
- `session_id`: Unique identifier
- `scenario`, `ai_agent`: Study configuration
- `transparency`, `warmth`, `expertise`, `adaptability`, `theory_of_mind`: Intervention levels
- `turn_number`, `speaker`, `action_type`, `content`: Conversation data

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