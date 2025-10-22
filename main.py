#!/usr/bin/env python3
"""
FollowUpBoss Conversation Summarizer
Main script to fetch, aggregate, and summarize conversations
"""

import os
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

from fub_client import FollowUpBossClient
from data_aggregator import ConversationAggregator
from summarizer import ConversationSummarizer
from motion_webhook import MotionWebhookSender


def load_config():
    """Load configuration from environment variables"""
    load_dotenv()

    fub_api_key = os.getenv('FOLLOWUPBOSS_API_KEY')
    anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')

    if not fub_api_key:
        print("Error: FOLLOWUPBOSS_API_KEY not found in environment variables")
        print("Please copy .env.example to .env and add your API key")
        sys.exit(1)

    if not anthropic_api_key:
        print("Warning: ANTHROPIC_API_KEY not found. AI summarization will be skipped.")
        anthropic_api_key = None

    motion_webhook_url = os.getenv('MOTION_WEBHOOK_URL')
    if not motion_webhook_url:
        print("Info: MOTION_WEBHOOK_URL not found. Motion integration will be skipped.")

    config = {
        'fub_api_key': fub_api_key,
        'anthropic_api_key': anthropic_api_key,
        'motion_webhook_url': motion_webhook_url,
        'max_people': int(os.getenv('MAX_PEOPLE', 100)),
        'max_events': int(os.getenv('MAX_EVENTS', 500)),
        'max_text_messages': int(os.getenv('MAX_TEXT_MESSAGES', 500)),
    }

    return config


def filter_by_last_24_hours(items, date_field='created'):
    """
    Filter items to only include those from the last 24 hours

    Args:
        items: List of items with date fields
        date_field: Name of the date field to filter on

    Returns:
        Filtered list of items from last 24 hours
    """
    if not items:
        return []

    # Calculate 24 hours ago
    twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)

    filtered_items = []
    for item in items:
        created_str = item.get(date_field)
        if not created_str:
            continue

        try:
            # Parse the ISO 8601 date string
            # Handle both with and without 'Z' suffix
            created_str = created_str.replace('Z', '+00:00')
            if '.' in created_str:
                # Has microseconds
                created_date = datetime.fromisoformat(created_str.split('+')[0])
            else:
                created_date = datetime.fromisoformat(created_str.split('+')[0])

            # Check if within last 24 hours
            if created_date >= twenty_four_hours_ago:
                filtered_items.append(item)

        except (ValueError, AttributeError) as e:
            # Skip items with invalid dates
            continue

    return filtered_items


def fetch_data(config):
    """Fetch data from FollowUpBoss API"""
    print("=" * 60)
    print("FETCHING DATA FROM FOLLOWUPBOSS (LAST 24 HOURS)")
    print("=" * 60)

    client = FollowUpBossClient(config['fub_api_key'])

    print("\n1. Fetching people...")
    people = client.get_all_people(max_records=config['max_people'])
    print(f"   Retrieved {len(people)} people")

    print("\n2. Fetching events (last 24 hours)...")
    all_events = client.get_all_events(max_records=config['max_events'])
    events = filter_by_last_24_hours(all_events)
    print(f"   Retrieved {len(all_events)} total events")
    print(f"   Filtered to {len(events)} events from last 24 hours")

    print("\n3. Fetching text messages (last 24 hours)...")
    try:
        all_text_messages = client.get_all_text_messages(max_records=config['max_text_messages'])
        text_messages = filter_by_last_24_hours(all_text_messages)
        print(f"   Retrieved {len(all_text_messages)} total text messages")
        print(f"   Filtered to {len(text_messages)} text messages from last 24 hours")
    except Exception as e:
        print(f"   Warning: Could not fetch text messages (this is optional)")
        print(f"   Reason: {str(e)}")
        print(f"   Continuing with people and events data only...")
        text_messages = []

    return people, events, text_messages


def aggregate_data(people, events, text_messages):
    """Aggregate and analyze data"""
    print("\n" + "=" * 60)
    print("AGGREGATING DATA")
    print("=" * 60)

    aggregator = ConversationAggregator(people, events, text_messages)

    print("\nAggregating conversations by person...")
    aggregated_data = aggregator.aggregate_by_person()
    print(f"Found {len(aggregated_data)} people with interactions")

    print("\nCalculating summary statistics...")
    summary_stats = aggregator.get_summary_statistics()

    return aggregated_data, summary_stats, aggregator


def save_data(aggregated_data, summary_stats, output_dir="output"):
    """Save aggregated data to files"""
    print("\n" + "=" * 60)
    print("SAVING DATA")
    print("=" * 60)

    # Create output directory
    Path(output_dir).mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save summary statistics
    stats_file = f"{output_dir}/summary_stats_{timestamp}.json"
    with open(stats_file, 'w') as f:
        json.dump(summary_stats, f, indent=2)
    print(f"\nSaved summary statistics to: {stats_file}")

    # Save aggregated data
    data_file = f"{output_dir}/aggregated_data_{timestamp}.json"
    with open(data_file, 'w') as f:
        json.dump(aggregated_data, f, indent=2)
    print(f"Saved aggregated data to: {data_file}")

    return stats_file, data_file


def print_summary_stats(summary_stats):
    """Print summary statistics to console"""
    print("\n" + "=" * 60)
    print("SUMMARY STATISTICS (LAST 24 HOURS)")
    print("=" * 60)

    print(f"\nTotal People: {summary_stats['total_people']}")
    print(f"People with Interactions: {summary_stats['people_with_interactions']}")
    print(f"Total Events: {summary_stats['total_events']}")
    print(f"Total Text Messages: {summary_stats['total_text_messages']}")
    print(f"Total Interactions: {summary_stats['total_interactions']}")

    if summary_stats.get('event_type_breakdown'):
        print("\nEvent Type Breakdown:")
        for event_type, count in sorted(
            summary_stats['event_type_breakdown'].items(),
            key=lambda x: x[1],
            reverse=True
        ):
            print(f"  {event_type}: {count}")

    if summary_stats.get('top_engaged_people'):
        print("\nTop 10 Most Engaged People:")
        for i, person in enumerate(summary_stats['top_engaged_people'], 1):
            print(f"  {i}. {person['name']} ({person.get('email', 'no email')})")
            print(f"     Interactions: {person['total_interactions']}")
            print(f"     Last Activity: {person['last_activity']}")


def generate_ai_summaries(config, aggregated_data, summary_stats):
    """Generate AI summaries if API key is available"""
    if not config['anthropic_api_key']:
        print("\nSkipping AI summarization (no API key provided)")
        return None

    print("\n" + "=" * 60)
    print("GENERATING AI INSIGHTS")
    print("=" * 60)

    try:
        summarizer = ConversationSummarizer(config['anthropic_api_key'])

        print("\n1. Generating business insights...")
        business_insights = summarizer.generate_business_insights(
            summary_stats,
            aggregated_data,
            max_conversations=50
        )

        # Check if the result is an error message
        if business_insights.startswith("Error generating"):
            print(f"\n⚠️  {business_insights}")
            print("   Skipping AI summarization. Your data is still saved locally!")
            return None

        print("\n2. Generating individual conversation summaries...")
        individual_summaries = summarizer.generate_individual_summaries(
            aggregated_data,
            max_people=20
        )

        return {
            'business_insights': business_insights,
            'individual_summaries': individual_summaries
        }

    except Exception as e:
        error_msg = str(e)
        print(f"\n⚠️  Could not generate AI summaries")

        # Check for common errors
        if "credit balance" in error_msg.lower():
            print("   Reason: Anthropic API has insufficient credits")
            print("   Solution: Add credits at https://console.anthropic.com or remove ANTHROPIC_API_KEY from .env")
        elif "api_key" in error_msg.lower():
            print("   Reason: Invalid Anthropic API key")
            print("   Solution: Check your API key at https://console.anthropic.com")
        else:
            print(f"   Reason: {error_msg}")

        print("   Your FollowUpBoss data is still saved locally!")
        return None


def save_ai_summaries(ai_summaries, output_dir="output"):
    """Save AI summaries to files"""
    if not ai_summaries:
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save business insights
    insights_file = f"{output_dir}/business_insights_{timestamp}.txt"
    with open(insights_file, 'w') as f:
        f.write("BUSINESS INSIGHTS\n")
        f.write("=" * 60 + "\n\n")
        f.write(ai_summaries['business_insights'])
    print(f"\nSaved business insights to: {insights_file}")

    # Save individual summaries
    summaries_file = f"{output_dir}/individual_summaries_{timestamp}.json"
    with open(summaries_file, 'w') as f:
        json.dump(ai_summaries['individual_summaries'], f, indent=2)
    print(f"Saved individual summaries to: {summaries_file}")

    # Also create a readable text version
    summaries_txt = f"{output_dir}/individual_summaries_{timestamp}.txt"
    with open(summaries_txt, 'w') as f:
        f.write("INDIVIDUAL CONVERSATION SUMMARIES\n")
        f.write("=" * 60 + "\n\n")

        for summary in ai_summaries['individual_summaries']:
            f.write(f"\n{summary['name']}\n")
            f.write("-" * 60 + "\n")
            f.write(f"Email: {summary.get('email', 'N/A')}\n")
            f.write(f"Phone: {summary.get('phone', 'N/A')}\n")
            f.write(f"Total Interactions: {summary['total_interactions']}\n")
            f.write(f"Last Activity: {summary['last_activity']}\n")
            f.write(f"\nSummary:\n{summary['summary']}\n")
            f.write("\n" + "=" * 60 + "\n")

    print(f"Saved readable summaries to: {summaries_txt}")

    # Print business insights to console
    print("\n" + "=" * 60)
    print("BUSINESS INSIGHTS")
    print("=" * 60)
    print("\n" + ai_summaries['business_insights'])


def send_to_motion_webhook(config, summary_stats, aggregated_data):
    """Send summary data and detailed conversations to Motion webhook if configured"""
    if not config.get('motion_webhook_url'):
        print("\nSkipping Motion webhook (no URL configured)")
        return

    print("\n" + "=" * 60)
    print("SENDING DATA TO MOTION")
    print("=" * 60)

    webhook_sender = MotionWebhookSender(config['motion_webhook_url'])

    # Send the summary with detailed conversation data
    success = webhook_sender.send_summary(summary_stats, aggregated_data)

    if success:
        # Also print formatted text for reference
        formatted_text = webhook_sender.format_summary_text(summary_stats)
        print("\n📋 Preview of data sent:")
        print(formatted_text)

        # Show conversation count
        active_conversations = len([p for p in aggregated_data if p['events'] or p['text_messages']])
        print(f"\n✅ Sent {active_conversations} detailed conversations to Motion")
    else:
        print("\n⚠️  Motion webhook failed, but data is still saved locally")


def main():
    """Main execution function"""
    print("\nFollowUpBoss Conversation Summarizer - Last 24 Hours")
    print("=" * 60)

    # Load configuration
    config = load_config()

    # Fetch data from API
    people, events, text_messages = fetch_data(config)

    # Aggregate data
    aggregated_data, summary_stats, aggregator = aggregate_data(
        people, events, text_messages
    )

    # Print summary statistics
    print_summary_stats(summary_stats)

    # Save data
    save_data(aggregated_data, summary_stats)

    # Send to Motion webhook
    send_to_motion_webhook(config, summary_stats, aggregated_data)

    # Generate and save AI summaries
    ai_summaries = generate_ai_summaries(config, aggregated_data, summary_stats)
    if ai_summaries:
        save_ai_summaries(ai_summaries)

    print("\n" + "=" * 60)
    print("COMPLETE!")
    print("=" * 60)
    print("\nCheck the 'output' directory for all generated files.")
    if config.get('motion_webhook_url'):
        print("Data has also been sent to Motion!")


if __name__ == "__main__":
    main()
