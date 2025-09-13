# Lattice - Complete Flow Documentation



## Overview
Lattice is an intelligent automation system that transforms Slack bug reports into fully implemented code fixes with Jira tickets and GitHub pull requests, using sophisticated LLM routing for cost-effective and high-quality results.

## Architecture Flow

```
Slack Thread → MCP Server → Deimos Router → Jira + GitHub
     ↓             ↓              ↓              ↓
  /ticket    analyze_request  Optimal LLM   Automated Fix
```

## Detailed Flow

### Phase 1: Slack Ingestion
...

### Phase 2: Analysis with Deimos Router
**Tool**: `analyze_request.py`

1. **Input Processing**:
   ```python
   {
     "slack_context": {
       "conversation": "full text",
       "thread_messages": [...],
       "channel_id": "C123",
       "user_id": "U456",
       "attachments": [...]
     },
     "parsed_info": {
       "initial_summary": "...",
       "detected_keywords": [...],
       "error_messages": [...]
     }
   }
   ```

2. **Complexity Analysis**:
   - Detects programming languages
   - Identifies code patterns
   - Calculates complexity score
   - Estimates effort (S/M/L/XL)

3. **Deimos Router Decision**:
   - **Task Type Detection**:
     - `debugging` → Complex debugging models
     - `coding` → Code generation specialists
     - `architecture` → System design models
     - `simple_query` → Cost-effective models
   
   - **Model Selection Matrix**:
     ```
     Critical + Complex → Claude 3.5 Sonnet / GPT-4o
     Medium Complexity → Claude 3 Haiku / Gemini Flash
     Simple Tasks → Mistral Tiny / Llama 3.1
     ```

4. **Output**: Formatted Jira ticket content with metadata

### Phase 3: Jira Issue Creation
**Tool**: `jira_create_issue.py`

1. **Rich Content Generation**:
   - Creates ADF (Atlassian Document Format) description
   - Includes acceptance criteria
   - Adds technical details
   - Shows routing metadata (model used, cost)

2. **Issue Fields**:
   - Title, Priority, Issue Type
   - Labels and Components
   - Estimated Effort
   - Confidence Score

3. **Output**: Jira issue key and URL

### Phase 4: Fix Planning
**Tool**: `plan_fix.py`

1. **Repository Indexing**:
   - Uses `RepoIndexer` service
   - Vector search for relevant files
   - Pattern detection in codebase

2. **Deimos Router for Fix Generation**:
   - Complexity assessment:
     - Simple (≤3 score) → Basic models
     - Moderate (4-6) → Balanced models
     - Complex (>6) → Premium models
   
   - Creates comprehensive fix plan:
     ```json
     {
       "summary": "Fix approach",
       "root_cause": "Identified cause",
       "changes": [
         {
           "file_path": "src/file.js",
           "change_type": "modify",
           "old_content": "...",
           "new_content": "...",
           "description": "What changed"
         }
       ],
       "test_plan": ["Test steps"],
       "risks": ["Potential issues"]
     }
     ```

### Phase 5: GitHub PR Creation
**Tool**: `github_branch_and_pr.py`

1. **Branch Creation**:
   - Format: `auto/{jira-key}-{timestamp}`
   - Based on main/master branch

2. **Code Changes Application**:
   - Creates/modifies/deletes files per fix plan
   - Each change gets individual commit

3. **Pull Request**:
   - Title: `[JIRA-123] Fix summary`
   - Rich description with:
     - Jira link
     - Root cause analysis
     - Changes made
     - Test plan
     - Risk assessment

### Phase 6: Notification
Returns to Slack with:
- ✅ Jira ticket link
- 🔧 GitHub PR link
- 📊 Confidence score
- 💰 Total cost estimate

## Deimos Router Intelligence

### Multi-Layer Routing Rules

1. **Code Detection Layer**:
   ```python
   if code_detected:
     if language == "python":
       → Claude 3.5 Sonnet  # Best Python support
     elif language == "javascript":
       → GPT-4o            # Strong JS/TS support
     elif language == "rust":
       → Claude 3.5 Sonnet  # Systems programming
   ```

2. **Cost Priority Layer**:
   ```python
   if severity == CRITICAL:
     → "high_quality"  # Use best models
   elif severity == LOW and effort == "S":
     → "low_cost"      # Use cheapest models
   else:
     → "balanced"      # Optimize cost/quality
   ```

3. **Task-Based Layer**:
   ```python
   task_routing = {
     'debugging': 'openai/gpt-4o',
     'architecture': 'anthropic/claude-3-opus',
     'summarization': 'anthropic/claude-3-haiku',
     'classification': 'google/gemini-1.5-flash',
     'simple_query': 'mistral/mistral-tiny'
   }
   ```

4. **Complexity Fallback**:
   - <300 chars → Mistral Tiny ($0.00025/1K)
   - 300-1500 chars → Claude Haiku ($0.00025/1K)
   - >1500 chars → Claude 3.5 Sonnet ($0.003/1K)

## Cost Optimization

### Model Pricing Tiers
- **Ultra Low**: $0.00015-0.00025/1K tokens (Llama, Mistral Tiny)
- **Low**: $0.00025-0.00125/1K tokens (Haiku, Gemini Flash)
- **Medium**: $0.003-0.015/1K tokens (Claude Sonnet, GPT-4)
- **High**: $0.015-0.06/1K tokens (O1 models, Claude Opus)

### Typical Cost per Ticket
- Simple bug fix: ~$0.05
- Medium complexity: ~$0.25
- Complex analysis: ~$1.00

## Benefits

1. **70-90% Cost Reduction**: Smart routing vs always using GPT-4
2. **Quality Preservation**: Premium models for critical tasks
3. **Speed**: Parallel processing where possible
4. **Transparency**: Every routing decision logged
5. **Flexibility**: Easy to add new models/providers

## Configuration

### Environment Variables
```bash
# Deimos Router
DEIMOS_API_URL=https://api.deimos.com
DEIMOS_API_KEY=your-key

# Jira
JIRA_URL=https://company.atlassian.net
JIRA_USERNAME=email@company.com
JIRA_API_TOKEN=token
JIRA_PROJECT_KEY=PROJ

# GitHub
GITHUB_TOKEN=ghp_token
GITHUB_REPO=owner/repo

# Slack
SLACK_BOT_TOKEN=xoxb-token
SLACK_APP_TOKEN=xapp-token
```

### Adding New Models
Simply update the routing rules in `deimos_route.py`:
```python
task_rule = TaskRule(
    name="task-router",
    rules={
        'new_task': 'provider/new-model',
        # ...
    }
)
```

## Example Flow

1. **Slack**: "Getting null cartId error in checkout"
2. **Analysis**: Detects JavaScript, error pattern, checkout component
3. **Deimos Routes**: 
   - Analysis → GPT-4o (debugging task)
   - Fix Generation → Claude 3.5 Sonnet (code task)
4. **Jira**: Creates BUG-456 with full details
5. **Fix**: Adds null check in cart.js
6. **GitHub**: PR #789 with fix
7. **Slack**: "✅ Fixed in PR #789, Jira BUG-456"

## Future Enhancements

1. **Learning System**: Track which models perform best for specific error types
2. **Auto-Merge**: Merge PRs after CI passes
3. **Test Generation**: Automatically create unit tests
4. **Multi-Repo**: Support fixes across multiple repositories
5. **Custom Models**: Fine-tuned models for company-specific code patterns
