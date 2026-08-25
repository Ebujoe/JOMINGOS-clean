import numpy as np
import pandas as pd

np.random.seed(42)  # this helps to produce same dataset everytime
N = 6000  # number of rows i have generated


def news2_score(hr, rr, spo2, temp, sbp, on_oxygen, consciousness):   #this function will calculate the score (according to NEWS2)of a patient and returns total_score and max_single_param_score.

    # Each parameter contributes 0-3 points based on how far it deviates from normal.
    
    # we need to escalates a patient to urgent review if ANY single parameter scores 3, even if the total score(max_single_param_score) is low.
  
    points = []   # points are added to this list

    #   Respiratory rate (breaths/min)
    if rr <= 8 or rr >= 25:
        points.append(3)
    elif 21 <= rr <= 24:
        points.append(2)
    elif 9 <= rr <= 11:
        points.append(1)
    else:
        points.append(0)

    #  SpO2, (Scale 1 (%)) we have 2 scales and we chose scale 1 to calculate the scores
    if spo2 <= 91:
        points.append(3)
    elif 92 <= spo2 <= 93:
        points.append(2)
    elif 94 <= spo2 <= 95:
        points.append(1)
    else:
        points.append(0)

    # supplemental oxygen
    # NEWS2 awards 2 points if the patient needs supplemental oxygen
    points.append(2 if on_oxygen else 0)

    #Systolic blood pressure
    if sbp <= 90 or sbp >= 220:
        points.append(3)
    elif 91 <= sbp <= 100:
        points.append(2)
    elif 101 <= sbp <= 110:
        points.append(1)
    else:
        points.append(0)

    #Pulse / heart rate
    if hr <= 40 or hr >= 131:
        points.append(3)
    elif 111 <= hr <= 130:
        points.append(2)
    elif (91 <= hr <= 110) or (41 <= hr <= 50):
        points.append(1)
    else:
        points.append(0)

    # Consciousness (Alert / Confusion / Voice / Pain / Unresponsive)
    #NEWS2 awards 3 points for any level other than "Alert"
    points.append(0 if consciousness == "Alert" else 3)

    #Temperature (C)
    if temp <= 35.0:
        points.append(3)
    elif temp >= 39.1:
        points.append(2)
    elif (35.1 <= temp <= 36.0) or (38.1 <= temp <= 39.0):
        points.append(1)
    else:
        points.append(0)

    return sum(points), max(points) #sum(points) is used by adding all the scores
                                    # max(points) is used in risk-category assignment to calculate the risk coz max(points) gives you the highest value in the list and even if you have all parameters as 0s and one parameter has a score of 3, patient still needs to be esculated

def sample_patient(band):  # dataset is developed based on this "band" which can be mild, stable or severe.

    age = int(np.clip(np.random.normal(78, 12), 60, 101))   # this generates ages that are between 60 and 101 coz this dataset is of care-homes residents
    gender = np.random.choice(["Male", "Female"])

    if band == "stable":
        hr, rr, spo2, temp, sbp = (
            np.random.normal(78, 8), np.random.normal(16, 1.5),    # (mean, standerd deviation) number that is be generated will be around mean
            np.random.normal(97.5, 1.2), np.random.normal(36.8, 0.3),
            np.random.normal(120, 10),
        )
        on_oxygen = np.random.random() < 0.03   # this generates a decimal number between 0 and 1. and if the decimal is less than 0.03 then it gives true if not then it gives false.(3% chance for oxygen requirement)
        consciousness = np.random.choice(["Alert", "Confusion"], p=[0.99, 0.01])  # "p" is just a probabili"ty of getting "alert" and "confusion"
    elif band == "mild":
        hr, rr, spo2, temp, sbp = (
            np.random.normal(102, 12), np.random.normal(21, 2.5),
            np.random.normal(93.5, 1.5), np.random.normal(38.3, 0.5),
            np.random.normal(102, 12),
        )
        on_oxygen = np.random.random() < 0.25   # 25% chances that the oxygen requirement is needed.(it just randomly gives you a pick of 25% true and 75% false)
        consciousness = np.random.choice(["Alert", "Confusion"], p=[0.90, 0.10])
    else:  # severe
        hr, rr, spo2, sbp = (
            np.random.normal(135, 15), np.random.normal(28, 4),
            np.random.normal(88, 3), np.random.normal(85, 15),
        )
        temp = np.random.choice([np.random.normal(39.6, 0.4), np.random.normal(34.5, 0.5)])  # it generates to temperatures around 39 and 34 and np.random.choice selects one out of them.
        on_oxygen = np.random.random() < 0.70   # 70% of the severe patients require oxygen
        consciousness = np.random.choice(
            ["Alert", "Confusion", "Voice", "Pain", "Unresponsive"],
            p=[0.55, 0.20, 0.15, 0.07, 0.03]   # probability of severe patients being conscious.
        )

    #This prevents random generation from producing extremely unrealistic values.
    hr = float(np.clip(hr, 35, 190))
    rr = float(np.clip(rr, 5, 45))
    spo2 = float(np.clip(spo2, 70, 100))
    temp = float(np.clip(temp, 33.5, 41.5))
    sbp = float(np.clip(sbp, 55, 230))
    dbp = float(np.clip(sbp * 0.65, 35, 130))  # The code estimates DBP from SBP.
                                               #However, DBP is not used in the NEWS2 score.It is included because blood-pressure information is useful in the dataset.


    return (age, gender, round(hr, 1), round(rr, 1), round(spo2, 1),   # this is what the function is returning
            round(temp, 2), round(sbp, 1), round(dbp, 1), on_oxygen, consciousness)   # rounds the values before it returns.


# since most of the care-home residents are stable and only few shows mild and severe symptoms we generate data in this percentage
band_choices = np.random.choice(["stable", "mild", "severe"], size=N, p=[0.72, 0.20, 0.08])   # generates patients dataset in the ratio of 72%, 20%, and 8%

rows = []  #empty list whic will be filled with 6000 rows
for i, band in enumerate(band_choices):      # i is index position of the item and band_choice is the actual value of the item in that index position. the value might be stable, mild or severe.  enumerate() is a Python function that lets you loop through a list while getting both the index and the value at the same time.
    age, gender, hr, rr, spo2, temp, sbp, dbp, on_oxygen, consciousness = sample_patient(band)
    total_score, max_single = news2_score(hr, rr, spo2, temp, sbp, on_oxygen, consciousness)
  # total_score calculates the score and max_single finds the highest value.

# risk assessment scale
    if total_score >= 7:
        risk = "High"
    elif total_score >= 5 or max_single == 3:
        risk = "Medium"
    else:
        risk = "Low"

    rows.append([      # adding patients into rows to make a dataset
        i + 1, age, gender, hr, rr, temp, spo2, sbp, dbp,        #since pythons indexing starts with 0, we made i+1 so that now the indexing of patients id will be started with 1 and not 0
        "Yes" if on_oxygen else "No", consciousness, total_score, risk
    ])

df = pd.DataFrame(rows, columns=[     # this will now become a dataframe.
    "Patient ID", "Age", "Gender", "Heart Rate (bpm)", "Resp Rate (bpm)",
    "Body Temp (C)", "SpO2 (%)", "Systolic BP (mmHg)", "Diastolic BP (mmHg)",
    "On Oxygen", "Consciousness", "NEWS2 Score", "Risk Category"
])

# Save as CSV directly into your vitals data folder
df.to_csv("../vitals data/vitals_dataset_v2.csv", index=False)

print("Shape:", df.shape)
print("\nRisk Category distribution:\n", df["Risk Category"].value_counts())
print("\nMeans by risk category:\n", df.groupby("Risk Category")[
    ["Heart Rate (bpm)", "Resp Rate (bpm)", "Body Temp (C)", "SpO2 (%)", "Systolic BP (mmHg)"]
].mean())