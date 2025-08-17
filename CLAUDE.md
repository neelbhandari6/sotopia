URL Parameters for User Study Page# Sotopia Codebase Structure Summary

## Project Overview
**Sotopia** is an open-ended social learning environment for evaluating and facilitating social intelligence in language agents. It's a Python-based platform that enables multi-agent interactions and social simulations.

## Core Architecture

### Main Package Structure (`sotopia/`)
- **`agents/`** - Agent implementations and base classes
  - `base_agent.py` - Generic agent interface with goal setting
  - `llm_agent.py` - LLM-powered agents
  - `redis_agent.py` - Redis-backed agents for persistence
  - `generate_agent_background.py` - Agent profile generation

- **`envs/`** - Environment management and evaluation
  - `evaluators.py` - Rule-based and LLM-based evaluation systems
  - `parallel.py` - Multi-agent parallel environment handling

- **`database/`** - Data persistence and storage
  - `logs.py` - Episode logging and storage models
  - `persistent_profile.py` - Agent profile management
  - `evaluation_dimensions.py` - Evaluation metrics definitions
  - `serialization.py` - Data serialization utilities

- **`messages/`** - Communication system
  - `message_classes.py` - Message type definitions
  - `messenger.py` - Message routing and handling

- **`samplers/`** - Task and scenario sampling
  - `uniform_sampler.py` - Random sampling strategies
  - `constraint_based_sampler.py` - Rule-based sampling

- **`generation_utils/`** - LLM generation utilities
  - `generate.py` - Text generation interfaces
  - `output_parsers.py` - Response parsing logic

- **`renderers/`** - Output formatting
  - `xml_renderer.py` - XML-based rendering

### Key Server Components
- **`server.py`** - Main simulation server with async support
- **`api/fastapi_server.py`** - REST API server for external integrations

### Configuration & CLI
- **`cli/`** - Command-line interface
  - `app.py` - Main CLI application
  - `benchmark/` - Benchmarking tools
  - `install/` - Setup and installation utilities

- **`sotopia_conf/`** - Configuration management using Gin

### User Interfaces
- **`ui/`** - Streamlit-based web interface
  - `app.py` - Main UI application
  - `pages/` - Individual UI pages for data management
  - `database_utils.py` - UI database integration

- **`sotopia-chat/`** - Chat interface implementation
  - `fastapi_server.py` - Chat API server

### Documentation & Examples
- **`docs/`** - Next.js documentation site with API references
- **`examples/`** - Usage examples and demos
  - `minimalist_demo.py` - Simple getting started example
  - `experimental/` - Advanced use cases

### Testing & Development
- **`tests/`** - Comprehensive test suite
- **`notebooks/`** - Jupyter notebooks for analysis and tutorials
- **`scripts/`** - Utility scripts for database management

## Key Technologies
- **Backend**: Python with async/await, FastAPI, Redis
- **Database**: Redis with redis-om for object mapping
- **LLM Integration**: OpenAI API, LiteLLM for multi-provider support
- **UI**: Streamlit for web interface, Next.js for documentation
- **Configuration**: Gin-config for dependency injection
- **Build**: UV for package management, PyProject.toml

## Core Functionality
1. **Multi-agent social simulations** with configurable scenarios
2. **LLM-powered agents** with persistent profiles and goals
3. **Evaluation systems** for measuring social intelligence
4. **Real-time chat interfaces** for human-AI interaction
5. **Comprehensive data logging** and analysis tools
6. **Extensible sampling** strategies for generating diverse scenarios

## Architecture Flow
1. **Samplers** generate scenarios and agent combinations
2. **Agents** interact within **Environments** using **Messages**
3. **Evaluators** assess interactions and provide feedback
4. **Database** persists all interaction logs and agent profiles
5. **Renderers** format outputs for different consumption methods
6. **Server** orchestrates the entire simulation pipeline

## Development Commands
- `uv sync --all-extras` - Install dependencies
- `uv run sotopia install` - Setup environment and data
- `python examples/minimalist_demo.py` - Run basic simulation
- `pytest tests/` - Run test suite

## User Study URL Parameters Guide

The user study interface (`/user_study`) supports comprehensive URL parameter configuration for research experiments.

### 🎛️ **5 Intervention Dimensions**
Control AI agent behavior through these intervention parameters:

| Parameter | Short Form | Values | Default | Description |
|-----------|------------|--------|---------|-------------|
| `transparency` | `t` | `high` / `low` | `high` | Shows/hides AI thinking process (`<THINK>` tags) |
| `warmth` | `w` | `high` / `low` | `high` | Controls AI warmth and friendliness |
| `expertise` | `e` | `high` / `low` | `high` | Controls AI expertise level |
| `adaptability` | `a` | `high` / `low` | `high` | Controls AI adaptability |
| `theory_of_mind` | `tom` | `high` / `low` | `high` | Controls AI theory of mind capabilities |

### 🎬 **Scenario Selection**

| Parameter | Short Form | Available Values | Description |
|-----------|------------|------------------|-------------|
| `scenario` | `s` | See scenarios below | Selects conversation scenario |

**Available Scenarios:**
- `hiring_competitive` - Job salary/start date negotiation (competitive)
- `hiring_cooperative` - Job salary/start date negotiation (cooperative)
- `travel_restrictions` - Travel restrictions inquiry at airport
- `laptop_shopping` - Laptop purchase assistance
- `business_collab` - Business collaboration discussion

### 👥 **Interface Control**

| Parameter | Short Form | Values | Default | Description |
|-----------|------------|--------|---------|-------------|
| `participant` | `p` | `true` / `false` | `false` | Hides debug tools when `true` (participant mode) |

### 📝 **Example URLs**

**Full Parameter Names:**
```
/user_study?transparency=high&warmth=low&expertise=high&adaptability=high&theory_of_mind=low&scenario=hiring_competitive&participant=true
```

**Short Form (Recommended):**
```
/user_study?t=high&w=low&e=high&a=high&tom=low&s=laptop_shopping&p=true
```

**Minimal URL (All Defaults):**
```
/user_study?s=travel_restrictions&p=true
```

### 🔬 **Research Configuration**

**Control Condition (All High):**
```
/user_study?t=high&w=high&e=high&a=high&tom=high&s=hiring_competitive&p=true
```

**Low Transparency Test:**
```
/user_study?t=low&w=high&e=high&a=high&tom=high&s=hiring_competitive&p=true
```

**Mixed Intervention:**
```
/user_study?t=high&w=low&e=high&a=low&tom=high&s=business_collab&p=true
```

### 🤖 **Agent Selection**
- **Automatic**: Agents are automatically selected based on intervention dimensions
- **Profile Matching**: System finds agents whose `personality_and_values` match the specified intervention pattern
- **Fallback**: If no exact match found, defaults to first available agent

### 💾 **Data Storage**
- All conversations automatically saved to Redis database
- Episode logs include full intervention configuration
- Enhanced metadata includes agent attributes and conversation statistics
- Export options available for researchers (CSV/JSON)
