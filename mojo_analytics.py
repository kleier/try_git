"""
Mojo Dialer Analytics and CSV Export
Provides analytics queries and exports for AI coaching pipeline
"""

import csv
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
import json


class MojoAnalytics:
    """Analytics and export functionality for Mojo data"""

    def __init__(self, database):
        """
        Initialize analytics module

        Args:
            database: MojoDatabase instance
        """
        self.db = database

    def export_contacts_csv(self, output_path: str, include_synced: bool = True) -> int:
        """
        Export contacts to CSV for analytics

        Args:
            output_path: Path for output CSV file
            include_synced: Include already-synced contacts

        Returns:
            Number of records exported
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM contacts"
            if not include_synced:
                query += " WHERE synced_to_fub = 0"
            query += " ORDER BY created_date DESC"

            cursor.execute(query)
            rows = cursor.fetchall()

            if not rows:
                print("No contacts to export")
                return 0

            # Write CSV
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                # Get column names
                columns = [desc[0] for desc in cursor.description]
                writer = csv.DictWriter(f, fieldnames=columns)

                writer.writeheader()
                for row in rows:
                    writer.writerow(dict(row))

            print(f"Exported {len(rows)} contacts to {output_path}")
            return len(rows)

    def export_call_logs_csv(self, output_path: str, include_synced: bool = True,
                            days_back: Optional[int] = None) -> int:
        """
        Export call logs to CSV for analytics

        Args:
            output_path: Path for output CSV file
            include_synced: Include already-synced calls
            days_back: Only include calls from last N days

        Returns:
            Number of records exported
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            query = """
                SELECT
                    cl.*,
                    c.full_name as contact_name,
                    c.email as contact_email,
                    c.list_name as contact_list
                FROM call_logs cl
                LEFT JOIN contacts c ON cl.contact_id = c.id
                WHERE 1=1
            """

            params = []
            if not include_synced:
                query += " AND cl.synced_to_fub = 0"

            if days_back:
                cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()
                query += " AND cl.call_date >= ?"
                params.append(cutoff_date)

            query += " ORDER BY cl.call_date DESC"

            cursor.execute(query, params)
            rows = cursor.fetchall()

            if not rows:
                print("No call logs to export")
                return 0

            # Write CSV
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                columns = [desc[0] for desc in cursor.description]
                writer = csv.DictWriter(f, fieldnames=columns)

                writer.writeheader()
                for row in rows:
                    writer.writerow(dict(row))

            print(f"Exported {len(rows)} call logs to {output_path}")
            return len(rows)

    def export_recordings_for_analysis(self, output_path: str, only_unanalyzed: bool = True) -> int:
        """
        Export call recordings data for AI analysis pipeline

        Args:
            output_path: Path for output CSV file
            only_unanalyzed: Only export recordings without transcripts

        Returns:
            Number of records exported
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            query = """
                SELECT
                    cl.id as call_id,
                    cl.mojo_call_id,
                    cl.call_date,
                    cl.call_duration,
                    cl.call_result,
                    cl.agent_name,
                    cl.recording_url,
                    cl.notes,
                    c.full_name as contact_name,
                    c.email as contact_email,
                    c.phone as contact_phone,
                    cr.transcript,
                    cr.sentiment_score,
                    cr.sentiment_label,
                    cr.intent_classification,
                    cr.talk_listen_ratio,
                    cr.ai_coaching_notes
                FROM call_logs cl
                LEFT JOIN contacts c ON cl.contact_id = c.id
                LEFT JOIN call_recordings cr ON cl.id = cr.call_log_id
                WHERE cl.has_recording = 1
            """

            if only_unanalyzed:
                query += " AND (cr.transcript IS NULL OR cr.transcript = '')"

            query += " ORDER BY cl.call_date DESC"

            cursor.execute(query)
            rows = cursor.fetchall()

            if not rows:
                print("No recordings to export")
                return 0

            # Write CSV
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                columns = [desc[0] for desc in cursor.description]
                writer = csv.DictWriter(f, fieldnames=columns)

                writer.writeheader()
                for row in rows:
                    writer.writerow(dict(row))

            print(f"Exported {len(rows)} recordings for analysis to {output_path}")
            return len(rows)

    def get_agent_performance_metrics(self, agent_name: Optional[str] = None,
                                     days_back: int = 30) -> Dict[str, Any]:
        """
        Get performance metrics for an agent (or all agents)

        Args:
            agent_name: Specific agent name (None for all agents)
            days_back: Number of days to analyze

        Returns:
            Dictionary of performance metrics
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()

            # Base query
            where_clause = "WHERE call_date >= ?"
            params = [cutoff_date]

            if agent_name:
                where_clause += " AND agent_name = ?"
                params.append(agent_name)

            # Total calls
            cursor.execute(f"SELECT COUNT(*) FROM call_logs {where_clause}", params)
            total_calls = cursor.fetchone()[0]

            # Call results breakdown
            cursor.execute(f"""
                SELECT call_result, COUNT(*) as count
                FROM call_logs
                {where_clause}
                GROUP BY call_result
            """, params)
            call_results = {row[0]: row[1] for row in cursor.fetchall() if row[0]}

            # Average call duration
            cursor.execute(f"""
                SELECT AVG(call_duration) as avg_duration
                FROM call_logs
                {where_clause} AND call_duration IS NOT NULL
            """, params)
            avg_duration = cursor.fetchone()[0] or 0

            # Contact rate (successful contacts / total calls)
            contacts = call_results.get('Contact', 0) + call_results.get('DNC Contact', 0)
            contact_rate = (contacts / total_calls * 100) if total_calls > 0 else 0

            # Calls with recordings
            cursor.execute(f"""
                SELECT COUNT(*) FROM call_logs
                {where_clause} AND has_recording = 1
            """, params)
            recordings_count = cursor.fetchone()[0]

            # Sentiment analysis (if available)
            cursor.execute(f"""
                SELECT
                    AVG(cr.sentiment_score) as avg_sentiment,
                    AVG(cr.talk_listen_ratio) as avg_talk_listen,
                    COUNT(CASE WHEN cr.sentiment_label = 'Positive' THEN 1 END) as positive_count,
                    COUNT(CASE WHEN cr.sentiment_label = 'Negative' THEN 1 END) as negative_count
                FROM call_logs cl
                JOIN call_recordings cr ON cl.id = cr.call_log_id
                {where_clause}
            """, params)
            sentiment_row = cursor.fetchone()

            metrics = {
                'agent_name': agent_name or 'All Agents',
                'period_days': days_back,
                'total_calls': total_calls,
                'call_results': call_results,
                'avg_call_duration_seconds': round(avg_duration, 2),
                'contact_rate_percent': round(contact_rate, 2),
                'recordings_count': recordings_count,
                'recordings_percent': round(recordings_count / total_calls * 100, 2) if total_calls > 0 else 0,
            }

            if sentiment_row and sentiment_row[0] is not None:
                metrics['sentiment_analysis'] = {
                    'avg_sentiment_score': round(sentiment_row[0], 3),
                    'avg_talk_listen_ratio': round(sentiment_row[1], 3) if sentiment_row[1] else None,
                    'positive_calls': sentiment_row[2],
                    'negative_calls': sentiment_row[3],
                }

            return metrics

    def get_call_intent_breakdown(self, days_back: int = 30) -> Dict[str, int]:
        """
        Get breakdown of call intents from AI analysis

        Args:
            days_back: Number of days to analyze

        Returns:
            Dictionary mapping intent to count
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()

            cursor.execute("""
                SELECT cr.intent_classification, COUNT(*) as count
                FROM call_recordings cr
                JOIN call_logs cl ON cr.call_log_id = cl.id
                WHERE cl.call_date >= ? AND cr.intent_classification IS NOT NULL
                GROUP BY cr.intent_classification
                ORDER BY count DESC
            """, (cutoff_date,))

            return {row[0]: row[1] for row in cursor.fetchall()}

    def get_coaching_opportunities(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get calls that need coaching attention (low sentiment, poor talk/listen ratio, etc.)

        Args:
            limit: Maximum number of opportunities to return

        Returns:
            List of calls needing coaching attention
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            # Find calls with:
            # - Negative sentiment
            # - Poor talk/listen ratio (agent talking too much)
            # - Short duration on contact calls
            cursor.execute("""
                SELECT
                    cl.id,
                    cl.call_date,
                    cl.agent_name,
                    c.full_name as contact_name,
                    cl.call_result,
                    cl.call_duration,
                    cr.sentiment_score,
                    cr.sentiment_label,
                    cr.talk_listen_ratio,
                    cr.intent_classification,
                    cr.ai_coaching_notes,
                    cl.recording_url
                FROM call_logs cl
                JOIN call_recordings cr ON cl.id = cr.call_log_id
                LEFT JOIN contacts c ON cl.contact_id = c.id
                WHERE (
                    cr.sentiment_score < -0.3  -- Negative sentiment
                    OR cr.talk_listen_ratio > 2.0  -- Agent talking too much
                    OR (cl.call_result = 'Contact' AND cl.call_duration < 60)  -- Very short contacts
                )
                AND cl.call_date >= date('now', '-30 days')
                ORDER BY
                    CASE
                        WHEN cr.sentiment_score < -0.5 THEN 1
                        WHEN cr.talk_listen_ratio > 3.0 THEN 2
                        ELSE 3
                    END,
                    cl.call_date DESC
                LIMIT ?
            """, (limit,))

            opportunities = []
            for row in cursor.fetchall():
                row_dict = dict(row)

                # Add coaching recommendations
                recommendations = []
                if row_dict['sentiment_score'] and row_dict['sentiment_score'] < -0.3:
                    recommendations.append("Negative sentiment detected - review tone and approach")
                if row_dict['talk_listen_ratio'] and row_dict['talk_listen_ratio'] > 2.0:
                    recommendations.append(f"High talk/listen ratio ({row_dict['talk_listen_ratio']:.1f}) - practice active listening")
                if row_dict['call_result'] == 'Contact' and row_dict['call_duration'] < 60:
                    recommendations.append("Very short contact - improve engagement techniques")

                row_dict['coaching_recommendations'] = recommendations
                opportunities.append(row_dict)

            return opportunities

    def export_analytics_report(self, output_dir: str = "output/analytics") -> Dict[str, str]:
        """
        Generate comprehensive analytics report with multiple CSV exports

        Args:
            output_dir: Directory for output files

        Returns:
            Dictionary mapping report type to file path
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        reports = {}

        # 1. Export all contacts
        contacts_file = output_path / f"contacts_{timestamp}.csv"
        self.export_contacts_csv(str(contacts_file))
        reports['contacts'] = str(contacts_file)

        # 2. Export call logs (last 90 days)
        calls_file = output_path / f"call_logs_{timestamp}.csv"
        self.export_call_logs_csv(str(calls_file), days_back=90)
        reports['call_logs'] = str(calls_file)

        # 3. Export recordings for analysis
        recordings_file = output_path / f"recordings_unanalyzed_{timestamp}.csv"
        self.export_recordings_for_analysis(str(recordings_file))
        reports['recordings'] = str(recordings_file)

        # 4. Export agent performance metrics
        metrics_file = output_path / f"agent_metrics_{timestamp}.json"
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT agent_name FROM call_logs WHERE agent_name IS NOT NULL")
            agents = [row[0] for row in cursor.fetchall()]

        all_metrics = {}
        for agent in agents:
            all_metrics[agent] = self.get_agent_performance_metrics(agent, days_back=30)

        # Add overall metrics
        all_metrics['overall'] = self.get_agent_performance_metrics(None, days_back=30)

        with open(metrics_file, 'w') as f:
            json.dump(all_metrics, f, indent=2)
        reports['agent_metrics'] = str(metrics_file)

        # 5. Export coaching opportunities
        coaching_file = output_path / f"coaching_opportunities_{timestamp}.csv"
        opportunities = self.get_coaching_opportunities(limit=50)

        if opportunities:
            with open(coaching_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=opportunities[0].keys())
                writer.writeheader()
                writer.writerows(opportunities)
            reports['coaching_opportunities'] = str(coaching_file)

        # 6. Export database statistics
        stats_file = output_path / f"database_stats_{timestamp}.json"
        stats = self.db.get_statistics()
        with open(stats_file, 'w') as f:
            json.dump(stats, f, indent=2)
        reports['statistics'] = str(stats_file)

        print(f"\n✅ Analytics reports generated in {output_dir}:")
        for report_type, file_path in reports.items():
            print(f"  - {report_type}: {file_path}")

        return reports

    def generate_coaching_report_text(self, output_path: str) -> str:
        """
        Generate a human-readable coaching report for the ISA

        Args:
            output_path: Path for output text file

        Returns:
            Path to generated report
        """
        opportunities = self.get_coaching_opportunities(limit=20)
        metrics = self.get_agent_performance_metrics(days_back=30)
        intent_breakdown = self.get_call_intent_breakdown(days_back=30)

        with open(output_path, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("MOJO DIALER - ISA COACHING REPORT\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")

            # Overall Performance
            f.write("📊 OVERALL PERFORMANCE (Last 30 Days)\n")
            f.write("-" * 80 + "\n")
            f.write(f"Total Calls: {metrics['total_calls']}\n")
            f.write(f"Contact Rate: {metrics['contact_rate_percent']}%\n")
            f.write(f"Avg Call Duration: {int(metrics['avg_call_duration_seconds'])} seconds\n")
            f.write(f"Recordings Available: {metrics['recordings_count']} ({metrics['recordings_percent']}%)\n")
            f.write("\nCall Results Breakdown:\n")
            for result, count in sorted(metrics['call_results'].items(), key=lambda x: x[1], reverse=True):
                pct = (count / metrics['total_calls'] * 100) if metrics['total_calls'] > 0 else 0
                f.write(f"  • {result}: {count} ({pct:.1f}%)\n")

            # Sentiment Analysis
            if 'sentiment_analysis' in metrics:
                f.write("\n" + "=" * 80 + "\n")
                f.write("😊 SENTIMENT ANALYSIS\n")
                f.write("-" * 80 + "\n")
                sa = metrics['sentiment_analysis']
                f.write(f"Average Sentiment Score: {sa['avg_sentiment_score']:.3f} (-1 to +1 scale)\n")
                f.write(f"Positive Calls: {sa['positive_calls']}\n")
                f.write(f"Negative Calls: {sa['negative_calls']}\n")
                if sa['avg_talk_listen_ratio']:
                    f.write(f"Avg Talk/Listen Ratio: {sa['avg_talk_listen_ratio']:.2f}:1\n")
                    if sa['avg_talk_listen_ratio'] > 1.5:
                        f.write("  ⚠️ Consider listening more and talking less\n")

            # Intent Breakdown
            if intent_breakdown:
                f.write("\n" + "=" * 80 + "\n")
                f.write("🎯 CALL INTENT BREAKDOWN\n")
                f.write("-" * 80 + "\n")
                for intent, count in sorted(intent_breakdown.items(), key=lambda x: x[1], reverse=True):
                    f.write(f"  • {intent}: {count}\n")

            # Coaching Opportunities
            if opportunities:
                f.write("\n" + "=" * 80 + "\n")
                f.write("🎓 COACHING OPPORTUNITIES\n")
                f.write("-" * 80 + "\n")
                f.write(f"Found {len(opportunities)} calls needing attention:\n\n")

                for i, opp in enumerate(opportunities, 1):
                    f.write(f"\n{i}. {opp.get('contact_name', 'Unknown')} - {opp['call_date']}\n")
                    f.write(f"   Agent: {opp['agent_name']}\n")
                    f.write(f"   Result: {opp['call_result']} | Duration: {opp['call_duration']}s\n")
                    if opp.get('sentiment_score'):
                        f.write(f"   Sentiment: {opp['sentiment_label']} ({opp['sentiment_score']:.3f})\n")
                    if opp.get('talk_listen_ratio'):
                        f.write(f"   Talk/Listen Ratio: {opp['talk_listen_ratio']:.2f}:1\n")
                    if opp.get('recording_url'):
                        f.write(f"   Recording: {opp['recording_url']}\n")
                    f.write("   Recommendations:\n")
                    for rec in opp['coaching_recommendations']:
                        f.write(f"   • {rec}\n")
                    if opp.get('ai_coaching_notes'):
                        f.write(f"   AI Notes: {opp['ai_coaching_notes']}\n")

            f.write("\n" + "=" * 80 + "\n")
            f.write("End of Report\n")
            f.write("=" * 80 + "\n")

        print(f"\n✅ Coaching report generated: {output_path}")
        return output_path
