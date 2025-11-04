"""
Mojo Dialer Data Extractor
Handles importing data from Mojo Dialer CSV exports and (future) API integration
"""

import csv
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import hashlib


class MojoExtractor:
    """Extract and normalize data from Mojo Dialer exports"""

    # Common Mojo CSV field mappings (adjust based on your actual exports)
    CONTACT_FIELD_MAP = {
        'ID': 'mojo_id',
        'Contact ID': 'mojo_id',
        'First Name': 'first_name',
        'Last Name': 'last_name',
        'Full Name': 'full_name',
        'Email': 'email',
        'Email Address': 'email',
        'Phone': 'phone',
        'Phone Number': 'phone',
        'Mobile': 'mobile_phone',
        'Mobile Phone': 'mobile_phone',
        'Address': 'address',
        'Street Address': 'address',
        'City': 'city',
        'State': 'state',
        'Zip': 'zip_code',
        'ZIP': 'zip_code',
        'Zip Code': 'zip_code',
        'Status': 'status',
        'Lead Source': 'lead_source',
        'Source': 'lead_source',
        'List': 'list_name',
        'List Name': 'list_name',
        'Tags': 'tags',
        'Created': 'created_date',
        'Created Date': 'created_date',
        'Updated': 'updated_date',
        'Last Updated': 'updated_date',
        'Last Contact': 'last_contact_date',
        'Last Contact Date': 'last_contact_date',
    }

    CALL_LOG_FIELD_MAP = {
        'Call ID': 'mojo_call_id',
        'ID': 'mojo_call_id',
        'Contact ID': 'mojo_contact_id',
        'Phone': 'phone_number',
        'Phone Number': 'phone_number',
        'Call Date': 'call_date',
        'Date': 'call_date',
        'Time': 'call_date',
        'Duration': 'call_duration',
        'Call Duration': 'call_duration',
        'Result': 'call_result',
        'Call Result': 'call_result',
        'Disposition': 'disposition',
        'Type': 'call_type',
        'Call Type': 'call_type',
        'Agent': 'agent_name',
        'Agent Name': 'agent_name',
        'Rep': 'agent_name',
        'Notes': 'notes',
        'Recording URL': 'recording_url',
        'Recording': 'recording_url',
        'Has Recording': 'has_recording',
    }

    def __init__(self):
        """Initialize the extractor"""
        self.contacts_imported = 0
        self.contacts_updated = 0
        self.calls_imported = 0
        self.calls_updated = 0
        self.errors = []

    def import_contacts_csv(self, csv_path: str) -> List[Dict[str, Any]]:
        """
        Import contacts from a Mojo Dialer CSV export

        Args:
            csv_path: Path to the contacts CSV file

        Returns:
            List of normalized contact dictionaries
        """
        contacts = []
        csv_file = Path(csv_path)

        if not csv_file.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        print(f"Reading contacts from {csv_path}...")

        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)

            # Get the actual headers from the CSV
            headers = reader.fieldnames
            print(f"Found CSV headers: {headers}")

            for row_num, row in enumerate(reader, start=2):
                try:
                    contact = self._normalize_contact(row)

                    # Generate mojo_id from email/phone if not present
                    if not contact.get('mojo_id'):
                        contact['mojo_id'] = self._generate_id(contact)

                    contacts.append(contact)

                except Exception as e:
                    error_msg = f"Row {row_num}: {str(e)}"
                    self.errors.append(error_msg)
                    print(f"Error importing row {row_num}: {e}")
                    continue

        print(f"Successfully parsed {len(contacts)} contacts from CSV")
        return contacts

    def import_call_logs_csv(self, csv_path: str) -> List[Dict[str, Any]]:
        """
        Import call logs from a Mojo Dialer CSV export

        Args:
            csv_path: Path to the call logs CSV file

        Returns:
            List of normalized call log dictionaries
        """
        call_logs = []
        csv_file = Path(csv_path)

        if not csv_file.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        print(f"Reading call logs from {csv_path}...")

        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)

            headers = reader.fieldnames
            print(f"Found CSV headers: {headers}")

            for row_num, row in enumerate(reader, start=2):
                try:
                    call_log = self._normalize_call_log(row)

                    # Generate call_id if not present
                    if not call_log.get('mojo_call_id'):
                        call_log['mojo_call_id'] = self._generate_call_id(call_log)

                    call_logs.append(call_log)

                except Exception as e:
                    error_msg = f"Row {row_num}: {str(e)}"
                    self.errors.append(error_msg)
                    print(f"Error importing row {row_num}: {e}")
                    continue

        print(f"Successfully parsed {len(call_logs)} call logs from CSV")
        return call_logs

    def _normalize_contact(self, row: Dict[str, str]) -> Dict[str, Any]:
        """Normalize a contact row from CSV to our database schema"""
        contact = {}

        # Map known fields
        for csv_field, db_field in self.CONTACT_FIELD_MAP.items():
            if csv_field in row and row[csv_field]:
                value = row[csv_field].strip()

                # Handle date fields
                if 'date' in db_field and value:
                    value = self._parse_date(value)

                # Handle phone numbers
                elif 'phone' in db_field and value:
                    value = self._clean_phone(value)

                # Handle tags (comma-separated to list)
                elif db_field == 'tags' and value:
                    value = [tag.strip() for tag in value.split(',') if tag.strip()]

                contact[db_field] = value

        # Build full_name if not present
        if not contact.get('full_name') and (contact.get('first_name') or contact.get('last_name')):
            contact['full_name'] = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()

        # Store any unmapped fields as custom_fields
        custom_fields = {}
        for key, value in row.items():
            if key not in self.CONTACT_FIELD_MAP and value:
                custom_fields[key] = value

        if custom_fields:
            contact['custom_fields'] = custom_fields

        return contact

    def _normalize_call_log(self, row: Dict[str, str]) -> Dict[str, Any]:
        """Normalize a call log row from CSV to our database schema"""
        call_log = {}

        # Map known fields
        for csv_field, db_field in self.CALL_LOG_FIELD_MAP.items():
            if csv_field in row and row[csv_field]:
                value = row[csv_field].strip()

                # Handle date fields
                if 'date' in db_field and value:
                    value = self._parse_date(value)

                # Handle duration (convert to seconds)
                elif db_field == 'call_duration' and value:
                    value = self._parse_duration(value)

                # Handle phone numbers
                elif 'phone' in db_field and value:
                    value = self._clean_phone(value)

                # Handle boolean fields
                elif db_field == 'has_recording' and value:
                    value = value.lower() in ('yes', 'true', '1', 'y')

                call_log[db_field] = value

        # Check if recording URL exists
        if call_log.get('recording_url'):
            call_log['has_recording'] = True

        return call_log

    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse various date formats to ISO format"""
        if not date_str:
            return None

        # Try common date formats
        date_formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M',
            '%Y-%m-%d',
            '%m/%d/%Y %H:%M:%S',
            '%m/%d/%Y %H:%M',
            '%m/%d/%Y',
            '%m-%d-%Y %H:%M:%S',
            '%m-%d-%Y',
            '%Y/%m/%d %H:%M:%S',
            '%Y/%m/%d',
        ]

        for fmt in date_formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.isoformat()
            except ValueError:
                continue

        # If no format matched, return as-is
        return date_str

    def _parse_duration(self, duration_str: str) -> Optional[int]:
        """Parse duration string to seconds"""
        if not duration_str:
            return None

        duration_str = duration_str.strip().lower()

        try:
            # If it's already a number (seconds)
            if duration_str.isdigit():
                return int(duration_str)

            # Parse MM:SS format
            if ':' in duration_str:
                parts = duration_str.split(':')
                if len(parts) == 2:
                    minutes, seconds = int(parts[0]), int(parts[1])
                    return minutes * 60 + seconds
                elif len(parts) == 3:
                    hours, minutes, seconds = int(parts[0]), int(parts[1]), int(parts[2])
                    return hours * 3600 + minutes * 60 + seconds

            # Parse "X min Y sec" format
            if 'min' in duration_str or 'sec' in duration_str:
                total = 0
                if 'min' in duration_str:
                    minutes = int(duration_str.split('min')[0].strip())
                    total += minutes * 60
                if 'sec' in duration_str:
                    seconds = int(duration_str.split('sec')[0].split()[-1].strip())
                    total += seconds
                return total

        except (ValueError, IndexError):
            pass

        return None

    def _clean_phone(self, phone: str) -> str:
        """Clean and standardize phone number format"""
        if not phone:
            return ""

        # Remove common formatting characters
        cleaned = ''.join(c for c in phone if c.isdigit())

        # If it's a 10-digit US number, format it
        if len(cleaned) == 10:
            return f"({cleaned[:3]}) {cleaned[3:6]}-{cleaned[6:]}"
        elif len(cleaned) == 11 and cleaned[0] == '1':
            return f"+1 ({cleaned[1:4]}) {cleaned[4:7]}-{cleaned[7:]}"

        return cleaned

    def _generate_id(self, contact: Dict[str, Any]) -> str:
        """Generate a unique ID for a contact based on email/phone"""
        identifier = contact.get('email') or contact.get('phone') or contact.get('full_name', '')
        return hashlib.md5(identifier.encode()).hexdigest()

    def _generate_call_id(self, call: Dict[str, Any]) -> str:
        """Generate a unique ID for a call log"""
        # Combine phone, date, and agent to create unique ID
        parts = [
            call.get('phone_number', ''),
            call.get('call_date', ''),
            call.get('agent_name', ''),
        ]
        identifier = '_'.join(str(p) for p in parts if p)
        return hashlib.md5(identifier.encode()).hexdigest()

    def get_errors(self) -> List[str]:
        """Get list of import errors"""
        return self.errors


# Future: API-based extraction
class MojoAPIClient:
    """
    Future implementation: Direct API integration with Mojo Dialer

    This will replace CSV-based extraction once API credentials are available.
    Expected endpoints:
    - GET /contacts
    - GET /lists
    - GET /calls
    - GET /recordings
    """

    def __init__(self, api_key: str, api_url: str = "https://api.mojosells.com"):
        """Initialize the Mojo API client (placeholder)"""
        self.api_key = api_key
        self.api_url = api_url
        raise NotImplementedError(
            "Mojo Dialer API integration not yet implemented. "
            "Use CSV-based extraction for now. "
            "Contact Mojo support for API documentation."
        )

    def get_contacts(self) -> List[Dict]:
        """Fetch contacts from Mojo API (placeholder)"""
        raise NotImplementedError("API integration pending")

    def get_call_logs(self) -> List[Dict]:
        """Fetch call logs from Mojo API (placeholder)"""
        raise NotImplementedError("API integration pending")

    def download_recording(self, recording_url: str) -> bytes:
        """Download a call recording (placeholder)"""
        raise NotImplementedError("API integration pending")
