# Save this file as scrape_sldc.py
import requests
import csv
import time
from bs4 import BeautifulSoup
from datetime import date, timedelta

# --- Configuration ---
# Scrape from Jan 1, 2021, to Dec 31, 2024
start_date = date(2021, 1, 1)
end_date = date(2024, 12, 31)

url = 'http://www.delhisldc.org/Loaddata.aspx?mode='
output_csv = 'SLDC_Data_2021_2024.csv'
header = ['date', 'time', 'Delhi', 'BPRL', 'BYPL', 'NDPL', 'NDMC', 'MES']

# --- Scraping Logic ---

print(f"Starting scraper. Data will be saved to {output_csv}")
print("This will take a very long time. Please be patient.")

try:
    # Open the CSV file in 'append' (a) mode to resume if it's interrupted
    with open(output_csv, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Check if the file is new. If it is, write the header.
        f.seek(0, 2) # Go to the end of the file
        if f.tell() == 0: # Check if the file size is 0
            writer.writerow(header)
            print("New file created, writing header.")
        else:
            print("Resuming script. Will append to existing file.")

        current_date = start_date
        delta = timedelta(days=1)
        
        # Loop through each day in the date range
        while current_date <= end_date:
            date_str = current_date.strftime('%d/%m/%Y')
            print(f'Attempting to scrape: {date_str}')
            
            try:
                # Make the request with a 15-second timeout
                resp = requests.get(url + date_str, timeout=15)
                # Check for bad responses (4xx, 5xx)
                resp.raise_for_status() 
                
                soup = BeautifulSoup(resp.text, 'lxml')
                # Find the data table
                table = soup.find('table', {'id': 'ContentPlaceHolder3_DGGridAv'})
                
                if table is None:
                    print(f"No data table found for {date_str}. Skipping.")
                    current_date += delta
                    continue
                    
                trs = table.findAll('tr')
                
                # Write all rows for the current date
                for tr in trs[1:]:
                    fonts = tr.findChildren('font')[:7]
                    
                    if len(fonts) == 7:
                        time_val, delhi, bprl, bypl, ndpl, ndmc, mes = [font.text.strip() for font in fonts]
                        writer.writerow([date_str, time_val, delhi, bprl, bypl, ndpl, ndmc, mes])
                
                # Be polite to the server
                time.sleep(0.1) 

            except requests.exceptions.Timeout:
                print(f"!! Timeout occurred for {date_str}. Skipping.")
            
            except requests.exceptions.RequestException as e:
                print(f"!! Error scraping {date_str}: {e}. Skipping.")
            
            except Exception as e:
                print(f"!! An unexpected error occurred for {date_str}: {e}. Skipping.")

            # IMPORTANT: Always move to the next day, even if the scrape failed
            current_date += delta

    print("-" * 30)
    print("Scraping complete.")
    print(f"All data saved to {output_csv}")

except KeyboardInterrupt:
    print("\nScript interrupted by user. Rerun the script to resume.")
except Exception as e:
    print(f"A critical error occurred: {e}")