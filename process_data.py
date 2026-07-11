import os
import json
from datetime import datetime
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

def main():
    # 1. Connect to Google Sheets
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds_dict = json.loads(os.environ["GCP_CREDENTIALS"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    gc = gspread.authorize(creds)
    
    # Open the Sheet
    sheet_id = os.environ["SHEET_ID"]
    spreadsheet = gc.open_by_key(sheet_id)
    
    # 2. Download Data
    roster_df = pd.DataFrame(spreadsheet.worksheet("Roster").get_all_records())
    morning_df = pd.DataFrame(spreadsheet.worksheet("Morning").get_all_records())
    evening_df = pd.DataFrame(spreadsheet.worksheet("Evening").get_all_records())
    
    # Standardize emails for matching
    roster_df['Official Email'] = roster_df['Official Email'].str.strip().str.lower()
    morning_df['Employee Official Mail id'] = morning_df['Employee Official Mail id'].str.strip().str.lower()
    evening_df['Official Mail Id'] = evening_df['Official Mail Id'].str.strip().str.lower()
    
    # 3. Setup Today's Date Context
    today = datetime.now()
    today_str = today.strftime('%Y-%m-%d')
    current_day_name = today.strftime('%a') 
    
    # 4. Filter for today's Slack check-ins
    morning_df['Date'] = pd.to_datetime(morning_df['Timestamp']).dt.strftime('%Y-%m-%d')
    evening_df['Date'] = pd.to_datetime(evening_df['Timestamp']).dt.strftime('%Y-%m-%d')
    
    today_morning = morning_df[morning_df['Date'] == today_str]
    today_evening = evening_df[evening_df['Date'] == today_str]
    
    checked_in_emails = set(today_morning['Employee Official Mail id'])
    checked_out_emails = set(today_evening['Official Mail Id'])
    
    # 5. Build Dashboard Data
    dashboard_data = []
    
    for _, row in roster_df.iterrows():
        email = row['Official Email']
        if not email:
            continue
            
        roster_status = row.get(current_day_name, 'DS') 
        is_checked_in = email in checked_in_emails
        is_checked_out = email in checked_out_emails
        
        if roster_status == 'OFF':
            final_status = 'Week Off'
        elif is_checked_in and is_checked_out:
            final_status = 'Completed Shift'
        elif is_checked_in:
            final_status = 'Checked In'
        else:
            final_status = 'Pending / Absent'
            
        dashboard_data.append({
            "agent_name": row['Agent Name'],
            "email": email,
            "vertical": row['Vertical'],
            "morning_status": "Checked In" if is_checked_in else "Pending",
            "evening_status": "Checked Out" if is_checked_out else "Pending",
            "final_status": final_status
        })
        
    # 6. Save JSON file
    os.makedirs('public', exist_ok=True)
    with open('public/dashboard.json', 'w') as f:
        json.dump(dashboard_data, f, indent=4)
        
    print(f"Success! Dashboard updated for {today_str}")

if __name__ == "__main__":
    main()
