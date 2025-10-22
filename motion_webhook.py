"""
Motion Webhook Integration
Sends FollowUpBoss summary data to Motion via webhook
"""

import requests
from typing import Dict, Optional
from datetime import datetime


class MotionWebhookSender:
    """Sends data to Motion via webhook"""

    def __init__(self, webhook_url: str):
        """
        Initialize the webhook sender

        Args:
            webhook_url: Motion webhook URL
        """
        self.webhook_url = webhook_url

    def format_conversations(self, aggregated_data: list, max_people: int = 20) -> list:
        """
        Format detailed conversation data for webhook

        Args:
            aggregated_data: List of person data with events and messages
            max_people: Maximum number of people to include

        Returns:
            List of formatted conversation objects
        """
        conversations = []

        for person_data in aggregated_data[:max_people]:
            person = person_data['person']
            events = person_data['events']
            text_messages = person_data['text_messages']

            # Build conversation details
            conversation = {
                "contact": {
                    "name": person.get('name', 'Unknown'),
                    "email": person.get('emails', [{}])[0].get('value') if person.get('emails') else None,
                    "phone": person.get('phones', [{}])[0].get('value') if person.get('phones') else None,
                },
                "metrics": {
                    "total_interactions": person_data['metrics']['total_interactions'],
                    "total_events": len(events),
                    "total_messages": len(text_messages),
                    "last_activity": person_data['metrics']['last_activity']
                },
                "events": [],
                "text_messages": [],
                "emails": []
            }

            # Add events (calls, notes, meetings, etc.)
            for event in events[:30]:  # Limit to 30 most recent
                event_data = {
                    "type": event.get('type', 'Unknown'),
                    "created": event.get('created'),
                    "message": event.get('message', ''),
                    "source": event.get('source', ''),
                    "subject": event.get('subject', '')
                }

                # Separate emails from other events
                if event.get('type') == 'Email':
                    conversation['emails'].append({
                        "subject": event.get('subject', 'No subject'),
                        "message": event.get('message', ''),
                        "created": event.get('created'),
                        "direction": event.get('direction', 'unknown')
                    })
                else:
                    conversation['events'].append(event_data)

            # Add text messages
            for msg in text_messages[:30]:  # Limit to 30 most recent
                conversation['text_messages'].append({
                    "body": msg.get('body', ''),
                    "created": msg.get('created'),
                    "direction": msg.get('direction', 'unknown'),
                    "from": msg.get('from', ''),
                    "to": msg.get('to', '')
                })

            # Only include if there's activity
            if conversation['events'] or conversation['text_messages'] or conversation['emails']:
                conversations.append(conversation)

        return conversations

    def send_summary(self, summary_stats: Dict, aggregated_data: Optional[list] = None, raw_events: Optional[list] = None, raw_messages: Optional[list] = None) -> bool:
        """
        Send summary statistics, detailed conversations, and raw data to Motion webhook

        Args:
            summary_stats: Summary statistics dictionary
            aggregated_data: Optional list of detailed conversation data
            raw_events: Optional list of raw events from FollowUpBoss API
            raw_messages: Optional list of raw text messages from FollowUpBoss API

        Returns:
            True if successful, False otherwise
        """
        try:
            # Build the payload with ALL data
            payload = {
                "summary": {
                    "total_people": summary_stats.get('total_people', 0),
                    "people_with_interactions": summary_stats.get('people_with_interactions', 0),
                    "total_events": summary_stats.get('total_events', 0),
                    "total_text_messages": summary_stats.get('total_text_messages', 0),
                    "total_interactions": summary_stats.get('total_interactions', 0),
                    "event_type_breakdown": summary_stats.get('event_type_breakdown', {}),
                    "top_engaged_people": summary_stats.get('top_engaged_people', [])
                },
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "data_source": "FollowUpBoss",
                "report_type": "conversation_summary",
                "time_period": "last_24_hours"
            }

            # Add detailed conversations if provided
            if aggregated_data:
                payload["conversations"] = self.format_conversations(aggregated_data, max_people=50)

            # Add ALL raw data from FollowUpBoss API
            payload["raw_data"] = {
                "events": raw_events if raw_events else [],
                "text_messages": raw_messages if raw_messages else [],
                "total_raw_events": len(raw_events) if raw_events else 0,
                "total_raw_messages": len(raw_messages) if raw_messages else 0
            }

            # Send POST request to webhook
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'FollowUpBoss-Summarizer/1.0'
                },
                timeout=30
            )

            # Check response
            response.raise_for_status()

            print(f"\n✅ Successfully sent data to Motion webhook!")
            print(f"   Response status: {response.status_code}")

            return True

        except requests.exceptions.RequestException as e:
            print(f"\n❌ Failed to send data to Motion webhook")
            print(f"   Error: {str(e)}")
            return False

    def format_summary_text(self, summary_stats: Dict) -> str:
        """
        Format summary statistics as readable text

        Args:
            summary_stats: Summary statistics dictionary

        Returns:
            Formatted text summary
        """
        lines = []

        lines.append("📊 FollowUpBoss Summary Report - Last 24 Hours")
        lines.append("")
        lines.append("=" * 50)
        lines.append("")

        # Main stats
        lines.append("📈 OVERALL STATISTICS (LAST 24 HOURS)")
        lines.append(f"• Total Contacts: {summary_stats.get('total_people', 0)}")
        lines.append(f"• Active Contacts: {summary_stats.get('people_with_interactions', 0)}")
        lines.append(f"• Total Interactions: {summary_stats.get('total_interactions', 0)}")
        lines.append(f"• Total Events: {summary_stats.get('total_events', 0)}")
        lines.append(f"• Total Messages: {summary_stats.get('total_text_messages', 0)}")
        lines.append("")

        # Event breakdown
        event_breakdown = summary_stats.get('event_type_breakdown', {})
        if event_breakdown:
            lines.append("📋 EVENT TYPE BREAKDOWN")
            for event_type, count in sorted(event_breakdown.items(), key=lambda x: x[1], reverse=True):
                lines.append(f"• {event_type}: {count}")
            lines.append("")

        # Top engaged people
        top_people = summary_stats.get('top_engaged_people', [])
        if top_people:
            lines.append("🔥 TOP ENGAGED CONTACTS")
            for i, person in enumerate(top_people[:5], 1):
                name = person.get('name', 'Unknown')
                interactions = person.get('total_interactions', 0)
                email = person.get('email', 'No email')
                lines.append(f"{i}. {name} ({email})")
                lines.append(f"   {interactions} interactions")
            lines.append("")

        lines.append("=" * 50)
        lines.append(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")

        return "\n".join(lines)
