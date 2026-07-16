import os
import json
from datetime import datetime, timedelta, timezone
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
    
    try:
        lop_df = pd.DataFrame(spreadsheet.worksheet("LOP").get_all_records())
        lop_df['Agent Name'] = lop_df['Agent Name'].astype(str).str.strip().str.lower()
        if 'Date of LOP' in lop_df.columns:
            lop_df['Date of LOP'] = pd.to_datetime(lop_df['Date of LOP'], errors='coerce').dt.strftime('%Y-%m-%d')
    except:
        lop_df = pd.DataFrame(columns=['Agent Name', 'Date of LOP'])
    
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
    
    # 1. Grab all dates normally (NO MORE YESTERDAY SHIFT)
    morning_dates = set(morning_df['Date'].unique())
    evening_dates = set(evening_df['Date'].unique())
    all_dates_set = morning_dates.union(evening_dates)
    
    # 2. FORCE "TODAY" IN IST TIMEZONE
    ist_offset = timedelta(hours=5, minutes=30)
    ist_tz = timezone(ist_offset)
    today_str = datetime.now(ist_tz).strftime('%Y-%m-%d')
    all_dates_set.add(today_str)
    
    # Sort descending so Today is always at the very top [0]
    all_dates = sorted(list(all_dates_set), reverse=True)
    
    team_leads = ["aayush goyal", "rishab de", "ankur singh", "dhanendra kumar"]
    off_keywords = ["OFF", "WO", "WEEK OFF", "WEEKOFF"]
    
    dashboard_data = []
    
    for date_str in all_dates:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        day_name = date_obj.strftime('%a') 
        
        # Look for Morning and Evening on the EXACT same day
        day_morning = morning_df[morning_df['Date'] == date_str]
        day_evening = evening_df[evening_df['Date'] == date_str]
        
        morning_times = dict(zip(day_morning['Employee Official Mail id'], day_morning['Time']))
        evening_times = dict(zip(day_evening['Official Mail Id'], day_evening['Time']))
        
        for _, row in roster_df.iterrows():
            email = row['Official Email']
            if not email or email == 'nan':
                continue
            
            agent_name = str(row['Agent Name']).strip()
            agent_name_lower = agent_name.lower()
            
            designation = "Team Lead" if agent_name_lower in team_leads else "Executive"
                
            raw_status = str(row.get(day_name, '')).strip().upper()
            roster_status = 'OFF' if raw_status in off_keywords else 'DS'
            
            m_time = morning_times.get(email, None)
            e_time = evening_times.get(email, None)
            
            is_lop = False
            if not lop_df.empty and 'Date of LOP' in lop_df.columns:
                match = lop_df[(lop_df['Agent Name'] == agent_name_lower) & (lop_df['Date of LOP'] == date_str)]
                if not match.empty:
                    is_lop = True
                
            dashboard_data.append({
                "date": date_str,
                "agent_name": agent_name,
                "email": email,
                "designation": designation,
                "vertical": row['Vertical'],
                "morning_time": m_time if m_time else "-",
                "evening_time": e_time if e_time else "-",
                # Morning and Evening now share the exact same roster status
                "morning_roster": roster_status,
                "evening_roster": roster_status,
                "is_lop": is_lop 
            })
            
    os.makedirs('public', exist_ok=True)
    with open('public/dashboard.json', 'w') as f:
        json.dump(dashboard_data, f, indent=4)

if __name__ == "__main__":
    main()
