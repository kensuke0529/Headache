"""
Python script to fetch headache tracking data from Google Sheets.

This script uses the Google Sheets API and Google Drive API to:
1. Authenticate with service account credentials
2. Find the headache tracking spreadsheet in the specified Drive folder
3. Fetch and return headache data from the spreadsheet
"""

import os
import json
import tempfile
from typing import List, Dict, Optional

from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Load environment variables
load_dotenv()

# Configuration
SERVICE_ACCOUNT_JSON = os.getenv("SERVICE_ACCOUNT_JSON")  # For deployment
SERVICE_ACCOUNT_PATH = os.getenv("SERVICE_ACCOUNT_PATH")
DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID")

# Google API scopes
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]


class HeadacheDataFetcher:
    """Class to handle fetching headache data from Google Sheets."""

    def __init__(self, service_account_path: str, drive_folder_id: str):
        """
        Initialize the fetcher with service account and folder ID.

        Args:
            service_account_path: Path to the service account JSON file
            drive_folder_id: Google Drive folder ID containing the spreadsheet
        """
        self.service_account_path = service_account_path
        self.drive_folder_id = drive_folder_id
        self.credentials = None
        self.sheets_service = None
        self.drive_service = None

    def authenticate(self):
        """Authenticate with Google APIs using service account credentials."""
        try:
            # Check if SERVICE_ACCOUNT_JSON environment variable is set (for deployment)
            if SERVICE_ACCOUNT_JSON:
                # Parse JSON from environment variable
                try:
                    service_account_info = json.loads(SERVICE_ACCOUNT_JSON)
                    self.credentials = (
                        service_account.Credentials.from_service_account_info(
                            service_account_info, scopes=SCOPES
                        )
                    )
                except json.JSONDecodeError:
                    print("❌ Invalid SERVICE_ACCOUNT_JSON format")
                    return False
            else:
                # Load from file path (for local development)
                self.credentials = (
                    service_account.Credentials.from_service_account_file(
                        self.service_account_path, scopes=SCOPES
                    )
                )

            # Build API services
            self.sheets_service = build("sheets", "v4", credentials=self.credentials)
            self.drive_service = build("drive", "v3", credentials=self.credentials)

            print("✅ Successfully authenticated with Google APIs")
            return True

        except FileNotFoundError:
            print(f"❌ Service account file not found: {self.service_account_path}")
            return False
        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            return False

    def find_spreadsheet(self) -> Optional[str]:
        """
        Find the headache tracking spreadsheet in the Drive folder.

        Returns:
            Spreadsheet ID if found, None otherwise
        """
        try:
            # List files in the folder
            query = f"'{self.drive_folder_id}' in parents and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false"

            results = (
                self.drive_service.files()
                .list(q=query, fields="files(id, name)")
                .execute()
            )

            files = results.get("files", [])

            if not files:
                print(f"❌ No spreadsheets found in folder {self.drive_folder_id}")
                return None

            # If multiple spreadsheets, return the first one (or most recent)
            # You can modify this logic to select a specific spreadsheet by name
            spreadsheet = files[0]
            print(
                f"✅ Found spreadsheet: {spreadsheet['name']} (ID: {spreadsheet['id']})"
            )

            return spreadsheet["id"]

        except HttpError as e:
            print(f"❌ Error finding spreadsheet: {e}")
            return None
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return None

    def get_sheet_names(self, spreadsheet_id: str) -> Optional[List[str]]:
        """
        Get the list of sheet names from the spreadsheet.

        Args:
            spreadsheet_id: The ID of the spreadsheet

        Returns:
            List of sheet names, or None if error
        """
        try:
            spreadsheet = (
                self.sheets_service.spreadsheets()
                .get(spreadsheetId=spreadsheet_id)
                .execute()
            )

            sheets = spreadsheet.get("sheets", [])
            sheet_names = [sheet["properties"]["title"] for sheet in sheets]

            if sheet_names:
                print(f"✅ Found sheets: {', '.join(sheet_names)}")
            return sheet_names

        except HttpError as e:
            print(f"❌ Error getting sheet names: {e}")
            return None
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return None

    def fetch_data(
        self, spreadsheet_id: str, range_name: str = "Sheet1"
    ) -> Optional[List[List[str]]]:
        """
        Fetch data from the specified spreadsheet range.

        Args:
            spreadsheet_id: The ID of the spreadsheet
            range_name: The range to fetch (e.g., "Sheet1" or "Sheet1!A1:Z100")

        Returns:
            List of rows (each row is a list of cell values), or None if error
        """
        try:
            # Fetch the data
            result = (
                self.sheets_service.spreadsheets()
                .values()
                .get(spreadsheetId=spreadsheet_id, range=range_name)
                .execute()
            )

            values = result.get("values", [])

            if not values:
                print("⚠️  No data found in spreadsheet")
                return []

            print(f"✅ Fetched {len(values)} rows from spreadsheet")
            return values

        except HttpError as e:
            print(f"❌ Error fetching data: {e}")
            return None
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return None

    def parse_headache_data(self, raw_data: List[List[str]]) -> List[Dict]:
        """
        Parse raw spreadsheet data into structured headache records.

        Assumes first row contains headers. Adjust this function based on your
        actual spreadsheet structure.

        Args:
            raw_data: Raw data from spreadsheet (list of rows)

        Returns:
            List of dictionaries, each representing a headache entry
        """
        if not raw_data:
            return []

        # First row is headers
        headers = raw_data[0] if raw_data else []

        # Parse data rows
        records = []
        for i, row in enumerate(raw_data[1:], start=2):  # Start at row 2 (skip header)
            if not row:  # Skip empty rows
                continue

            # Create a dictionary for this row
            record = {}
            for j, header in enumerate(headers):
                value = row[j] if j < len(row) else ""
                record[header] = value

            # Add row number for reference
            record["_row_number"] = i
            records.append(record)

        return records

    def get_headache_data(self, range_name: str = "Sheet1") -> Optional[List[Dict]]:
        """
        Main method to fetch and parse headache data.

        Args:
            range_name: The spreadsheet range to fetch

        Returns:
            List of parsed headache records, or None if error
        """
        # Authenticate
        if not self.authenticate():
            return None

        # Find spreadsheet
        spreadsheet_id = self.find_spreadsheet()
        if not spreadsheet_id:
            return None

        # Get sheet names and use the first one if range_name is default
        if range_name == "Sheet1":
            sheet_names = self.get_sheet_names(spreadsheet_id)
            if sheet_names:
                range_name = sheet_names[0]
                print(f"📄 Using sheet: {range_name}")

        # Fetch raw data
        raw_data = self.fetch_data(spreadsheet_id, range_name)
        if raw_data is None:
            return None

        # Parse data
        parsed_data = self.parse_headache_data(raw_data)

        return parsed_data


def main():
    """Main function to demonstrate usage."""
    print("🚀 Starting Headache Data Fetcher...\n")

    # Initialize fetcher
    fetcher = HeadacheDataFetcher(
        service_account_path=SERVICE_ACCOUNT_PATH, drive_folder_id=DRIVE_FOLDER_ID
    )

    # Fetch data (adjust range_name if your sheet has a different name)
    headache_data = fetcher.get_headache_data(range_name="Sheet1")

    if headache_data:
        print(f"\n📊 Found {len(headache_data)} headache records:\n")

        # Display first few records as example
        for i, record in enumerate(headache_data[:5], 1):
            print(f"Record {i}:")
            for key, value in record.items():
                if not key.startswith("_"):
                    print(f"  {key}: {value}")
            print()

        if len(headache_data) > 5:
            print(f"... and {len(headache_data) - 5} more records\n")

        return headache_data
    else:
        print("\n❌ Failed to fetch headache data")
        return None


if __name__ == "__main__":
    main()
