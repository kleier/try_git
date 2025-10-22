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

    def send_summary(self, summary_stats: Dict) -> bool:
        """
        Send summary statistics to Motion webhook

        Args:
            summary_stats: Summary statistics dictionary

        Returns:
            True if successful, False otherwise
        """
        try:
            # Build the payload according to WEBHOOK_PAYLOAD_SPEC.md
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
