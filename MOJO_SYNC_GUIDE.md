# Mojo Dialer Sync Tool - Complete Guide

## Overview

This tool extracts data from **Mojo Dialer**, stores it in a local **SQLite database**, generates **analytics reports and CSVs**, and syncs key contact and call data to **Follow Up Boss (FUB)**.

### Business Goals
- **AI Coaching Pipeline**: Extract call data, transcripts, and recordings for AI-driven coaching feedback
- **Performance Analytics**: Track ISA metrics (contact rate, sentiment, talk/listen ratio)
- **CRM Integration**: Ensure Mojo conversations are reflected in Follow Up Boss
- **Trend Analysis**: Identify patterns in lead behavior and agent performance

### Key Features
- ✅ Import contacts and call logs from Mojo CSV exports
- ✅ Store data in structured SQLite database
- ✅ Export analytics to CSV for external analysis
- ✅ Sync contacts and calls to Follow Up Boss
- ✅ Generate AI coaching reports
- ✅ Track performance metrics by agent
- ✅ Future-ready for Mojo API integration

---

## Architecture

```
┌─────────────────┐
│  Mojo Dialer    │
│  CSV Exports    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────────┐
│ mojo_extractor  │─────▶│  SQLite Database │
│   (CSV Parser)  │      │  (mojo_data.db)  │
└─────────────────┘      └────────┬─────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼             ▼
         ┌──────────────┐  ┌────────────┐  ┌─────────────┐
         │ mojo_analytics│  │ mojo_fub   │  │  CSV/JSON   │
         │   (Reports)   │  │   (Sync)   │  │   Exports   │
         └──────────────┘  └──────┬──────┘  └─────────────┘
                                  │
                                  ▼
                         ┌────────────────┐
                         │ Follow Up Boss │
                         │   (CRM Sync)   │
                         └────────────────┘
```

---

## Quick Start

### 1. Installation

```bash
# Clone repository
cd try_git

# Install dependencies (already done if you have the main FUB tool)
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env and add your FOLLOWUPBOSS_API_KEY
```

### 2. Export Data from Mojo Dialer

Since Mojo doesn't have public API documentation, we use CSV exports:

**Export Contacts:**
1. Log into Mojo Dialer
2. Go to **Data → Export**
3. Select fields: First Name, Last Name, Email, Phone, Address, City, State, ZIP, Status, Lead Source, List Name, Tags, Created Date, Last Contact Date
4. Export to CSV (max 100k records at a time)
5. Save as `mojo_contacts.csv`

**Export Call Logs:**
1. Go to **Reports → Call Logs**
2. Select date range (e.g., last 30-90 days)
3. Include fields: Call ID, Contact ID, Phone, Date, Duration, Result, Type, Agent, Notes, Recording URL
4. Export to CSV
5. Save as `mojo_calls.csv`

### 3. Import Data

```bash
# Import contacts
python mojo_sync.py --import-contacts mojo_contacts.csv

# Import call logs
python mojo_sync.py --import-calls mojo_calls.csv

# Check what was imported
python mojo_sync.py --stats
```

### 4. Sync to Follow Up Boss

```bash
# Dry run first (see what would be synced)
python mojo_sync.py --sync-fub --dry-run

# Actually sync contacts and calls
python mojo_sync.py --sync-fub

# Or sync contacts only
python mojo_sync.py --sync-fub --contacts-only

# Or sync calls only (for contacts already in FUB)
python mojo_sync.py --sync-fub --calls-only
```

### 5. Generate Analytics

```bash
# Generate all analytics reports
python mojo_sync.py --export-analytics

# Reports will be in: output/analytics/
```

---

## Database Schema

### Core Tables

#### `contacts`
Stores all Mojo contacts with FUB sync tracking:
- Contact details (name, email, phone, address)
- Status, lead source, list assignment
- Tags and custom fields (JSON)
- FUB sync status and person ID

#### `call_logs`
Stores all call history:
- Call metadata (date, duration, result, type)
- Agent name
- Recording URL
- Notes and disposition
- FUB sync status

#### `call_recordings`
Stores recording analysis (future use):
- Transcript
- Sentiment analysis
- Intent classification
- Talk/listen ratio
- AI coaching notes

#### `analytics_summary`
Pre-computed daily metrics by agent

#### `import_history`
Tracks all import operations

---

## Analytics & Reports

### Available Analytics

**1. Contact Export**
```bash
python mojo_sync.py --export-analytics
```
Generates: `contacts_YYYYMMDD_HHMMSS.csv`

**2. Call Logs Export**
Generates: `call_logs_YYYYMMDD_HHMMSS.csv`
- Includes contact information
- Last 90 days by default

**3. Agent Performance Metrics**
Generates: `agent_metrics_YYYYMMDD_HHMMSS.json`
- Total calls per agent
- Contact rate %
- Average call duration
- Call results breakdown
- Sentiment analysis (if available)

**4. Coaching Opportunities**
Generates: `coaching_opportunities_YYYYMMDD_HHMMSS.csv`
- Calls with negative sentiment
- High talk/listen ratios (agent talking too much)
- Short duration contacts
- AI coaching recommendations

**5. Text Coaching Report**
Generates: `coaching_report_YYYYMMDD_HHMMSS.txt`
- Human-readable ISA coaching summary
- Performance overview
- Specific improvement opportunities

### Example Analytics Query

You can also query the SQLite database directly:

```bash
sqlite3 mojo_data.db
```

```sql
-- Agent performance last 30 days
SELECT
    agent_name,
    COUNT(*) as total_calls,
    SUM(CASE WHEN call_result = 'Contact' THEN 1 ELSE 0 END) as contacts,
    ROUND(AVG(call_duration), 1) as avg_duration,
    ROUND(SUM(CASE WHEN call_result = 'Contact' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as contact_rate
FROM call_logs
WHERE call_date >= date('now', '-30 days')
GROUP BY agent_name;

-- Top contacted leads
SELECT
    c.full_name,
    c.email,
    c.phone,
    c.list_name,
    COUNT(cl.id) as call_count,
    MAX(cl.call_date) as last_call
FROM contacts c
JOIN call_logs cl ON c.id = cl.contact_id
GROUP BY c.id
ORDER BY call_count DESC
LIMIT 20;
```

---

## Follow Up Boss Integration

### What Gets Synced

**Contacts:**
- Creates new person in FUB using `/events` endpoint
- Includes: Name, email, phone, address
- Source: "Mojo Dialer"
- Custom fields: Mojo Status, Lead Source, List Name, Tags
- Stores Mojo Contact ID for reference
- Triggers FUB action plans (for new leads)

**Call Logs:**
- Creates call event for existing FUB contacts
- Includes: Date, duration, result, agent, notes
- Links to recording URL (if available)
- Does NOT create duplicate contacts

### Sync Process

1. **Contacts First**: Sync all Mojo contacts to FUB
2. **Track IDs**: Database stores FUB person ID for each contact
3. **Calls Second**: Sync call logs only for contacts already in FUB
4. **No Duplicates**: Uses email/phone matching in FUB

### Rate Limiting

The sync tool includes:
- Exponential backoff on errors
- Respects `Retry-After` headers
- 0.5s delay between requests
- 2s pause after every 50 records
- Automatic retry on network failures

---

## AI Coaching Pipeline

### Current Capabilities

The system stores and tracks:
- Call recordings URLs
- Call duration and results
- Agent performance metrics
- Contact rates and patterns

### Future AI Integration

The schema is ready for:

**1. Transcript Analysis**
- Store transcripts in `call_recordings.transcript`
- Source: Outdoo, AWS Transcribe, or manual

**2. Sentiment Analysis**
- Score: -1.0 (negative) to +1.0 (positive)
- Label: Positive, Neutral, Negative
- Store in `call_recordings.sentiment_score/label`

**3. Intent Classification**
- Categories: Buyer, Seller, Just Looking, Not Interested
- Store in `call_recordings.intent_classification`

**4. Talk/Listen Ratio**
- Calculate agent talk time vs. client talk time
- Target: 1:2 ratio (agent should listen more)
- Store in `call_recordings.talk_listen_ratio`

**5. AI Coaching Notes**
- Generate feedback using Claude/GPT
- Store in `call_recordings.ai_coaching_notes`

### Example AI Integration (Future)

```python
from anthropic import Anthropic

# After adding transcripts to the database
db = MojoDatabase()
analytics = MojoAnalytics(db)

# Get unanalyzed recordings
recordings = analytics.export_recordings_for_analysis('recordings.csv', only_unanalyzed=True)

# For each recording with transcript:
# 1. Analyze sentiment
# 2. Classify intent
# 3. Calculate talk/listen ratio
# 4. Generate coaching feedback
# 5. Update call_recordings table
```

---

## Command Reference

### Import Commands

```bash
# Import contacts from CSV
python mojo_sync.py --import-contacts <csv_file>

# Import call logs from CSV
python mojo_sync.py --import-calls <csv_file>
```

### Sync Commands

```bash
# Dry run (preview only)
python mojo_sync.py --sync-fub --dry-run

# Sync everything
python mojo_sync.py --sync-fub

# Sync contacts only
python mojo_sync.py --sync-fub --contacts-only

# Sync calls only
python mojo_sync.py --sync-fub --calls-only

# Limit number of items (testing)
python mojo_sync.py --sync-fub --max-items 10
```

### Analytics Commands

```bash
# Generate all reports
python mojo_sync.py --export-analytics

# Custom output directory
python mojo_sync.py --export-analytics --output-dir custom_reports/

# Show database statistics
python mojo_sync.py --stats
```

### Combined Workflow

```bash
# Complete pipeline: import → analyze → sync
python mojo_sync.py \
  --import-contacts contacts.csv \
  --import-calls calls.csv \
  --export-analytics \
  --sync-fub
```

---

## Troubleshooting

### Issue: "No contacts to sync"

**Cause**: Contacts need email or phone to sync to FUB

**Solution**: Check your Mojo CSV export includes email/phone columns

```bash
# Verify contacts have email/phone
sqlite3 mojo_data.db "SELECT COUNT(*) FROM contacts WHERE email IS NOT NULL OR phone IS NOT NULL"
```

### Issue: "Failed to sync contact"

**Cause**: FUB API error (duplicate, rate limit, etc.)

**Solution**: Check error message, may be:
- Duplicate contact (already exists in FUB)
- Invalid email/phone format
- Rate limit (tool will retry automatically)

### Issue: Call logs not syncing

**Cause**: Calls only sync for contacts already in FUB

**Solution**: Sync contacts first
```bash
# 1. Sync contacts
python mojo_sync.py --sync-fub --contacts-only

# 2. Then sync calls
python mojo_sync.py --sync-fub --calls-only
```

### Issue: CSV import errors

**Cause**: Column names don't match expected format

**Solution**: Edit `mojo_extractor.py` field mappings:
- Check `CONTACT_FIELD_MAP` and `CALL_LOG_FIELD_MAP`
- Add your CSV column names to the mappings

### Issue: Database locked

**Cause**: Another process is using the database

**Solution**: Close other processes or specify different DB path
```bash
export MOJO_DB_PATH=mojo_data_v2.db
python mojo_sync.py --stats
```

---

## Best Practices

### Regular Sync Schedule

**Weekly:**
1. Export last 7 days of calls from Mojo
2. Import to database
3. Sync to FUB
4. Generate coaching reports

```bash
# Weekly sync script
python mojo_sync.py --import-calls mojo_calls_$(date +%Y%m%d).csv
python mojo_sync.py --sync-fub --calls-only
python mojo_sync.py --export-analytics
```

**Monthly:**
1. Export all contacts (full refresh)
2. Import to database
3. Sync new/updated contacts to FUB
4. Generate comprehensive reports

### Data Retention

- SQLite database: Keep indefinitely (it's your source of truth)
- CSV exports: Keep 90 days for backup
- Call recordings: Mojo stores for 90 days (download if needed for long-term analysis)

### Performance Optimization

**Large imports (100k+ records):**
- Import in batches
- Use `--max-items` flag for testing
- Run during off-hours to avoid rate limits

**Analytics:**
- Pre-compute metrics using `analytics_summary` table
- Run analytics weekly to avoid processing entire dataset

---

## Future Enhancements

### Phase 1: Call Recording Download (Current)
- Manual download from Mojo UI
- Store `recording_url` in database
- Access for review/coaching

### Phase 2: Transcript Integration
- Partner with Outdoo or use AWS Transcribe
- Populate `call_recordings.transcript`
- Enable text-based analysis

### Phase 3: AI Analysis
- Sentiment analysis (Claude/GPT)
- Intent classification
- Talk/listen ratio calculation
- Automated coaching feedback

### Phase 4: Mojo API Integration
- Replace CSV imports with API calls
- Real-time sync
- Automatic recording downloads
- See `mojo_extractor.py` → `MojoAPIClient` (placeholder)

### Phase 5: Advanced Analytics
- Predictive lead scoring
- Conversion probability
- Best time to call
- Script optimization suggestions

---

## Data Privacy & Security

### Local Storage
- SQLite database is stored locally
- Not transmitted except FUB sync
- Add to `.gitignore` (already done)

### FUB Sync
- Only syncs data you choose
- Uses official FUB API (secure HTTPS)
- Respects FUB permissions

### Call Recordings
- Only stores URLs (not audio files)
- Download manually if needed
- Comply with state recording laws

---

## Support & Resources

### Mojo Dialer
- Support: www.mojosells.com
- Knowledge Base: knowledge.mojosells.com
- For API access: Contact Mojo sales/support

### Follow Up Boss
- API Docs: docs.followupboss.com
- Support: api@followupboss.com
- Get API Key: Admin → API in FUB dashboard

### This Tool
- Issues: GitHub repository
- Questions: Contact your integration engineer

---

## Appendix: Example Workflow

### For Dee (ISA) - Weekly Routine

**Monday Morning:**
```bash
# 1. Export last week's calls from Mojo
# (Do this manually in Mojo UI)

# 2. Import and sync
cd try_git
python mojo_sync.py --import-calls ~/Downloads/mojo_calls_weekly.csv
python mojo_sync.py --sync-fub --calls-only

# 3. Review coaching report
python mojo_sync.py --export-analytics
cat output/analytics/coaching_report_*.txt
```

**End of Month:**
```bash
# Full refresh: contacts + calls + comprehensive reports
python mojo_sync.py \
  --import-contacts ~/Downloads/mojo_contacts_full.csv \
  --import-calls ~/Downloads/mojo_calls_monthly.csv \
  --sync-fub \
  --export-analytics

# Review metrics
python mojo_sync.py --stats
```

### For Jeremy (Owner) - Monthly Review

```bash
# Generate comprehensive analytics
python mojo_sync.py --export-analytics --output-dir reports/$(date +%Y%m)

# Open in Excel/Google Sheets:
# - agent_metrics_*.json (convert to spreadsheet)
# - coaching_opportunities_*.csv
# - call_logs_*.csv

# Run SQL queries for custom analysis
sqlite3 mojo_data.db < custom_queries.sql > monthly_report.txt
```

---

## License

MIT License - Big Red Barn Properties

---

**Questions?** Contact your integration engineer.

**Version:** 1.0.0
**Last Updated:** November 2025
