"""
Read survey responses from the Google Sheets master sheet.
"""

import os
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "../credentials/service_account.json")
SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME", "Survey Responses")


def _client() -> gspread.Client:
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    return gspread.authorize(creds)


def get_responses_df() -> pd.DataFrame:
    """Return the full Responses worksheet as a DataFrame."""
    try:
        client = _client()
        spreadsheet = client.open(SHEET_NAME)
        worksheet = spreadsheet.worksheet("Responses")
        records = worksheet.get_all_records()
        if not records:
            return pd.DataFrame()
        df = pd.DataFrame(records)
        if "Timestamp" in df.columns:
            df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
        return df
    except gspread.SpreadsheetNotFound:
        return pd.DataFrame()
    except gspread.WorksheetNotFound:
        return pd.DataFrame()
    except Exception as exc:
        raise RuntimeError(f"Could not read Google Sheet: {exc}") from exc
