# Field Mapping for Motion Webhook

## Quick Reference - Send This to Motion

---

### Root Level Fields (4 fields)

1. **summary** (Object) - Contains all the statistics and data
2. **generated_at** (String/DateTime) - When the report was created (format: `2025-10-22T14:30:00Z`)
3. **data_source** (String) - Always contains: `"FollowUpBoss"`
4. **report_type** (String) - Always contains: `"conversation_summary"`

---

### Summary Statistics Fields (7 fields inside "summary")

1. **summary.total_people** (Number) - How many total contacts you have
2. **summary.people_with_interactions** (Number) - How many contacts have activity
3. **summary.total_events** (Number) - Total events/activities logged
4. **summary.total_text_messages** (Number) - Total text messages
5. **summary.total_interactions** (Number) - Total of all interactions (events + messages)
6. **summary.event_type_breakdown** (Object) - Count by event type (Email, Calls, etc.)
7. **summary.top_engaged_people** (Array) - List of your 10 most active contacts

---

### Top Engaged People Fields (4 fields per person in array)

Each person in the `summary.top_engaged_people` array has:

1. **name** (String) - Contact's full name
2. **email** (String or null) - Contact's email address (can be empty)
3. **total_interactions** (Number) - How many times you've interacted with them
4. **last_activity** (String/DateTime) - When you last interacted (format: `2025-10-22T14:30:00Z`)

---

## What You'll Probably Want to Map

**For a Motion Task:**

- **Task Title**: Use `report_type` or create a static title like "FollowUpBoss Daily Summary"
- **Task Description**: Use `summary.total_people`, `summary.total_interactions`, and `summary.top_engaged_people`
- **Due Date**: Use `generated_at` or set to today
- **Priority**: Could set based on `summary.total_interactions` (higher = more urgent)

**Suggested Description Template:**
```
FollowUpBoss Summary Report

📊 Stats:
- Total Contacts: {{summary.total_people}}
- Active Contacts: {{summary.people_with_interactions}}
- Total Interactions: {{summary.total_interactions}}
- Events: {{summary.total_events}}
- Messages: {{summary.total_text_messages}}

🔥 Top Engaged Contacts:
{{summary.top_engaged_people[0].name}} - {{summary.top_engaged_people[0].total_interactions}} interactions
{{summary.top_engaged_people[1].name}} - {{summary.top_engaged_people[1].total_interactions}} interactions
{{summary.top_engaged_people[2].name}} - {{summary.top_engaged_people[2].total_interactions}} interactions

Generated: {{generated_at}}
```

---

## Request Format

- **Method**: POST
- **Content-Type**: application/json
- **Body**: JSON object with the fields listed above

---

## Sample Payload (Copy This as Example)

```json
{
  "summary": {
    "total_people": 150,
    "people_with_interactions": 89,
    "total_events": 450,
    "total_text_messages": 230,
    "total_interactions": 680,
    "event_type_breakdown": {
      "Email": 180,
      "Website Visit": 150,
      "Phone Call": 70,
      "Property View": 50
    },
    "top_engaged_people": [
      {
        "name": "John Doe",
        "email": "john@example.com",
        "total_interactions": 45,
        "last_activity": "2025-10-20T15:30:00Z"
      },
      {
        "name": "Jane Smith",
        "email": "jane@example.com",
        "total_interactions": 38,
        "last_activity": "2025-10-21T09:15:00Z"
      }
    ]
  },
  "generated_at": "2025-10-22T14:30:00Z",
  "data_source": "FollowUpBoss",
  "report_type": "conversation_summary"
}
```
