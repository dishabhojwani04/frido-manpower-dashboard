import os
import json
from datetime import datetime, timedelta
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

def main():
    # 1. Connect to Google Sheets
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds_dict = json.loads(os.environ["GCP_CREDENTIALS"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    gc = gspread.authorize(creds)
    
    sheet_id = os.environ["SHEET_ID"]
    spreadsheet = gc.open_by_key(sheet_id)
    
    # 2. Download Data
    roster_df = pd.DataFrame(spreadsheet.worksheet("Roster").get_all_records())
    morning_df = pd.DataFrame(spreadsheet.worksheet("Morning").get_all_records())
    evening_df = pd.DataFrame(spreadsheet.worksheet("Evening").get_all_records())
    
    # Clean emails
    roster_df['Official Email'] = roster_df['Official Email'].astype(str).str.strip().str.lower()
    morning_df['Employee Official Mail id'] = morning_df['Employee Official Mail id'].astype(str).str.strip().str.lower()
    evening_df['Official Mail Id'] = evening_df['Official Mail Id'].astype(str).str.strip().str.lower()
    
    # 3. Parse Dates and Exact Times
    morning_df['Timestamp'] = pd.to_datetime(morning_df['Timestamp'], errors='coerce')
    evening_df['Timestamp'] = pd.to_datetime(evening_df['Timestamp'], errors='coerce')
    
    morning_df = morning_df.dropna(subset=['Timestamp'])
    evening_df = evening_df.dropna(subset=['Timestamp'])
    
    morning_df['Date'] = morning_df['Timestamp'].dt.strftime('%Y-%m-%d')
    evening_df['Date'] = evening_df['Timestamp'].dt.strftime('%Y-%m-%d')
    morning_df['Time'] = morning_df['Timestamp'].dt.strftime('%I:%M %p') 
    evening_df['Time'] = evening_df['Timestamp'].dt.strftime('%I:%M %p')
    
    # 4. Find all unique dates from the MORNING sheet
    all_dates = sorted(list(morning_df['Date'].unique()), reverse=True)
    
    # 5. Build Historical Dashboard Data
    dashboard_data = []
    
    for date_str in all_dates:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        day_name = date_obj.strftime('%a') 
        
        # LOGIC: Evening data belongs to the DAY BEFORE
        prev_date_obj = date_obj - timedelta(days=1)
        prev_date_str = prev_date_obj.strftime('%Y-%m-%d')
        
        # Filter slack data for specific dates
        day_morning = morning_df[morning_df['Date'] == date_str]
        day_evening = evening_df[evening_df['Date'] == prev_date_str]
        
        morning_times = dict(zip(day_morning['Employee Official Mail id'], day_morning['Time']))
        evening_times = dict(zip(day_evening['Official Mail Id'], day_evening['Time']))
        
        for _, row in roster_df.iterrows():
            email = row['Official Email']
            if not email or email == 'nan':
                continue
                
            roster_status = row.get(day_name, 'DS') 
            
            m_time = morning_times.get(email, None)
            e_time = evening_times.get(email, None)
            
            if roster_status == 'OFF':
                final_status = 'Week Off'
            elif m_time and e_time:
                final_status = 'Completed Shift'
            elif m_time:
                final_status = 'Checked In'
            else:
                final_status = 'Absent'
                
            dashboard_data.append({
                "date": date_str,
                "agent_name": row['Agent Name'],
                "email": email,
                "vertical": row['Vertical'],
                "morning_time": m_time if m_time else "-",
                "evening_time": e_time if e_time else "-",
                "final_status": final_status
            })
            
    # 6. Save JSON file
    os.makedirs('public', exist_ok=True)
    with open('public/dashboard.json', 'w') as f:
        json.dump(dashboard_data, f, indent=4)

if __name__ == "__main__":
    main()
