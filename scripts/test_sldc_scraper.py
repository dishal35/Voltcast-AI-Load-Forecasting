"""
Test SLDC scraper to debug why it's failing.
"""
import requests
from bs4 import BeautifulSoup
from datetime import date
import pandas as pd

def test_scrape(target_date):
    """Test scraping for a specific date."""
    url = 'http://www.delhisldc.org/Loaddata.aspx?mode='
    date_str = target_date.strftime('%d/%m/%Y')
    
    print(f"\nTesting scrape for: {date_str}")
    print(f"URL: {url}{date_str}")
    print("="*60)
    
    try:
        print("Fetching page...")
        resp = requests.get(url + date_str, timeout=15)
        print(f"Status code: {resp.status_code}")
        
        if resp.status_code != 200:
            print(f"ERROR: Got status code {resp.status_code}")
            return
        
        print(f"Response length: {len(resp.text)} bytes")
        
        soup = BeautifulSoup(resp.text, 'lxml')
        
        # Try to find the table
        table = soup.find('table', {'id': 'ContentPlaceHolder3_DGGridAv'})
        
        if not table:
            print("ERROR: Table not found with ID 'ContentPlaceHolder3_DGGridAv'")
            print("\nSearching for any tables...")
            all_tables = soup.find_all('table')
            print(f"Found {len(all_tables)} tables total")
            
            if all_tables:
                print("\nTable IDs found:")
                for i, t in enumerate(all_tables):
                    table_id = t.get('id', 'No ID')
                    print(f"  {i+1}. {table_id}")
            
            # Save HTML for inspection
            with open('sldc_debug.html', 'w', encoding='utf-8') as f:
                f.write(resp.text)
            print("\nSaved response to sldc_debug.html for inspection")
            return
        
        print(f"✓ Table found!")
        
        # Parse table
        all_data = []
        trs = table.find_all('tr')
        print(f"Found {len(trs)} rows")
        
        for i, tr in enumerate(trs[1:10]):  # First 10 rows
            fonts = tr.find_all('font')[:7]
            
            if len(fonts) >= 2:
                time_val = fonts[0].text.strip()
                delhi = fonts[1].text.strip()
                
                print(f"Row {i+1}: Time={time_val}, Load={delhi}")
                
                timestamp_str = f"{date_str} {time_val}"
                
                try:
                    ts = pd.to_datetime(timestamp_str, format='%d/%m/%Y %H:%M')
                    load = float(delhi) if delhi else None
                    all_data.append({'timestamp': ts, 'load': load})
                except Exception as e:
                    print(f"  ERROR parsing: {e}")
        
        if all_data:
            df = pd.DataFrame(all_data)
            print(f"\n✓ Successfully parsed {len(df)} records")
            print(f"First record: {df.iloc[0]['timestamp']} - {df.iloc[0]['load']} MW")
            print(f"Last record: {df.iloc[-1]['timestamp']} - {df.iloc[-1]['load']} MW")
        else:
            print("\nERROR: No data parsed")
    
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Test for Nov 18, 2025
    test_date = date(2025, 11, 18)
    test_scrape(test_date)
