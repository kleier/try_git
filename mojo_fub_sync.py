"""
Mojo to Follow Up Boss Sync Module
Syncs Mojo Dialer contacts and call logs to Follow Up Boss
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import time


class MojoFUBSync:
    """Sync Mojo Dialer data to Follow Up Boss"""

    def __init__(self, fub_client, mojo_db):
        """
        Initialize the sync module

        Args:
            fub_client: FollowUpBossClient instance
            mojo_db: MojoDatabase instance
        """
        self.fub = fub_client
        self.db = mojo_db
        self.sync_stats = {
            'contacts_synced': 0,
            'contacts_failed': 0,
            'calls_synced': 0,
            'calls_failed': 0,
            'errors': []
        }

    def sync_contacts(self, batch_size: int = 50, max_contacts: Optional[int] = None) -> Dict[str, int]:
        """
        Sync contacts from Mojo to Follow Up Boss

        Args:
            batch_size: Number of contacts to sync in each batch
            max_contacts: Maximum total contacts to sync (None for all)

        Returns:
            Dictionary with sync statistics
        """
        print("\n🔄 Starting contact sync to Follow Up Boss...")

        # Get contacts that haven't been synced yet
        contacts = self.db.get_contacts_to_sync(limit=max_contacts)

        if not contacts:
            print("✅ No contacts to sync - all up to date!")
            return self.sync_stats

        print(f"Found {len(contacts)} contacts to sync")

        for i, contact in enumerate(contacts, 1):
            try:
                print(f"[{i}/{len(contacts)}] Syncing {contact['full_name']} ({contact['email'] or contact['phone']})...")

                # Convert Mojo contact to FUB event format
                fub_event = self._convert_contact_to_fub_event(contact)

                # Create event in FUB (preferred method for new leads)
                response = self.fub._make_request(
                    'POST',
                    'events',
                    data=fub_event
                )

                # Extract person ID from response
                fub_person_id = self._extract_person_id(response)

                if fub_person_id:
                    # Mark as synced in our database
                    self.db.mark_contact_synced(contact['id'], fub_person_id)
                    self.sync_stats['contacts_synced'] += 1
                    print(f"  ✅ Synced successfully (FUB ID: {fub_person_id})")
                else:
                    raise Exception("No person ID returned from FUB")

                # Rate limiting - be nice to the API
                if i % batch_size == 0:
                    print(f"  ⏸️  Batch complete, pausing 2 seconds...")
                    time.sleep(2)
                else:
                    time.sleep(0.5)  # Small delay between requests

            except Exception as e:
                error_msg = f"Failed to sync {contact.get('full_name', 'Unknown')}: {str(e)}"
                print(f"  ❌ {error_msg}")
                self.sync_stats['contacts_failed'] += 1
                self.sync_stats['errors'].append(error_msg)
                continue

        print(f"\n✅ Contact sync complete:")
        print(f"  • Synced: {self.sync_stats['contacts_synced']}")
        print(f"  • Failed: {self.sync_stats['contacts_failed']}")

        return self.sync_stats

    def sync_call_logs(self, batch_size: int = 50, max_calls: Optional[int] = None) -> Dict[str, int]:
        """
        Sync call logs from Mojo to Follow Up Boss as call events

        Args:
            batch_size: Number of calls to sync in each batch
            max_calls: Maximum total calls to sync (None for all)

        Returns:
            Dictionary with sync statistics
        """
        print("\n📞 Starting call log sync to Follow Up Boss...")

        # Get calls that haven't been synced yet (only for contacts already in FUB)
        calls = self.db.get_call_logs_to_sync(limit=max_calls)

        if not calls:
            print("✅ No call logs to sync - all up to date!")
            return self.sync_stats

        print(f"Found {len(calls)} call logs to sync")

        for i, call in enumerate(calls, 1):
            try:
                contact_name = call.get('full_name', 'Unknown')
                call_date = call.get('call_date', 'Unknown date')

                print(f"[{i}/{len(calls)}] Syncing call: {contact_name} on {call_date}...")

                # Convert call to FUB call log event
                fub_event = self._convert_call_to_fub_event(call)

                # Create event in FUB
                response = self.fub._make_request(
                    'POST',
                    'events',
                    data=fub_event
                )

                # Mark as synced
                self.db.mark_call_synced(call['id'])
                self.sync_stats['calls_synced'] += 1
                print(f"  ✅ Call logged successfully")

                # Rate limiting
                if i % batch_size == 0:
                    print(f"  ⏸️  Batch complete, pausing 2 seconds...")
                    time.sleep(2)
                else:
                    time.sleep(0.5)

            except Exception as e:
                error_msg = f"Failed to sync call {call.get('id')}: {str(e)}"
                print(f"  ❌ {error_msg}")
                self.sync_stats['calls_failed'] += 1
                self.sync_stats['errors'].append(error_msg)
                continue

        print(f"\n✅ Call log sync complete:")
        print(f"  • Synced: {self.sync_stats['calls_synced']}")
        print(f"  • Failed: {self.sync_stats['calls_failed']}")

        return self.sync_stats

    def _convert_contact_to_fub_event(self, contact: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert Mojo contact to FUB event format

        Args:
            contact: Mojo contact dictionary

        Returns:
            FUB event payload
        """
        # Build person data
        person = {}

        # Name
        if contact.get('first_name'):
            person['firstName'] = contact['first_name']
        if contact.get('last_name'):
            person['lastName'] = contact['last_name']

        # Email
        emails = []
        if contact.get('email'):
            emails.append({'value': contact['email'], 'type': 'home'})
        if emails:
            person['emails'] = emails

        # Phones
        phones = []
        if contact.get('phone'):
            phones.append({'value': contact['phone'], 'type': 'home'})
        if contact.get('mobile_phone') and contact['mobile_phone'] != contact.get('phone'):
            phones.append({'value': contact['mobile_phone'], 'type': 'mobile'})
        if phones:
            person['phones'] = phones

        # Address
        if contact.get('address') or contact.get('city') or contact.get('state'):
            address = {}
            if contact.get('address'):
                address['street'] = contact['address']
            if contact.get('city'):
                address['city'] = contact['city']
            if contact.get('state'):
                address['state'] = contact['state']
            if contact.get('zip_code'):
                address['code'] = contact['zip_code']
            if address:
                person['addresses'] = [address]

        # Custom fields - add Mojo-specific data
        custom_fields = {}

        if contact.get('status'):
            custom_fields['Mojo Status'] = contact['status']

        if contact.get('lead_source'):
            person['source'] = contact['lead_source']
            custom_fields['Mojo Lead Source'] = contact['lead_source']

        if contact.get('list_name'):
            custom_fields['Mojo List'] = contact['list_name']

        # Add tags
        if contact.get('tags'):
            import json
            try:
                tags = json.loads(contact['tags']) if isinstance(contact['tags'], str) else contact['tags']
                if tags and isinstance(tags, list):
                    person['tags'] = tags
            except:
                pass

        # Store Mojo ID for reference
        custom_fields['Mojo Contact ID'] = contact.get('mojo_id', '')

        if custom_fields:
            person['customFields'] = custom_fields

        # Build event
        event = {
            'source': 'Mojo Dialer',
            'type': 'General Inquiry',  # This will trigger action plans
            'person': person,
            'message': f"Contact imported from Mojo Dialer (List: {contact.get('list_name', 'Unknown')})",
        }

        # Add timestamp if available
        if contact.get('created_date'):
            event['created'] = contact['created_date']

        return event

    def _convert_call_to_fub_event(self, call: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert Mojo call log to FUB call event format

        Args:
            call: Mojo call log dictionary (with joined contact data)

        Returns:
            FUB event payload
        """
        # Build person identifier (use existing FUB person ID)
        person = {
            'id': call['fub_person_id']
        }

        # Build call message
        message_parts = [
            f"Mojo Dialer Call - {call.get('call_result', 'Unknown Result')}",
            f"Duration: {call.get('call_duration', 0)} seconds",
        ]

        if call.get('agent_name'):
            message_parts.append(f"Agent: {call['agent_name']}")

        if call.get('disposition'):
            message_parts.append(f"Disposition: {call['disposition']}")

        if call.get('notes'):
            message_parts.append(f"Notes: {call['notes']}")

        if call.get('recording_url'):
            message_parts.append(f"Recording: {call['recording_url']}")

        message = "\n".join(message_parts)

        # Build event
        event = {
            'source': 'Mojo Dialer',
            'type': 'Call',
            'person': person,
            'message': message,
        }

        # Add call timestamp
        if call.get('call_date'):
            event['created'] = call['call_date']

        return event

    def _extract_person_id(self, fub_response: Dict[str, Any]) -> Optional[str]:
        """
        Extract person ID from FUB API response

        Args:
            fub_response: Response from FUB events endpoint

        Returns:
            Person ID or None
        """
        # FUB event response structure varies, try different paths
        if isinstance(fub_response, dict):
            # Try direct person ID
            if 'personId' in fub_response:
                return str(fub_response['personId'])

            # Try person object
            if 'person' in fub_response and isinstance(fub_response['person'], dict):
                if 'id' in fub_response['person']:
                    return str(fub_response['person']['id'])

            # Try event object
            if 'event' in fub_response and isinstance(fub_response['event'], dict):
                if 'personId' in fub_response['event']:
                    return str(fub_response['event']['personId'])

        return None

    def get_sync_report(self) -> str:
        """Generate a text report of sync results"""
        report = []
        report.append("\n" + "=" * 60)
        report.append("MOJO TO FOLLOW UP BOSS SYNC REPORT")
        report.append("=" * 60)

        report.append(f"\n📊 CONTACTS")
        report.append(f"  Synced: {self.sync_stats['contacts_synced']}")
        report.append(f"  Failed: {self.sync_stats['contacts_failed']}")

        report.append(f"\n📞 CALL LOGS")
        report.append(f"  Synced: {self.sync_stats['calls_synced']}")
        report.append(f"  Failed: {self.sync_stats['calls_failed']}")

        if self.sync_stats['errors']:
            report.append(f"\n❌ ERRORS ({len(self.sync_stats['errors'])})")
            for error in self.sync_stats['errors'][:10]:  # Show first 10 errors
                report.append(f"  • {error}")
            if len(self.sync_stats['errors']) > 10:
                report.append(f"  ... and {len(self.sync_stats['errors']) - 10} more")

        report.append("\n" + "=" * 60)

        return "\n".join(report)

    def dry_run_sync(self, max_contacts: int = 5) -> Dict[str, Any]:
        """
        Perform a dry run to show what would be synced without actually syncing

        Args:
            max_contacts: Number of sample contacts to show

        Returns:
            Dictionary with sample data
        """
        print("\n🔍 DRY RUN - Preview of data to be synced\n")

        # Get sample contacts
        contacts = self.db.get_contacts_to_sync(limit=max_contacts)

        print(f"📋 CONTACTS TO SYNC: {len(contacts)}")
        print("-" * 60)

        samples = []
        for i, contact in enumerate(contacts[:5], 1):
            print(f"\n{i}. {contact['full_name']}")
            print(f"   Email: {contact.get('email', 'N/A')}")
            print(f"   Phone: {contact.get('phone', 'N/A')}")
            print(f"   List: {contact.get('list_name', 'N/A')}")
            print(f"   Status: {contact.get('status', 'N/A')}")

            # Show what the FUB event would look like
            fub_event = self._convert_contact_to_fub_event(contact)
            samples.append({
                'mojo_contact': contact,
                'fub_event': fub_event
            })

        # Get sample calls
        calls = self.db.get_call_logs_to_sync(limit=max_contacts)

        print(f"\n\n📞 CALL LOGS TO SYNC: {len(calls)}")
        print("-" * 60)

        for i, call in enumerate(calls[:5], 1):
            print(f"\n{i}. {call.get('full_name', 'Unknown')}")
            print(f"   Date: {call.get('call_date', 'N/A')}")
            print(f"   Result: {call.get('call_result', 'N/A')}")
            print(f"   Duration: {call.get('call_duration', 0)} seconds")
            print(f"   Agent: {call.get('agent_name', 'N/A')}")

        return {
            'contacts_to_sync': len(contacts),
            'calls_to_sync': len(calls),
            'samples': samples
        }
