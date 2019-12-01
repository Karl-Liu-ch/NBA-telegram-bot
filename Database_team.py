import requests
import json
import sqlite3
conn = sqlite3.connect('teams.db')
c = conn.cursor()
c.execute("DROP TABLE teams")
c.execute("CREATE TABLE IF NOT EXISTS teams(fullname text, nickname text, location text, shortname text, teamid text)")
for id in range(1,5):
    value = '{}'.format(id)
    url = "https://api-nba-v1.p.rapidapi.com/teams/teamId/"+value
    headers = {
        'x-rapidapi-host': "api-nba-v1.p.rapidapi.com",
        'x-rapidapi-key': "bb1964a290mshf67b124cec9c396p1b74ddjsnd9930eb00087"
    }
    response = requests.request("GET", url, headers=headers)
    Dict = json.loads(response.text)['api']['teams'][0]
    string = "INSERT INTO teams(fullname, nickname, location, shortname, teamid) VALUES('{}', '{}', '{}', '{}', '{}')".format(Dict['fullName'], Dict['nickname'], Dict['city'], Dict['shortName'], Dict['teamId'])
    c.execute(string)
    print(Dict['fullName'], Dict['nickname'], Dict['city'], Dict['shortName'], Dict['teamId'])
c.execute("commit")

c.execute("SELECT * FROM teams WHERE shortname = 'Thunder'")
fullname = [r[0] for r in c.fetchall()]
print("{}".format(*fullname))