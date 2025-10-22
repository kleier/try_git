"""
FollowUpBoss API Client
Handles authentication and API requests to FollowUpBoss
"""

import requests
from typing import Dict, List, Optional
import time


class FollowUpBossClient:
    """Client for interacting with FollowUpBoss API"""

    BASE_URL = "https://api.followupboss.com/v1"

    def __init__(self, api_key: str):
        """
        Initialize the FollowUpBoss client

        Args:
            api_key: FollowUpBoss API key (obtained from Admin -> API screen)
        """
        self.api_key = api_key
        self.session = requests.Session()
        # API uses Basic Auth with API key as username and empty password
        self.session.auth = (api_key, '')
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        max_retries: int = 3
    ) -> Dict:
        """
        Make an API request with retry logic

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (without base URL)
            params: Query parameters
            data: Request body data
            max_retries: Maximum number of retry attempts

        Returns:
            Response data as dictionary
        """
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"

        for attempt in range(max_retries):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=data
                )

                # Check for rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    print(f"Rate limited. Waiting {retry_after} seconds...")
                    time.sleep(retry_after)
                    continue

                # Raise exception for error status codes
                response.raise_for_status()

                return response.json()

            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    raise Exception(f"API request failed after {max_retries} attempts: {str(e)}")

                wait_time = 2 ** attempt  # Exponential backoff
                print(f"Request failed (attempt {attempt + 1}/{max_retries}). Retrying in {wait_time}s...")
                time.sleep(wait_time)

        raise Exception("Unexpected error in API request")

    def get_people(
        self,
        limit: Optional[int] = None,
        offset: int = 0,
        fields: str = 'allFields',
        **filters
    ) -> List[Dict]:
        """
        Get people (contacts/leads) from FollowUpBoss

        Args:
            limit: Maximum number of results to return
            offset: Pagination offset
            fields: Fields to return (default: allFields for custom fields)
            **filters: Additional filter parameters

        Returns:
            List of people records
        """
        params = {
            'offset': offset,
            'fields': fields,
            **filters
        }

        if limit:
            params['limit'] = limit

        response = self._make_request('GET', 'people', params=params)
        return response.get('people', [])

    def get_all_people(self, max_records: Optional[int] = None) -> List[Dict]:
        """
        Get all people using pagination

        Args:
            max_records: Maximum total records to fetch

        Returns:
            List of all people records
        """
        all_people = []
        offset = 0
        limit = 100  # API default page size

        while True:
            people = self.get_people(limit=limit, offset=offset)

            if not people:
                break

            all_people.extend(people)

            if max_records and len(all_people) >= max_records:
                all_people = all_people[:max_records]
                break

            if len(people) < limit:
                break

            offset += limit
            print(f"Fetched {len(all_people)} people so far...")

        return all_people

    def get_events(
        self,
        limit: Optional[int] = None,
        offset: int = 0,
        **filters
    ) -> List[Dict]:
        """
        Get events (activities, interactions) from FollowUpBoss

        Args:
            limit: Maximum number of results to return
            offset: Pagination offset
            **filters: Additional filter parameters (e.g., personId, type, created)

        Returns:
            List of event records
        """
        params = {
            'offset': offset,
            **filters
        }

        if limit:
            params['limit'] = limit

        response = self._make_request('GET', 'events', params=params)
        return response.get('events', [])

    def get_all_events(self, max_records: Optional[int] = None) -> List[Dict]:
        """
        Get all events using pagination

        Args:
            max_records: Maximum total records to fetch

        Returns:
            List of all event records
        """
        all_events = []
        offset = 0
        limit = 100

        while True:
            events = self.get_events(limit=limit, offset=offset)

            if not events:
                break

            all_events.extend(events)

            if max_records and len(all_events) >= max_records:
                all_events = all_events[:max_records]
                break

            if len(events) < limit:
                break

            offset += limit
            print(f"Fetched {len(all_events)} events so far...")

        return all_events

    def get_text_messages(
        self,
        person_id: Optional[str] = None,
        phone_number: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Dict]:
        """
        Get text messages from FollowUpBoss

        Args:
            person_id: Filter by person ID
            phone_number: Filter by phone number
            limit: Maximum number of results to return
            offset: Pagination offset

        Returns:
            List of text message records
        """
        params = {'offset': offset}

        if person_id:
            params['personId'] = person_id
        if phone_number:
            params['phoneNumber'] = phone_number
        if limit:
            params['limit'] = limit

        response = self._make_request('GET', 'textMessages', params=params)
        return response.get('textMessages', [])

    def get_all_text_messages(self, max_records: Optional[int] = None) -> List[Dict]:
        """
        Get all text messages using pagination

        Args:
            max_records: Maximum total records to fetch

        Returns:
            List of all text message records
        """
        all_messages = []
        offset = 0
        limit = 100

        while True:
            messages = self.get_text_messages(limit=limit, offset=offset)

            if not messages:
                break

            all_messages.extend(messages)

            if max_records and len(all_messages) >= max_records:
                all_messages = all_messages[:max_records]
                break

            if len(messages) < limit:
                break

            offset += limit
            print(f"Fetched {len(all_messages)} text messages so far...")

        return all_messages
