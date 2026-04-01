import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import GOOGLE_CREDENTIALS_FILE, GOOGLE_SHEET_NAME

import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

MASTER_HEADERS = [
    "Timestamp",
    "Survey ID",
    "Survey Title",
    "User ID",
    "Username",
    "First Name",
    "Question #",
    "Question Text",
    "Question Type",
    "Answer",
]


def _get_client() -> gspread.Client:
    creds = Credentials.from_service_account_file(GOOGLE_CREDENTIALS_FILE, scopes=SCOPES)
    return gspread.authorize(creds)


def _get_or_create_worksheet() -> gspread.Worksheet:
    client = _get_client()
    try:
        spreadsheet = client.open(GOOGLE_SHEET_NAME)
    except gspread.SpreadsheetNotFound:
        spreadsheet = client.create(GOOGLE_SHEET_NAME)

    try:
        worksheet = spreadsheet.worksheet("Responses")
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title="Responses", rows=5000, cols=20)
        worksheet.append_row(MASTER_HEADERS, value_input_option="RAW")

    return worksheet


def save_responses(
    survey_id: int,
    survey_title: str,
    user_id: int,
    username: str,
    first_name: str,
    responses: list[dict],
) -> bool:
    """
    Save all responses for one completed survey submission to the master sheet.

    Each item in `responses` must have:
        question_num  : int
        question_text : str
        question_type : str
        answer        : str
    """
    worksheet = _get_or_create_worksheet()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    rows = [
        [
            timestamp,
            survey_id,
            survey_title,
            user_id,
            username or "",
            first_name or "",
            r["question_num"],
            r["question_text"],
            r["question_type"],
            r["answer"],
        ]
        for r in responses
    ]

    if rows:
        worksheet.append_rows(rows, value_input_option="RAW")

    return True
