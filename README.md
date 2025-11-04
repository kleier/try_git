# Big Red Barn Properties - CRM Integration Suite

A comprehensive Python toolkit for real estate CRM data integration, analytics, and AI-powered coaching for ISAs (Inside Sales Agents).

## Tools Included

### 1. FollowUpBoss Conversation Summarizer (`main.py`)
Fetches, aggregates, and analyzes all conversations from your FollowUpBoss account with AI-powered insights.

### 2. **Mojo Dialer Sync Tool (`mojo_sync.py`)** - NEW!
Complete Mojo Dialer integration: extract data, store in SQLite, generate analytics, and sync to Follow Up Boss.

## Features

### FollowUpBoss Tool
- Fetches all data from FollowUpBoss API:
  - People (contacts/leads)
  - Events (activities, interactions)
  - Text messages
- Aggregates conversations by person
- Calculates engagement metrics
- Generates AI-powered insights using Claude
- Provides both individual conversation summaries and overall business insights
- Exports data in JSON and human-readable formats

### Mojo Dialer Tool (NEW!)
- **Data Extraction**: Import contacts and call logs from Mojo CSV exports
- **SQLite Database**: Centralized storage with complete schema for contacts, calls, and recordings
- **Analytics & Reports**:
  - Agent performance metrics (contact rate, avg duration, call results)
  - Coaching opportunities (sentiment analysis, talk/listen ratio)
  - CSV exports for external analysis
  - AI-ready structure for call transcripts and coaching feedback
- **Follow Up Boss Sync**:
  - Auto-sync Mojo contacts to FUB as new leads
  - Sync call logs as activity history
  - Prevents duplicates with intelligent matching
- **Future-Ready**: Schema supports call transcripts, sentiment analysis, and AI coaching notes

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

# Optional (for Motion integration)
MOTION_WEBHOOK_URL=your_motion_webhook_url_here

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

### Motion Webhook (Optional)

Automatically send your FollowUpBoss summary to Motion as a task:

1. Go to [Motion](https://app.usemotion.com/)
2. Set up a webhook integration (or use Zapier/Make.com to create a webhook that creates Motion tasks)
3. Copy your webhook URL
4. Add it to your `.env` file as `MOTION_WEBHOOK_URL`

**What gets sent to Motion:**
- Total people and interactions
- Event type breakdown
- Top 10 most engaged contacts
- All data is formatted as JSON (see `WEBHOOK_PAYLOAD_SPEC.md` for details)

If you don't provide a webhook URL, the tool will still work and save all data locally.

## Usage

### FollowUpBoss Tool

Run the main script:

```bash
python main.py
```

This will:
1. Fetch all conversations from FollowUpBoss
2. Aggregate data by person
3. Generate summary statistics
4. Send data to Motion webhook (if configured)
5. Create AI-powered insights (if Anthropic API key provided)
6. Save all outputs to the `output/` directory

### Mojo Dialer Tool

**Quick Start:**

```bash
# 1. Export data from Mojo Dialer (CSV format)
# 2. Import to local database
python mojo_sync.py --import-contacts mojo_contacts.csv
python mojo_sync.py --import-calls mojo_calls.csv

# 3. Generate analytics reports
python mojo_sync.py --export-analytics

# 4. Sync to Follow Up Boss
python mojo_sync.py --sync-fub --dry-run  # Preview first
python mojo_sync.py --sync-fub             # Actually sync

# 5. View statistics
python mojo_sync.py --stats
```

**Complete Workflow:**
```bash
python mojo_sync.py \
  --import-contacts contacts.csv \
  --import-calls calls.csv \
  --export-analytics \
  --sync-fub
```

**📖 For detailed documentation, see [MOJO_SYNC_GUIDE.md](MOJO_SYNC_GUIDE.md)**

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

### FollowUpBoss Tool

- **fub_client.py** - FollowUpBoss API client with authentication and pagination
- **data_aggregator.py** - Aggregates conversations and calculates metrics
- **summarizer.py** - AI-powered summarization using Claude
- **motion_webhook.py** - Motion integration for task creation
- **main.py** - Main orchestration script

### Mojo Dialer Tool

- **mojo_database.py** - SQLite database manager with full schema
- **mojo_extractor.py** - CSV parser and data normalizer (future: API client)
- **mojo_analytics.py** - Analytics engine and CSV exports
- **mojo_fub_sync.py** - Follow Up Boss sync integration
- **mojo_sync.py** - Main CLI tool
- **MOJO_SYNC_GUIDE.md** - Complete documentation and usage guide

### Database Schema

The SQLite database (`mojo_data.db`) includes:
- **contacts** - All Mojo leads with FUB sync tracking
- **call_logs** - Complete call history
- **call_recordings** - Recording metadata, transcripts, AI analysis
- **analytics_summary** - Pre-computed metrics
- **import_history** - Audit trail for all imports

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
