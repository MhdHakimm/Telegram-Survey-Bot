# credentials/

Place your Google Service Account JSON key file here.

Rename it to `service_account.json` (or update `GOOGLE_CREDENTIALS_FILE` in your `.env`).

## How to get a Service Account key

1. Go to https://console.cloud.google.com/
2. Create a new project (or select an existing one).
3. Enable the **Google Sheets API** and **Google Drive API**.
4. Go to **IAM & Admin → Service Accounts** and create a new service account.
5. Create a JSON key for that service account and download it.
6. Rename it `service_account.json` and place it in this folder.
7. Share your Google Sheet with the service account email (found inside the JSON as `client_email`).

## Security

⚠️ **Never commit this file to version control.**
The `.gitignore` already excludes `credentials/*.json`.
