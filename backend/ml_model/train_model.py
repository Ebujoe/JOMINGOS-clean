import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split, GridSearchCV, StratifiedKFold
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, StackingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, f1_score

DATA_PATH = "../vitals data/vitals_dataset_v2.csv"

NUMERIC_FEATURES = [
    "Age", "Heart Rate (bpm)", "Resp Rate (bpm)", "Body Temp (C)",
    "SpO2 (%)", "Systolic BP (mmHg)", "Diastolic BP (mmHg)",
]
CATEGORICAL_FEATURES = ["Gender", "On Oxygen", "Consciousness"]
TARGET = "Risk Category"


def load_data(path):   # loads the data and split it into X and Y(target variable)
    df = pd.read_csv(path)
    X = df[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    y = df[TARGET]
    return X, y


def build_preprocessor(): # this function doesn't need any parameters as an input, it just returns.
    return ColumnTransformer([
        ("num", StandardScaler(), NUMERIC_FEATURES),   # it standardised numeric columns to make it's value around 1 (standard deviation) and 0(mean) (value might increase sometimes)
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_FEATURES),   #   it onehotencoded all then categorical columns to create new columns and converted to 0s and 1s.
    ])


def get_candidate_models():
    return {   
        "Random Forest": (
            RandomForestClassifier(random_state=42, class_weight="balanced"),
            {
                "classifier__n_estimators": [200, 300],  # we say it to build either 200 or 300 trees
                "classifier__max_depth": [6, 8, 10],    # tells how much depth each tree should be          
                "classifier__min_samples_leaf": [1, 2, 4],   # options to have  number of leaves
            },      # these are given with prefix classifier__ so that these will be taken as "classifier" in pipline step.
        ),
        "Gradient Boosting": (
            GradientBoostingClassifier(random_state=42),
            {
                "classifier__n_estimators": [100, 200],  # how many trees are added
                "classifier__max_depth": [2, 3, 4],    # keeping it shallow coz GB combines many small trees and won't combine few trees with more depth
                "classifier__learning_rate": [0.05, 0.1],   # how strongly the new tree corrects the error of the previous tree
            },
        ),
        "Logistic Regression": (
            LogisticRegression(max_iter=2000, class_weight="balanced"),   # 2000 internal optimization steps
            {"classifier__C": [0.1, 1, 10]},
        ),
    }


def tune_model(name, estimator, param_grid, preprocessor, X_train, y_train, cv): # runs gridsearchcv and gives back the best one
    pipeline = Pipeline([("preprocess", preprocessor), ("classifier", estimator)])  # preprocessor transform raw vitals through standardscaler and onehotencoding
    search = GridSearchCV(pipeline, param_grid, cv=cv, scoring="f1_macro", n_jobs=-1)  #  work on the pipeline results with param_grid combinations with cv number of times and give F1 every time using all cpu cores(to run fast)
    search.fit(X_train, y_train)
    return search    # returns the best performing version out of all the combinations mentioned above


def strip_pipeline_prefix(params): # takes one parameter from the dictionary(params) and trims off the prefix "classifier__" in the key
    return {key.replace("classifier__", ""): value for key, value in params.items()}


def build_stacking_ensemble(tuned_results):
    rf_params = strip_pipeline_prefix(tuned_results["Random Forest"].best_params_)  # it is taking each of 3 winning algorithms
    gb_params = strip_pipeline_prefix(tuned_results["Gradient Boosting"].best_params_)
    lr_params = strip_pipeline_prefix(tuned_results["Logistic Regression"].best_params_)
    base_learners = [      #(base models)      # creates new objects using those winnning model's hyperparameters
        ("random_forest", RandomForestClassifier(random_state=42, class_weight="balanced", **rf_params)),
        ("gradient_boosting", GradientBoostingClassifier(random_state=42, **gb_params)),
        ("logistic_regression", LogisticRegression(max_iter=2000, class_weight="balanced", **lr_params)),
    ]

    return StackingClassifier(     # meta learner model
        estimators=base_learners,   # stacking classifier uses those base models to generate outputs for meta learner
        final_estimator=LogisticRegression(max_iter=2000),
        cv=5,
        stack_method="predict_proba",  # base emodels create probabilities of each class
        n_jobs=-1,
    )     # this meta learner lears to predict the final answer from base model's probabilities


def evaluate(pipeline, X_test, y_test):   # pipeline should guess itself on the unseen test data now by it's own
# Prints accuracy, macro-F1, classification report, and confusion matrix.
    predictions = pipeline.predict(X_test)  # run the trained pipeline on test vitals data and gives back prediction
    accuracy = accuracy_score(y_test, predictions)   # compares it's prediction to the actual values
    macro_f1 = f1_score(y_test, predictions, average="macro") #calculate F1 separately for Low, Medium, and High then average those three numbers equally
    print(f"Stacking Ensemble: test accuracy = {accuracy:.4f}, test macro-F1 = {macro_f1:.4f}")  # .4f will round to 4 decimal places.
    print("Classification report:\n", classification_report(y_test, predictions)) # produces precision, recall, and F1 individually for High, Low, and Medium, plus overall accuracy and averages.
    print("Confusion matrix:\n", confusion_matrix(y_test, predictions))  # gives confusion matrix


def save_shap_background(pipeline, X_train, sample_size=100):   # it takes the sample size of 100 by default if we didn't specify while calling this function
    # this saves the 100 rows reference sample to build SHAP explainer to generate explanation for new samples.
    fitted_preprocessor = pipeline.named_steps["preprocess"]  # goes into the pipeline and takes the preprocessing step
    X_train_encoded = fitted_preprocessor.transform(X_train)   # it takes the trainig data and applies preprocessing by appling standardscalar and onehotencoding
    rng = np.random.RandomState(42)  # by fixing this random seed the result will always be same no matter how many time you produce
    sample_idx = rng.choice(X_train_encoded.shape[0], size=sample_size, replace=False)   # shape[0] is no. of rows and shape[1] is number of columns. replace=false is that it will not select a row more than once. sample size is fixed to 100 previously
    joblib.dump(X_train_encoded[sample_idx], "shap_background.joblib")  # from the training data it takes 100 rows and then it is saved in this joblib file


if __name__ == "__main__":
    X, y = load_data(DATA_PATH)   # loads the data and separates it into input and output variable
    preprocessor = build_preprocessor()  # before giving data to the to algoriths it just transforms the columns by applying standardscaler and onehotencoding
    X_train, X_test, y_train, y_test = train_test_split(    # used 20% data for testing and 80% for training
        X, y, test_size=0.2, random_state=42, stratify=y    # stratify=y keeps the portion of classes same in both training and testing data
    )
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)  # makes 5 splits and shuffles the rows 5 times/splits

    candidates = get_candidate_models()  
    tuned_results = {}   # it will store the results of each tuned model (3 models)
    for name, (estimator, param_grid) in candidates.items():
        tuned_results[name] = tune_model(name, estimator, param_grid, preprocessor, X_train, y_train, cv)

    stacking_classifier = build_stacking_ensemble(tuned_results)   # this is calling build_stacking_ensemble() and passing the tuned results into it
    stacking_pipeline = Pipeline([("preprocess", preprocessor), ("classifier", stacking_classifier)])   # preprocess the data and sends it to stacking classifier

    stacking_pipeline.fit(X_train, y_train)  # training the final stacking classifier by passing the training data  # actual training happens here

    evaluate(stacking_pipeline, X_test, y_test)   # testing the stacking classifier with unseen data    

    joblib.dump(stacking_pipeline, "risk_model.joblib")   # saving the stacking classifier into this joblib file. so that we can predict new patient using this joblib file.

    save_shap_background(stacking_pipeline, X_train)   # saving some backgound data for SHAP