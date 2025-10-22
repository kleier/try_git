# FollowUpBoss Webhook Payload Specification

This document describes the exact structure and field names of the JSON payload that will be sent to the webhook URL.

## Payload Structure

The webhook will receive a JSON POST request with the following structure:

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
      }
    ]
  },
  "generated_at": "2025-10-22T14:30:00Z",
  "data_source": "FollowUpBoss",
  "report_type": "conversation_summary"
}
```

---

## Field Definitions

### Root Level Fields

| Field Name | Data Type | Description | Example |
|------------|-----------|-------------|---------|
| `summary` | Object | Contains all summary statistics and metrics | See below |
| `generated_at` | String (ISO 8601 DateTime) | Timestamp when this report was generated | `"2025-10-22T14:30:00Z"` |
| `data_source` | String | The source system (always "FollowUpBoss") | `"FollowUpBoss"` |
| `report_type` | String | Type of report (always "conversation_summary") | `"conversation_summary"` |

---

### Summary Object Fields

| Field Name | Data Type | Description | Example |
|------------|-----------|-------------|---------|
| `total_people` | Integer | Total number of people/contacts in FollowUpBoss | `150` |
| `people_with_interactions` | Integer | Number of people who have at least one interaction (event or message) | `89` |
| `total_events` | Integer | Total number of events (activities, interactions) | `450` |
| `total_text_messages` | Integer | Total number of text messages | `230` |
| `total_interactions` | Integer | Combined total of all events and text messages | `680` |
| `event_type_breakdown` | Object | Count of each event type | See below |
| `top_engaged_people` | Array | List of the 10 most engaged contacts | See below |

---

### Event Type Breakdown Object

This is a dynamic object where keys are event type names and values are counts.

**Common Event Types:**
- `Email` - Email interactions
- `Website Visit` - Website activity
- `Phone Call` - Phone call logs
- `Property View` - Property viewing events
- `Note` - Notes added to contacts
- `Task` - Tasks associated with contacts
- `Meeting` - Meeting events
- `Text Message` - Text message events

**Example:**
```json
{
  "Email": 180,
  "Website Visit": 150,
  "Phone Call": 70,
  "Property View": 50,
  "Note": 35,
  "Task": 25
}
```

| Field Pattern | Data Type | Description |
|---------------|-----------|-------------|
| `{EventType}` | Integer | Number of events of this type |

---

### Top Engaged People Array

Array of the top 10 most engaged contacts, sorted by total interactions (descending).

**Each person object contains:**

| Field Name | Data Type | Description | Example | Can Be Null? |
|------------|-----------|-------------|---------|--------------|
| `name` | String | Full name of the contact | `"John Doe"` | No (defaults to "Unknown") |
| `email` | String | Primary email address | `"john@example.com"` | Yes |
| `total_interactions` | Integer | Total number of interactions for this person | `45` | No |
| `last_activity` | String (ISO 8601 DateTime) | Timestamp of their most recent activity | `"2025-10-20T15:30:00Z"` | Yes |

**Example:**
```json
[
  {
    "name": "John Doe",
    "email": "john@example.com",
    "total_interactions": 45,
    "last_activity": "2025-10-20T15:30:00Z"
  },
  {
    "name": "Jane Smith",
    "email": null,
    "total_interactions": 38,
    "last_activity": "2025-10-21T09:15:00Z"
  }
]
```

---

## Complete Example Payload

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
      "Property View": 50,
      "Note": 35,
      "Task": 25,
      "Meeting": 15,
      "Text Message": 10
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
      },
      {
        "name": "Bob Johnson",
        "email": "bob@example.com",
        "total_interactions": 32,
        "last_activity": "2025-10-19T14:20:00Z"
      },
      {
        "name": "Sarah Williams",
        "email": null,
        "total_interactions": 28,
        "last_activity": "2025-10-18T11:45:00Z"
      },
      {
        "name": "Mike Davis",
        "email": "mike@example.com",
        "total_interactions": 25,
        "last_activity": "2025-10-22T08:30:00Z"
      }
    ]
  },
  "generated_at": "2025-10-22T14:30:00Z",
  "data_source": "FollowUpBoss",
  "report_type": "conversation_summary"
}
```

---

## HTTP Request Details

**Method:** `POST`

**Content-Type:** `application/json`

**Headers:**
```
Content-Type: application/json
User-Agent: FollowUpBoss-Summarizer/1.0
```

**Body:** JSON payload as described above

---

## Data Types Reference

- **String**: Text value, enclosed in quotes
- **Integer**: Whole number (no decimals)
- **Object**: Key-value pairs enclosed in `{}`
- **Array**: List of items enclosed in `[]`
- **ISO 8601 DateTime**: Date/time format like `"2025-10-22T14:30:00Z"`
  - Format: `YYYY-MM-DDTHH:MM:SSZ`
  - Always in UTC timezone (indicated by `Z`)
  - Can be null if no activity exists

---

## Notes for Motion Configuration

1. **Nullable Fields**: `email` and `last_activity` can be `null` if the data doesn't exist
2. **Dynamic Keys**: `event_type_breakdown` keys depend on your actual event types in FollowUpBoss
3. **Array Length**: `top_engaged_people` array always contains up to 10 items (may be fewer if you have less than 10 people)
4. **Timestamps**: All timestamps are in UTC (Coordinated Universal Time)
5. **Encoding**: UTF-8 character encoding
