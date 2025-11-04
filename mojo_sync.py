#!/usr/bin/env python3
"""
Mojo Dialer Sync Tool
Main CLI for extracting Mojo data, storing in SQLite, and syncing to Follow Up Boss
"""

import os
import sys
import argparse
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Import our modules
from mojo_database import MojoDatabase
from mojo_extractor import MojoExtractor
from mojo_analytics import MojoAnalytics
from mojo_fub_sync import MojoFUBSync
from fub_client import FollowUpBossClient


class MojoSync:
    """Main orchestrator for Mojo Dialer sync operations"""

    def __init__(self):
        """Initialize the sync tool"""
        # Load environment variables
        load_dotenv()

        # Initialize database
        self.db = MojoDatabase(db_path=os.getenv('MOJO_DB_PATH', 'mojo_data.db'))

        # Initialize FUB client (if configured)
        self.fub_client = None
        fub_api_key = os.getenv('FOLLOWUPBOSS_API_KEY')
        if fub_api_key:
            self.fub_client = FollowUpBossClient(fub_api_key)

        # Initialize other components
        self.extractor = MojoExtractor()
        self.analytics = MojoAnalytics(self.db)

    def import_contacts(self, csv_path: str) -> bool:
        """Import contacts from CSV"""
        try:
            print(f"\n📥 Importing contacts from {csv_path}...")
            start_time = datetime.now()

            # Parse CSV
            contacts = self.extractor.import_contacts_csv(csv_path)

            if not contacts:
                print("❌ No contacts found in CSV")
                return False

            # Insert into database
            print(f"\n💾 Storing {len(contacts)} contacts in database...")
            imported = 0
            updated = 0

            for contact in contacts:
                try:
                    contact_id = self.db.insert_contact(contact)
                    # Check if this was an update or insert (simplified)
                    imported += 1
                except Exception as e:
                    print(f"  ⚠️  Error storing contact {contact.get('full_name', 'Unknown')}: {e}")
                    continue

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            # Record import history
            self.db.record_import(
                import_type='contacts',
                source_file=csv_path,
                records_imported=imported,
                records_updated=0,
                records_failed=len(self.extractor.errors),
                status='success' if imported > 0 else 'failed',
                error_message='; '.join(self.extractor.errors[:5]) if self.extractor.errors else None,
                started_at=start_time,
                completed_at=end_time
            )

            print(f"\n✅ Import complete in {duration:.1f} seconds:")
            print(f"  • Imported: {imported}")
            print(f"  • Errors: {len(self.extractor.errors)}")

            if self.extractor.errors:
                print(f"\n⚠️  First few errors:")
                for error in self.extractor.errors[:5]:
                    print(f"  • {error}")

            return imported > 0

        except Exception as e:
            print(f"❌ Import failed: {str(e)}")
            return False

    def import_calls(self, csv_path: str) -> bool:
        """Import call logs from CSV"""
        try:
            print(f"\n📥 Importing call logs from {csv_path}...")
            start_time = datetime.now()

            # Parse CSV
            calls = self.extractor.import_call_logs_csv(csv_path)

            if not calls:
                print("❌ No call logs found in CSV")
                return False

            # Insert into database
            print(f"\n💾 Storing {len(calls)} call logs in database...")
            imported = 0

            for call in calls:
                try:
                    call_id = self.db.insert_call_log(call)
                    imported += 1
                except Exception as e:
                    print(f"  ⚠️  Error storing call: {e}")
                    continue

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            # Record import history
            self.db.record_import(
                import_type='calls',
                source_file=csv_path,
                records_imported=imported,
                records_failed=len(self.extractor.errors),
                status='success' if imported > 0 else 'failed',
                started_at=start_time,
                completed_at=end_time
            )

            print(f"\n✅ Import complete in {duration:.1f} seconds:")
            print(f"  • Imported: {imported}")
            print(f"  • Errors: {len(self.extractor.errors)}")

            return imported > 0

        except Exception as e:
            print(f"❌ Import failed: {str(e)}")
            return False

    def sync_to_fub(self, dry_run: bool = False, contacts_only: bool = False,
                   calls_only: bool = False, max_items: int = None) -> bool:
        """Sync data to Follow Up Boss"""
        if not self.fub_client:
            print("❌ Follow Up Boss API key not configured")
            print("   Set FOLLOWUPBOSS_API_KEY in .env file")
            return False

        try:
            sync = MojoFUBSync(self.fub_client, self.db)

            if dry_run:
                # Just show what would be synced
                sync.dry_run_sync(max_contacts=10)
                print("\n💡 This was a dry run. Use --sync to actually sync data.")
                return True

            # Real sync
            if not calls_only:
                sync.sync_contacts(max_contacts=max_items)

            if not contacts_only:
                sync.sync_call_logs(max_calls=max_items)

            # Print report
            print(sync.get_sync_report())

            return True

        except Exception as e:
            print(f"❌ Sync failed: {str(e)}")
            return False

    def export_analytics(self, output_dir: str = "output/analytics") -> bool:
        """Export analytics and reports"""
        try:
            print(f"\n📊 Generating analytics reports...")

            # Generate all analytics reports
            reports = self.analytics.export_analytics_report(output_dir)

            # Generate coaching report
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            coaching_report = Path(output_dir) / f"coaching_report_{timestamp}.txt"
            self.analytics.generate_coaching_report_text(str(coaching_report))

            print(f"\n✅ All reports generated successfully!")
            return True

        except Exception as e:
            print(f"❌ Analytics export failed: {str(e)}")
            return False

    def show_stats(self):
        """Display database statistics"""
        stats = self.db.get_statistics()

        print("\n" + "=" * 60)
        print("📊 MOJO DIALER DATABASE STATISTICS")
        print("=" * 60)

        print(f"\n📇 CONTACTS")
        print(f"  Total: {stats['total_contacts']}")
        print(f"  Synced to FUB: {stats['synced_contacts']}")
        print(f"  Pending: {stats['total_contacts'] - stats['synced_contacts']}")

        print(f"\n📞 CALL LOGS")
        print(f"  Total: {stats['total_calls']}")
        print(f"  Synced to FUB: {stats['synced_calls']}")
        print(f"  Pending: {stats['total_calls'] - stats['synced_calls']}")
        print(f"  With Recordings: {stats['calls_with_recordings']}")

        print(f"\n🎙️  RECORDINGS")
        print(f"  Transcribed: {stats['transcribed_recordings']}")

        if stats['call_results']:
            print(f"\n📋 CALL RESULTS BREAKDOWN")
            for result, count in sorted(stats['call_results'].items(), key=lambda x: x[1], reverse=True):
                pct = (count / stats['total_calls'] * 100) if stats['total_calls'] > 0 else 0
                bar = "█" * int(pct / 2)
                print(f"  {result:20s} {count:5d} ({pct:5.1f}%) {bar}")

        print("\n" + "=" * 60)


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description='Mojo Dialer Data Extraction and Sync Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Import contacts from Mojo CSV export
  python mojo_sync.py --import-contacts mojo_contacts.csv

  # Import call logs
  python mojo_sync.py --import-calls mojo_calls.csv

  # Sync to Follow Up Boss (dry run first)
  python mojo_sync.py --sync-fub --dry-run

  # Actually sync to FUB
  python mojo_sync.py --sync-fub

  # Generate analytics reports
  python mojo_sync.py --export-analytics

  # Show database statistics
  python mojo_sync.py --stats

  # Full workflow: import, analyze, and sync
  python mojo_sync.py --import-contacts contacts.csv --import-calls calls.csv --sync-fub --export-analytics
        """
    )

    # Import options
    parser.add_argument('--import-contacts', metavar='CSV_FILE',
                       help='Import contacts from Mojo CSV export')
    parser.add_argument('--import-calls', metavar='CSV_FILE',
                       help='Import call logs from Mojo CSV export')

    # Sync options
    parser.add_argument('--sync-fub', action='store_true',
                       help='Sync data to Follow Up Boss')
    parser.add_argument('--dry-run', action='store_true',
                       help='Perform dry run (show what would be synced)')
    parser.add_argument('--contacts-only', action='store_true',
                       help='Only sync contacts (not calls)')
    parser.add_argument('--calls-only', action='store_true',
                       help='Only sync calls (not contacts)')
    parser.add_argument('--max-items', type=int,
                       help='Maximum items to sync (for testing)')

    # Analytics options
    parser.add_argument('--export-analytics', action='store_true',
                       help='Export analytics reports and CSVs')
    parser.add_argument('--output-dir', default='output/analytics',
                       help='Output directory for analytics (default: output/analytics)')

    # Info options
    parser.add_argument('--stats', action='store_true',
                       help='Show database statistics')

    args = parser.parse_args()

    # Show help if no arguments
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    # Initialize sync tool
    sync_tool = MojoSync()

    success = True

    # Execute requested operations
    if args.import_contacts:
        if not sync_tool.import_contacts(args.import_contacts):
            success = False

    if args.import_calls:
        if not sync_tool.import_calls(args.import_calls):
            success = False

    if args.sync_fub:
        if not sync_tool.sync_to_fub(
            dry_run=args.dry_run,
            contacts_only=args.contacts_only,
            calls_only=args.calls_only,
            max_items=args.max_items
        ):
            success = False

    if args.export_analytics:
        if not sync_tool.export_analytics(args.output_dir):
            success = False

    if args.stats:
        sync_tool.show_stats()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
