import os
import json
from datetime import datetime, timedelta
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

def main():
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds_dict = json.loads(os.environ["GCP_CREDENTIALS"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    gc = gspread.authorize(creds)
    
    sheet_id = os.environ["SHEET_ID"]
    spreadsheet = gc.open_by_key(sheet_id)
    
    roster_df = pd.DataFrame(spreadsheet.worksheet("Roster").get_all_records())
    morning_df = pd.DataFrame(spreadsheet.worksheet("Morning").get_all_records())
    evening_df = pd.DataFrame(spreadsheet.worksheet("Evening").get_all_records())
    
    roster_df['Official Email'] = roster_df['Official Email'].astype(str).str.strip().str.lower()
    morning_df['Employee Official Mail id'] = morning_df['Employee Official Mail id'].astype(str).str.strip().str.lower()
    evening_df['Official Mail Id'] = evening_df['Official Mail Id'].astype(str).str.strip().str.lower()
    
    morning_df['Timestamp'] = pd.to_datetime(morning_df['Timestamp'], errors='coerce')
    evening_df['Timestamp'] = pd.to_datetime(evening_df['Timestamp'], errors='coerce')
    
    morning_df = morning_df.dropna(subset=['Timestamp'])
    evening_df = evening_df.dropna(subset=['Timestamp'])
    
    morning_df['Date'] = morning_df['Timestamp'].dt.strftime('%Y-%m-%d')
    evening_df['Date'] = evening_df['Timestamp'].dt.strftime('%Y-%m-%d')
    
    morning_df['Time'] = morning_df['Timestamp'].dt.strftime('%I:%M %p') 
    evening_df['Time'] = evening_df['Timestamp'].dt.strftime('%I:%M %p')
    
    morning_dates = set(morning_df['Date'].unique())
    
    evening_dates_shifted = set()
    for ed in evening_df['Date'].unique():
        ed_obj = datetime.strptime(ed, '%Y-%m-%d')
        shifted_obj = ed_obj + timedelta(days=1)
        evening_dates_shifted.add(shifted_obj.strftime('%Y-%m-%d'))
        
    all_dates = sorted(list(morning_dates.union(evening_dates_shifted)), reverse=True)
    
    # *** DESIGNATION LIST ***
    team_leads = ["aayush goyal", "rishab de", "ankur singh", "dhanendra kumar"]
    
    dashboard_data = []
    
    for date_str in all_dates:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        day_name = date_obj.strftime('%a') 
        
        prev_date_obj = date_obj - timedelta(days=1)
        prev_date_str = prev_date_obj.strftime('%Y-%m-%d')
        prev_day_name = prev_date_obj.strftime('%a') 
        
        day_morning = morning_df[morning_df['Date'] == date_str]
        day_evening = evening_df[evening_df['Date'] == prev_date_str]
        
        morning_times = dict(zip(day_morning['Employee Official Mail id'], day_morning['Time']))
        evening_times = dict(zip(day_evening['Official Mail Id'], day_evening['Time']))
        
        for _, row in roster_df.iterrows():
            email = row['Official Email']
            if not email or email == 'nan':
                continue
            
            # *** ASSIGN DESIGNATION ***
            agent_name = str(row['Agent Name']).strip()
            if agent_name.lower() in team_leads:
                designation = "Team Lead"
            else:
                designation = "Executive"
                
            roster_status_morning = row.get(day_name, 'DS')
            roster_status_evening = row.get(prev_day_name, 'DS')
            
            m_time = morning_times.get(email, None)
            e_time = evening_times.get(email, None)
                
            dashboard_data.append({
                "date": date_str,
                "agent_name": agent_name,
                "email": email,
                "designation": designation,
                "vertical": row['Vertical'],
                "morning_time": m_time if m_time else "-",
                "evening_time": e_time if e_time else "-",
                "morning_roster": roster_status_morning,
                "evening_roster": roster_status_evening
            })
            
    os.makedirs('public', exist_ok=True)
    with open('public/dashboard.json', 'w') as f:
        json.dump(dashboard_data, f, indent=4)

if __name__ == "__main__":
    main()
