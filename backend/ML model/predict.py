import joblib
import numpy as np
import pandas as pd
import shap

pipeline = joblib.load("risk_model.joblib")   # loading the trained model
preprocessor = pipeline.named_steps["preprocess"]  # named_steps allows you to access preprocessor
classifier = pipeline.named_steps["classifier"]    # named_steps allows you to access stackingclassifier
ENCODED_FEATURE_NAMES = preprocessor.get_feature_names_out()  # brininging back the column names after preprocessing after applying standardscaler and onehotencoding

background_sample = joblib.load("shap_background.joblib")
explainer = shap.Explainer(classifier.predict_proba, background_sample)  #classifier already knows how to predict. SHAP explainer just uses the prediction function to determine which feature pushied higher and lower for a prediction
 # SHAP just explains the probability (predict_prob) produced by the classifier # shap.Explainer will create an object that calculates SHAP values for the model
 # because SHAP needs reference point/ baseline prediction it is using background_sample
CATEGORICAL_FEATURES = ["Gender", "On Oxygen", "Consciousness"]   # these are the features that we have onhotencoded which SHAP needs in next steps

PLAUSIBLE_RANGES = {    # to reject clearly invalid input
    "Age": (0, 120),
    "Heart Rate (bpm)": (20, 250),
    "Resp Rate (bpm)": (4, 60),
    "Body Temp (C)": (25.0, 45.0),    #   any input through the webapp should be between these values for the model to accept and predict
    "SpO2 (%)": (50.0, 100.0),
    "Systolic BP (mmHg)": (40, 300),
    "Diastolic BP (mmHg)": (20, 200),
}
VALID_CATEGORIES = {
    "Gender": {"Male", "Female"},
    "On Oxygen": {"Yes", "No"},                             # will only accept these values as input for these categories
    "Consciousness": {"Alert", "Confusion", "Voice", "Pain", "Unresponsive"},
}

# normal ranges 
CLINICAL_NORMAL_RANGES = {
    "Heart Rate (bpm)": (60, 100),
    "Resp Rate (bpm)": (12, 20),
    "Body Temp (C)": (36.1, 37.2),
    "SpO2 (%)": (95, 100),
    "Systolic BP (mmHg)": (90, 120),
    "Diastolic BP (mmHg)": (60, 80),
}


def validate_vitals(vitals):   # vitals is a dictionary parameter
    # Collects every problem with the input and raises one clear error listing them all.
    problems = []
    required_fields = list(PLAUSIBLE_RANGES) + list(VALID_CATEGORIES)

    for field in required_fields:
        if field not in vitals:       # points out the missing fields
            problems.append(f"'{field}' is missing.")

    for field, (low, high) in PLAUSIBLE_RANGES.items():   # this will loop through every numeric values and checks for the minimum and maximum values
        if field in vitals:
            value = vitals[field]   # if the vitals are not given then it will not validate
            if not isinstance(value, (int, float)):   # checks if the value is either int or float. coz it accepts int and float 
                problems.append(f"'{field}' must be a number.")  # if you add string input instead of a number it will give you error
            elif not (low <= value <= high):   # checks the value f it is between plausable range
                problems.append(f"'{field}' = {value} is outside the plausible range ({low}-{high}).") # tells if the entered number is outside the plausible range

    for field, valid_options in VALID_CATEGORIES.items():  # goes through the valid_categories's keys 
        if field in vitals and vitals[field] not in valid_options: # it checks if the field(key) exists and the entered value is not one of the allowed values
            problems.append(f"'{field}' = '{vitals[field]}' must be one of {sorted(valid_options)}.") # since categories are stored as "set" which has no particular order sorted() is used to make it an ordered list

    if problems:
        raise ValueError("Invalid vitals input:\n- " + "\n- ".join(problems))  # gives all the problems


def decode_feature_name(encoded_name):   # it removes the "num__" and gives it's name back
    # Maps an encoded column like 'cat__Consciousness_Confusion' back to 'Consciousness' .
    for field in CATEGORICAL_FEATURES:
        if field in encoded_name:
            return field
    return encoded_name.replace("num__", "")


def describe_field(field, vitals): #  this uses the clinical_normal_ranges dictionary to decide the risk levels
    if field == "Consciousness":   # field is key in the vitals dictionary
        return "Patient is fully alert" if vitals["Consciousness"] == "Alert" else "Reduced level of consciousness"  # since this is not a numeric column we are dealing it separately

    if field not in CLINICAL_NORMAL_RANGES:  # checks if the field has clinical normal range 
        return None  

    value = vitals[field]   # gives patient's actual vitals
    low, high = CLINICAL_NORMAL_RANGES[field]     # gets nomal range
    label = field.split(" (")[0]    # makes output easier to read

    if value < low:
        return f"{label} is low"    # checks if the value is low
    if value > high:
        return f"{label} is high"        #checks if the value is high
    return f"{label} is normal"   # says if it is normal (if both the above values are false then it is normal)

# we already know the category of risk, explain_prediction explains how this prediction is derived
def explain_prediction(encoded_row, predicted_class, class_names, vitals, max_reasons=3):  # encoded_row is patient's data after encoding "num__"
    # Uses SHAP to rank which vitals mattered most, then phrases the top few as reasons. # prediction_class is categorical risk prediction by model
    # class_names have all possible prediction of risk # vitals are dictionary  # max_reasons=3, gives 3 reasons of why it has come to the prediction
    explanation = explainer(encoded_row)   #SHAP analyzes this patient's encoded data and calculates how each feature contributed to the model's output and the value is stored in this variable.
    class_index = list(class_names).index(predicted_class)# list(class_names) is having all possible outcomes #predict_class will have the predicted output
    contributions = explanation.values[0, :, class_index]   # now this explains why it has come to the conclusions

    ranked_features = sorted(  # it sorts with high influence to come to the conclusion to the lowest one up to three results.
        zip(ENCODED_FEATURE_NAMES, contributions), key=lambda pair: abs(pair[1]), reverse=True
    )       # encoded column names(ex. num__heart) and their contribution(it's value will be in float) as an evidence for the conclusion

    reasons = []
    fields_already_used = set() # it writes the fields into this set.
    for encoded_name, _ in ranked_features:
        field = decode_feature_name(encoded_name)   # it decodes the encoded column names
        if field in fields_already_used:
            continue   # since multiple olumns will be created while encoding, once the field is stored in the set, we will not store it again and we skip it using "continue"
        description = describe_field(field, vitals)   # function takes the actual patient's data and give it a meaning full outcome to explain
        if description:
            reasons.append(description) # it keeps on appending the reasons for the conclusion upto 3
            fields_already_used.add(field)
        if len(reasons) >= max_reasons: # it will stop after 3 reasons
            break
    return reasons


def predict_risk(vitals):
    
    # Takes a dictionary of vitals and returns the predicted risk category,a confidence score, whether it's a close call, and the top reasons why.
    
    validate_vitals(vitals)   # checks if the vitals are valid or invalid

    raw_row = pd.DataFrame([vitals])    # puts the patient's data into dataframe from dictionary
    encoded_row = preprocessor.transform(raw_row)   # encodes the patient's data into ML understandable number forms(0.89 etc ) which is later used for SHAP explanation

    probabilities = pipeline.predict_proba(raw_row)[0]  # since we ar epredicting for one patient it will be [0] # prediction is done by using this. coz pipeline contains preprocessig step
    class_names = pipeline.classes_   #gets the names of the claases (low, medium, high)

    ranked_indexes = np.argsort(probabilities)[::-1]        # sorts probability from high to low
    top_index, runner_up_index = ranked_indexes[0], ranked_indexes[1]  # the 2nd value is also important coz we can see the close call

    predicted_class = class_names[top_index]   #  this is where model actually predicts
    confidence = round(float(probabilities[top_index]) * 100, 1)   # this shows how confident the model actually is
    confidence_gap = round(float(probabilities[top_index] - probabilities[runner_up_index]) * 100, 1) # compares the hiest one with the next one and checks the gap between 2 categories
    is_borderline = confidence_gap < 15.0   # if the prediction gap is just lest than 15 then we consider it as boarder line prediction
    reasons = explain_prediction(encoded_row, predicted_class, class_names, vitals) 

    return {
        "prediction": str(predicted_class),
        "confidence": confidence,               # it gives the result of prediction, confidence, reasons and tells if it is boarderline prediction 
        "reasons": reasons,
        "borderline": is_borderline,
    }


if __name__ == "__main__":
    high_risk_patient = {                   # test data
        "Age": 84, "Gender": "Female", "Heart Rate (bpm)": 128, "Resp Rate (bpm)": 27,
        "Body Temp (C)": 38.9, "SpO2 (%)": 89, "Systolic BP (mmHg)": 92, "Diastolic BP (mmHg)": 58,
        "On Oxygen": "Yes", "Consciousness": "Confusion",
    }
    low_risk_patient = {
        "Age": 71, "Gender": "Male", "Heart Rate (bpm)": 76, "Resp Rate (bpm)": 15,
        "Body Temp (C)": 36.8, "SpO2 (%)": 98, "Systolic BP (mmHg)": 122, "Diastolic BP (mmHg)": 79,
        "On Oxygen": "No", "Consciousness": "Alert",
    }
    invalid_patient = {**low_risk_patient, "Heart Rate (bpm)": 764}

    print(" Clearly high risk")
    print(predict_risk(high_risk_patient))

    print("\n Clearly low risk")
    print(predict_risk(low_risk_patient))

    print("\n Invalid input (should raise an error)")
    try:
        predict_risk(invalid_patient)
    except ValueError as e:
        print("Rejected:", e)