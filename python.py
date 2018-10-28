import urllib.request
import urllib.parse
import re
import time
import datetime as dt
import time as tm
import pandas as pd


def nospace(x):
   output = ""

   for c in x:
       if c == " ":
           output+= "_"
       else:
           output+= c
   return output

print("Please enter your Summoner Name: ")
x = "aaksfeaaff ef adfafasdfadfaha"

# read and find user accountID
user_Input = input()
user_Input1 = nospace(user_Input)
req = urllib.request.Request('https://na1.api.riotgames.com/lol/summoner/v3/summoners/by-name/' + user_Input1 + '?api_key=RGAPI-8bc10804-37ab-47d2-8874-b48efd0fcd2c')
resp = urllib.request.urlopen(req)
respData = resp.read()

accountID = respData[respData.find(b"\"accountId\":")+12 : respData.find(b",\"name\":")  ]
accountIDstr =str(accountID.decode('utf-8'))

# read all matches the user has played
req1 = urllib.request.Request('https://na1.api.riotgames.com/lol/match/v3/matchlists/by-account/' + accountIDstr + '?api_key=RGAPI-8bc10804-37ab-47d2-8874-b48efd0fcd2c')
resp1 = urllib.request.urlopen(req1)
respData1 = resp1.read()
respData1str = str(respData1.decode('utf-8'))

gameIDS = []
x=0
while x < len(respData1str):
   if respData1str[x: x+ 9]== "\"gameId\":":
       gameID = respData1str[x + 9: respData1str.find(",\"champion\":",x)]
       gameIDS.append(gameID)


   x=x+1

# read the player stats for a particular game given the index of the game
def match_getter(i):
   req2 = urllib.request.Request('https://na1.api.riotgames.com//lol/match/v3/matches/' + gameIDS[i] + '?api_key=RGAPI-8bc10804-37ab-47d2-8874-b48efd0fcd2c')
   resp2 = urllib.request.urlopen(req2)
   respData2 = resp2.read()
   respData2str = str(respData2.decode('utf-8'))
   return(respData2str)

# get the index of a player in a match
def count(i):
   counter = 10
   match = match_getter(i)
   x = len(match) - len(user_Input)

   while (counter > 0):
       x=x-1
       if match[x: x + len("\"participantId\":")] == "\"participantId\":":
           counter = counter - 1
       else:
           if match[x:x+len(user_Input)] == user_Input:
               break

   return counter


# get the particular player info
def participant_getter(i, num):
	s = "\"participantId\":"+str(num)
	result = i.split(s)
	return i.split(s)[2]

def participant_info(i):
   return participant_getter(match_getter(i),count(i))


#win, kills, death, assists, totalminionskills
def search_key_table():
	index = ["win", "kills", "death", "assists", "totalMinionsKilled"]
	win = {"j": "\"win\":", "k": ",\"item0\":"}
	kills = {"j": "\"kills\":", "k": ",\"deaths\":"}
	death = {"j": "\"deaths\":", "k": ",\"assists\""}
	assists = {"j": "\"assists\":", "k": ",\"largestKillingSpree\":"}
	totalMinionsKilled = {"j": "\"totalMinionsKilled\":", "k": ",\"neutralMinionsKilled\""}
	dps = [pd.Series(win), pd.Series(kills), pd.Series(death), pd.Series(assists), pd.Series(totalMinionsKilled)]
	return pd.DataFrame(dps, index)


def the_getter(i, j, k):
   x = -1
   while x < len(i):
       x = x + 1
       if i[x: x + len(j)] == j:
           item_get = i[x + len(j): i.find(k, x)]
   return item_get

#print(the_getter(0,  "\"kills\":",",\"deaths\":"))


def match_dictionary_getter(matchID):
	index = ["win", "kills", "death", "assists", "totalMinionsKilled", "meanMinionsKilled"]
	match = dict.fromkeys(index, None)
	search_table = search_key_table()
	i = participant_info(matchID)

	index2 = ["win", "kills", "death", "assists", "totalMinionsKilled"]
	for key in index2:
		j = search_table.loc[key]["j"]
		k = search_table.loc[key]["k"]
		val = the_getter(i, j, k)
		match[key] = val
	total = float(match["totalMinionsKilled"])
	sec = float(match_duration_getter(matchID))
	minute = sec/60

	match["meanMinionsKilled"] = str(round(total/minute,2))
	return match

def match_duration_getter(matchID):
	i = match_getter(matchID)
	val = the_getter(i, "\"gameDuration\":", ",\"queueId\"")
	return val

def matches_getter():
	index = 1
	list_matches = []
	while (index <= 10):
		match = match_dictionary_getter(index)
		list_matches.append(pd.Series(match))
		index = index + 1
	return pd.DataFrame(list_matches)

def analysis_getter():
	matchesT = matches_getter()
	matches = matchesT.T
	#print(matches)
	index = ["win", "kills", "death", "assists", "totalMinionsKilled", "meanMinionsKilled"]
	anaMean = dict.fromkeys(index, None)
	anaStd = dict.fromkeys(index, None)

	var = ["kills", "death", "assists", "totalMinionsKilled", "meanMinionsKilled"]
	for key in var:
		colnum = pd.to_numeric(matches.loc[key]).astype(float)
		anaMean[key] = colnum.mean()
		anaStd[key] = colnum.std()

	return pd.DataFrame([pd.Series(anaMean), pd.Series(anaStd)], ["mean", "std"])

def scorer(match):
	analysis = analysis_getter()
	index = ["kills", "death", "assists"]
	score = 0

	for key in index:
		mean = analysis.loc["mean"][key]
		std = analysis.loc["std"][key]
		val = match[key]
		score = score + scorer_key(float(val), float(mean), float(std))

	mean = analysis.loc["mean"]["meanMinionsKilled"]
	std = analysis.loc["std"]["meanMinionsKilled"]
	val = match["meanMinionsKilled"]
	score = score + scorer_key_neg(float(val), float(mean), float(std))
	return score

def scorer_key(val, mean, std):
	score = 0

	if val > mean + 1.5*std:
		score = score + 3
	if ((val > mean + 1*std) & (val <= mean + 1.5*std)):
		score = score + 2
	if ((val > mean) & (val <= mean + 1*std)):
		score = score + 1 
	if ((val <= mean) & (val > mean - 1*std)):
		score = score -1
	if ((val > mean - 1.5*std) & (val <= mean - 1*std)):
		score = score - 2
	if (val <= mean - 1.5*std):
		score = score - 3

	return score

def scorer_key_neg(val, mean, std):
	score = 0

	if (val > mean + 1.5*std):
		score = score - 3
	if ((val > mean + 1*std) & (val <= mean + 1.5*std)):
		score = score - 2
	if ((val > mean) & (val <= mean + 1*std)):
		score = score - 1 
	if ((val <= mean) & (val > mean - 1*std)):
		score = score + 1
	if ((val > mean - 1.5*std) & (val <= mean - 1*std)):
		score = score + 2
	if (val <= mean - 1.5*std):
		score = score + 3

	return score

def currMatch_getter(matchID):
	match = match_dictionary_getter(matchID)
	return scorer(match)

score = currMatch_getter(0)
#match_dictionary_getter(1)
if (score <= -8):
	print("You are too tilted. Pls stop. ")
if (score > -8):
	print("You are not that tilted. You can continue playing. ")

def get_timestamp(x):
	timestamptmp = x.split(",\"role\":")[0]
	timestampStr = timestamptmp.split("\"timestamp\":")[-1]
	#timestampStr = timestampBytes.decode("utf-8")
	timestampEpoch = float(timestampStr)/1000
	dtnow = tm.localtime(timestampEpoch)
	dtnow2 = dt.datetime.fromtimestamp(timestampEpoch)
	return {'year': dtnow.tm_year, 'month': dtnow.tm_mon, 'day': dtnow.tm_mday, 'hour': dtnow.tm_hour, 'minute': dtnow.tm_min, 'second': dtnow.tm_sec}

def epoch_to_est(x):
	return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(x))

	







