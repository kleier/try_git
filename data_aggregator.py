"""
Data Aggregator
Combines and organizes data from FollowUpBoss API
"""

from typing import Dict, List
from collections import defaultdict
from datetime import datetime


class ConversationAggregator:
    """Aggregates conversations and interactions by person"""

    def __init__(self, people: List[Dict], events: List[Dict], text_messages: List[Dict]):
        """
        Initialize aggregator with data from FollowUpBoss

        Args:
            people: List of people records
            events: List of event records
            text_messages: List of text message records
        """
        self.people = people
        self.events = events
        self.text_messages = text_messages

        # Create lookup dictionaries
        self.people_by_id = {p.get('id'): p for p in people if p.get('id')}

    def aggregate_by_person(self) -> List[Dict]:
        """
        Aggregate all interactions by person

        Returns:
            List of person records with their conversations and interactions
        """
        # Group events by person
        events_by_person = defaultdict(list)
        for event in self.events:
            person_id = event.get('personId')
            if person_id:
                events_by_person[person_id].append(event)

        # Group text messages by person
        messages_by_person = defaultdict(list)
        for msg in self.text_messages:
            person_id = msg.get('personId')
            if person_id:
                messages_by_person[person_id].append(msg)

        # Combine all data
        aggregated_data = []

        for person_id, person in self.people_by_id.items():
            person_data = {
                'person': person,
                'events': sorted(
                    events_by_person.get(person_id, []),
                    key=lambda x: x.get('created', ''),
                    reverse=True
                ),
                'text_messages': sorted(
                    messages_by_person.get(person_id, []),
                    key=lambda x: x.get('created', ''),
                    reverse=True
                ),
            }

            # Calculate engagement metrics
            person_data['metrics'] = self._calculate_metrics(person_data)

            # Only include people with interactions
            if person_data['events'] or person_data['text_messages']:
                aggregated_data.append(person_data)

        # Sort by most recent activity
        aggregated_data.sort(
            key=lambda x: x['metrics']['last_activity'],
            reverse=True
        )

        return aggregated_data

    def _calculate_metrics(self, person_data: Dict) -> Dict:
        """
        Calculate engagement metrics for a person

        Args:
            person_data: Person data with events and messages

        Returns:
            Dictionary of metrics
        """
        events = person_data['events']
        messages = person_data['text_messages']

        # Get all activity dates
        activity_dates = []

        for event in events:
            created = event.get('created')
            if created:
                activity_dates.append(created)

        for msg in messages:
            created = msg.get('created')
            if created:
                activity_dates.append(created)

        # Calculate metrics
        metrics = {
            'total_events': len(events),
            'total_messages': len(messages),
            'total_interactions': len(events) + len(messages),
            'last_activity': max(activity_dates) if activity_dates else None,
            'first_activity': min(activity_dates) if activity_dates else None,
        }

        # Count event types
        event_types = defaultdict(int)
        for event in events:
            event_type = event.get('type', 'unknown')
            event_types[event_type] += 1

        metrics['event_types'] = dict(event_types)

        return metrics

    def get_summary_statistics(self) -> Dict:
        """
        Get overall summary statistics

        Returns:
            Dictionary of summary statistics
        """
        aggregated = self.aggregate_by_person()

        stats = {
            'total_people': len(self.people),
            'people_with_interactions': len(aggregated),
            'total_events': len(self.events),
            'total_text_messages': len(self.text_messages),
            'total_interactions': len(self.events) + len(self.text_messages),
        }

        # Event type breakdown
        event_types = defaultdict(int)
        for event in self.events:
            event_type = event.get('type', 'unknown')
            event_types[event_type] += 1

        stats['event_type_breakdown'] = dict(event_types)

        # Top engaged people
        top_people = sorted(
            aggregated,
            key=lambda x: x['metrics']['total_interactions'],
            reverse=True
        )[:10]

        stats['top_engaged_people'] = [
            {
                'name': p['person'].get('name', 'Unknown'),
                'email': p['person'].get('emails', [{}])[0].get('value') if p['person'].get('emails') else None,
                'total_interactions': p['metrics']['total_interactions'],
                'last_activity': p['metrics']['last_activity']
            }
            for p in top_people
        ]

        return stats

    def format_conversation_for_summary(self, person_data: Dict) -> str:
        """
        Format a person's conversation data for AI summarization

        Args:
            person_data: Aggregated person data

        Returns:
            Formatted string representation
        """
        person = person_data['person']
        events = person_data['events']
        messages = person_data['text_messages']
        metrics = person_data['metrics']

        # Build conversation text
        lines = []

        # Person info
        name = person.get('name', 'Unknown')
        emails = person.get('emails', [])
        email = emails[0].get('value') if emails else 'No email'

        lines.append(f"=== Contact: {name} ({email}) ===")
        lines.append(f"Total Interactions: {metrics['total_interactions']}")
        lines.append(f"Last Activity: {metrics['last_activity']}")
        lines.append("")

        # Events
        if events:
            lines.append("--- Events ---")
            for event in events[:20]:  # Limit to most recent 20
                event_type = event.get('type', 'unknown')
                created = event.get('created', 'unknown date')
                message = event.get('message', '')
                source = event.get('source', '')

                lines.append(f"[{created}] {event_type}")
                if message:
                    lines.append(f"  {message}")
                if source:
                    lines.append(f"  Source: {source}")

            lines.append("")

        # Text messages
        if messages:
            lines.append("--- Text Messages ---")
            for msg in messages[:20]:  # Limit to most recent 20
                created = msg.get('created', 'unknown date')
                body = msg.get('body', '')
                direction = msg.get('direction', 'unknown')

                lines.append(f"[{created}] {direction}: {body}")

            lines.append("")

        lines.append("=" * 50)
        lines.append("")

        return "\n".join(lines)
