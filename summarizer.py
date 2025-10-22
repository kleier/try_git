"""
AI Summarizer
Uses Claude AI to generate insights from conversations
"""

from typing import Dict, List, Optional
import anthropic
import json


class ConversationSummarizer:
    """Generates AI-powered summaries of conversations"""

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        """
        Initialize the summarizer

        Args:
            api_key: Anthropic API key
            model: Claude model to use
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def summarize_conversation(self, conversation_text: str) -> str:
        """
        Summarize a single conversation

        Args:
            conversation_text: Formatted conversation text

        Returns:
            AI-generated summary
        """
        prompt = f"""Analyze this conversation history from a CRM system and provide a concise summary:

{conversation_text}

Please provide:
1. Key discussion topics
2. Customer intent/interests
3. Stage in the sales process
4. Next recommended actions
5. Any concerns or objections raised

Keep the summary concise and actionable."""

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            return message.content[0].text

        except Exception as e:
            return f"Error generating summary: {str(e)}"

    def generate_business_insights(
        self,
        summary_stats: Dict,
        aggregated_data: List[Dict],
        max_conversations: int = 50
    ) -> str:
        """
        Generate high-level business insights

        Args:
            summary_stats: Overall statistics
            aggregated_data: List of aggregated person data
            max_conversations: Maximum number of conversations to analyze in detail

        Returns:
            AI-generated business insights
        """
        # Prepare data for analysis
        insights_data = {
            'summary_statistics': summary_stats,
            'sample_conversations': []
        }

        # Sample top conversations
        for person_data in aggregated_data[:max_conversations]:
            person = person_data['person']
            metrics = person_data['metrics']

            insights_data['sample_conversations'].append({
                'name': person.get('name', 'Unknown'),
                'interactions': metrics['total_interactions'],
                'last_activity': metrics['last_activity'],
                'event_types': metrics.get('event_types', {}),
                'recent_events': [
                    {
                        'type': e.get('type'),
                        'created': e.get('created'),
                        'message': e.get('message', '')[:100]  # Truncate long messages
                    }
                    for e in person_data['events'][:5]
                ],
                'recent_messages': [
                    {
                        'direction': m.get('direction'),
                        'created': m.get('created'),
                        'body': m.get('body', '')[:100]  # Truncate long messages
                    }
                    for m in person_data['text_messages'][:5]
                ]
            })

        # Generate insights
        data_str = json.dumps(insights_data, indent=2)

        prompt = f"""Analyze this business data from a real estate CRM (FollowUpBoss) and provide strategic insights:

{data_str}

Please provide:

1. OVERALL BUSINESS HEALTH
   - What does the activity level tell us about the business?
   - Are there concerning trends or positive signals?

2. CUSTOMER ENGAGEMENT PATTERNS
   - What types of interactions are most common?
   - How engaged are leads/customers?
   - Quality of conversations

3. KEY OPPORTUNITIES
   - Which leads/customers need immediate attention?
   - Where are the best conversion opportunities?
   - Any leads going cold?

4. OPERATIONAL RECOMMENDATIONS
   - How can the team improve response times?
   - What processes should be optimized?
   - Resource allocation suggestions

5. GROWTH STRATEGIES
   - What's working well that should be scaled?
   - New approaches to consider?

Keep insights actionable and data-driven. Focus on what matters most for growing the business."""

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            return message.content[0].text

        except Exception as e:
            return f"Error generating insights: {str(e)}"

    def generate_individual_summaries(
        self,
        aggregated_data: List[Dict],
        max_people: int = 20
    ) -> List[Dict]:
        """
        Generate summaries for individual conversations

        Args:
            aggregated_data: List of aggregated person data
            max_people: Maximum number of people to summarize

        Returns:
            List of summaries with person info
        """
        summaries = []

        for i, person_data in enumerate(aggregated_data[:max_people]):
            print(f"Generating summary {i+1}/{min(max_people, len(aggregated_data))}...")

            person = person_data['person']

            # Format conversation
            from data_aggregator import ConversationAggregator
            aggregator = ConversationAggregator([], [], [])
            conversation_text = aggregator.format_conversation_for_summary(person_data)

            # Generate summary
            summary = self.summarize_conversation(conversation_text)

            summaries.append({
                'name': person.get('name', 'Unknown'),
                'email': person.get('emails', [{}])[0].get('value') if person.get('emails') else None,
                'phone': person.get('phones', [{}])[0].get('value') if person.get('phones') else None,
                'total_interactions': person_data['metrics']['total_interactions'],
                'last_activity': person_data['metrics']['last_activity'],
                'summary': summary
            })

        return summaries
