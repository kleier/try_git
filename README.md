# FollowUpBoss Conversation Summarizer

A Python tool to fetch, aggregate, and analyze all conversations and interactions from your FollowUpBoss account. Uses AI to generate actionable business insights and conversation summaries.

## Features

- Fetches all data from FollowUpBoss API:
  - People (contacts/leads)
  - Events (activities, interactions)
  - Text messages
- Aggregates conversations by person
- Calculates engagement metrics
- Generates AI-powered insights using Claude
- Provides both individual conversation summaries and overall business insights
- Exports data in JSON and human-readable formats

## Prerequisites

- Python 3.8 or higher
- FollowUpBoss account with API access
- Anthropic API key (optional, for AI summaries)

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd try_git
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
```

4. Edit `.env` and add your API keys:
```bash
# Required
FOLLOWUPBOSS_API_KEY=your_api_key_here

# Optional (for AI summaries)
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional limits (for testing)
MAX_PEOPLE=100
MAX_EVENTS=500
MAX_TEXT_MESSAGES=500
```

## Getting Your API Keys

### FollowUpBoss API Key

1. Log in to your FollowUpBoss account
2. Go to **Admin → API**
3. Copy your API key

**Note:** The API key has the same access level as your user:
- Agent API keys: Access only to assigned people
- Broker API keys: Access to all people in the account

For more information, see the [FollowUpBoss API Documentation](https://docs.followupboss.com/reference/authentication)

### Anthropic API Key (Optional)

1. Sign up at [Anthropic Console](https://console.anthropic.com/)
2. Go to API Keys section
3. Create a new API key

If you don't provide an Anthropic API key, the tool will still fetch and aggregate data, but will skip the AI-powered summarization.

## Usage

### Basic Usage

Run the main script:

```bash
python main.py
```

This will:
1. Fetch all conversations from FollowUpBoss
2. Aggregate data by person
3. Generate summary statistics
4. Create AI-powered insights (if API key provided)
5. Save all outputs to the `output/` directory

### Output Files

The tool generates several files in the `output/` directory:

- **summary_stats_[timestamp].json** - Overall statistics about your conversations
- **aggregated_data_[timestamp].json** - Complete data aggregated by person
- **business_insights_[timestamp].txt** - AI-generated business insights and recommendations
- **individual_summaries_[timestamp].json** - AI summaries for each conversation
- **individual_summaries_[timestamp].txt** - Human-readable version of conversation summaries

### Example Output

**Summary Statistics:**
```
Total People: 150
People with Interactions: 89
Total Events: 450
Total Text Messages: 230
Total Interactions: 680

Event Type Breakdown:
  Email: 180
  Website Visit: 150
  Phone Call: 70
  Property View: 50
```

**Top Engaged People:**
```
1. John Doe (john@example.com)
   Interactions: 45
   Last Activity: 2025-10-20T15:30:00Z
```

**Business Insights (AI-generated):**
The AI will provide insights on:
- Overall business health
- Customer engagement patterns
- Key opportunities
- Operational recommendations
- Growth strategies

## Configuration Options

You can adjust limits in the `.env` file:

```bash
# Limit number of records fetched (useful for testing or rate limit management)
MAX_PEOPLE=100          # Maximum people to fetch
MAX_EVENTS=500          # Maximum events to fetch
MAX_TEXT_MESSAGES=500   # Maximum text messages to fetch
```

Remove or increase these limits to fetch all available data.

## Architecture

The project is organized into several modules:

- **fub_client.py** - FollowUpBoss API client with authentication and pagination
- **data_aggregator.py** - Aggregates conversations and calculates metrics
- **summarizer.py** - AI-powered summarization using Claude
- **main.py** - Main orchestration script

## API Rate Limits

The tool includes automatic retry logic with exponential backoff for:
- Network failures
- Rate limit errors (respects `Retry-After` headers)
- Temporary API issues

## Troubleshooting

### "FOLLOWUPBOSS_API_KEY not found"
Make sure you've created a `.env` file with your API key. Don't modify `.env.example` directly.

### API Authentication Errors
- Verify your API key is correct
- Check that your user has the necessary permissions
- Ensure you're using the key from Admin → API screen

### Rate Limiting
If you hit rate limits:
- The tool will automatically wait and retry
- Consider reducing `MAX_PEOPLE`, `MAX_EVENTS`, and `MAX_TEXT_MESSAGES`
- Run during off-peak hours

### Missing Data
Some data may not be accessible via the API:
- Certain text message data is only visible in the FollowUpBoss UI
- Some event types may be restricted based on your account level

## API Documentation

For more information about the FollowUpBoss API:
- [Getting Started](https://docs.followupboss.com/reference/getting-started)
- [Authentication](https://docs.followupboss.com/reference/authentication)
- [API Reference](https://docs.followupboss.com/reference)

## License

MIT License

## Support

For issues related to:
- **FollowUpBoss API:** Contact api@followupboss.com
- **This tool:** Open an issue in this repository
- **Anthropic API:** Visit https://support.anthropic.com

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
