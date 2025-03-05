import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from io import StringIO

years = list(range(2024, 2020, -1))
all_matches = []
standings_url = "https://fbref.com/en/comps/9/Premier-League-Stats"
for year in years:
    data = requests.get(standings_url)
    time.sleep(6.5)
    soup = BeautifulSoup(data.text, features="lxml")
    standings_table = soup.select('table.stats_table')[0]
    
    links = [l.get('href') for l in standings_table.find_all('a')]
    links = [l for l in links if '/squads/' in l]
    team_urls = [f"https://fbref.com{l}" for l in links]
    
    previous_season = soup.select('a.prev')[0].get('href')
    standings_url = f"https://fbref.com/{previous_season}"
    
    for team_url in team_urls:
        team_name = team_url.split("/")[-1].replace("-Stats", "").replace("-", " ")
        print(team_name, year)
        
        try:
            data = requests.get(team_url)
            time.sleep(6.5)
            matches = pd.read_html(StringIO(data.text), match="Scores & Fixtures")[0]
            
            soup = BeautifulSoup(data.text, features="lxml")
            links = soup.find_all('a')
            links = [l.get("href") for l in links]
            shooting_links = [l for l in links if l and 'all_comps/shooting/' in l]
            passing_links = [l for l in links if l and 'all_comps/passing/' in l]
            poss_links = [l for l in links if l and 'all_comps/possession/' in l]
        
            data = requests.get(f"https://fbref.com{shooting_links[0]}")
            shooting = pd.read_html(StringIO(data.text), match="Shooting")[0]
            shooting.columns = shooting.columns.droplevel()        
            team_data = matches.merge(shooting[["Date", "Sh", "SoT", "Dist", "FK", "PK", "PKatt"]], on="Date")
            time.sleep(6.5)
            
            data = requests.get(f"https://fbref.com{passing_links[0]}")
            passing = pd.read_html(StringIO(data.text), match="Passing")[0]
            passing.columns = passing.columns.droplevel()
            cols = pd.Series(passing.columns)
            passing.columns = cols.where(~cols.duplicated(), cols + '_' + cols.groupby(cols).cumcount().astype('str'))
            team_data = team_data.merge(passing[["Date", "Cmp%", "TotDist", "PrgDist", "1/3", "PPA", "PrgP"]], on="Date")
            time.sleep(6.5)
            
            data = requests.get(f"https://fbref.com{poss_links[0]}")
            possession = pd.read_html(StringIO(data.text), match="Possession")[0]
            possession.columns = possession.columns.droplevel()
            team_data = team_data.merge(possession[["Date", "Poss", "Touches", "Att 3rd", "Att Pen", "Succ%"]], on="Date")
            time.sleep(6.5)
            
        except ValueError:
            continue
        
        team_data = team_data[team_data["Comp"] == "Premier League"]
        team_data["Season"] = year
        team_data["Team"] = team_name
        all_matches.append(team_data)

match_df = pd.concat(all_matches)
match_df.columns = [c.lower() for c in match_df.columns]
match_df.to_csv("matches.csv")