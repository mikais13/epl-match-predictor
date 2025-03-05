import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import precision_score

matches = pd.read_csv("matches.csv", index_col=0)

matches["date"] = pd.to_datetime(matches["date"])
matches["venue_code"] = matches["venue"].astype("category").cat.codes
matches["opp_code"] = matches["opponent"].astype("category").cat.codes
matches["hour"] = matches["time"].str.replace(":.+", "", regex=True).astype("int")
matches["day_code"] = matches["date"].dt.day_of_week
matches["formation_code"] = matches["formation"].astype("category").cat.codes
matches["opp_formation_code"] = matches["opp formation"].astype("category").cat.codes
matches["target"] = (matches["result"] == "W").astype("int")

grouped_matches = matches.groupby("team")

def rolling_averages(group, cols, new_cols):
    group = group.sort_values("date")
    rolling_stats = group[cols].rolling(3, closed="left").mean()
    group[new_cols] = rolling_stats
    group = group.dropna(subset=new_cols)
    return group

cols = ["gf", "ga", "sh", "sot", "dist", "fk", "pk", "pkatt", "xg", "cmp%", "totdist", "prgdist", "1/3", "ppa", "prgp", "poss_y", "touches", "att 3rd", "att pen", "succ%"]
new_cols = [f"{c}_rolling" for c in cols]
matches_rolling = matches.groupby("team").apply(lambda x: rolling_averages(x, cols, new_cols))
matches_rolling = matches_rolling.droplevel("team")
matches_rolling.index = range(matches_rolling.shape[0])

def make_predictions(data, predictors):
    rf = RandomForestClassifier(n_estimators=500, min_samples_split=10, random_state=1)
    train = data[data["date"] < "2025-01-02"]
    test = data[data["date"] >= '2025-01-02']
    rf.fit(train[predictors], train["target"])
    preds = rf.predict(test[predictors])
    combined = pd.DataFrame(dict(actual=test["target"], predicted=preds), index=test.index)
    precision = precision_score(test["target"], preds)
    return combined, precision

predictors = ["venue_code", "opp_code", "hour", "day_code", "formation_code", "opp_formation_code"]
combined, precision = make_predictions(matches_rolling, predictors + new_cols)
combined = combined.merge(matches_rolling[["date", "team", "opponent", "result"]], left_index=True, right_index=True)

class MissingDict(dict):
    __missing__ = lambda self, key: key

map_values = {
    "Brighton and Hove Albion": "Brighton",
    "Manchester United": "Manchester Utd",
    "Newcastle United": "Newcastle Utd",
    "Tottenham Hotspur": "Totteham",
    "West Ham United": "West Ham",
    "Wolverhampton Wanderers": "Wolves",
    "Nottingham Forest": "Nott'ham Forest",
    "Sheffield United": "Sheffield Utd"
}
mapping = MissingDict(**map_values)
combined["new_team"] = combined["team"].map(mapping)
merged = combined.merge(combined, left_on=["date", "new_team"], right_on=["date", "opponent"])
result = merged[(merged["predicted_x"] == 1) & (merged["predicted_y"] == 0)]["actual_x"].value_counts()
print(result)
print(result[1]/(result[0]+result[1]))