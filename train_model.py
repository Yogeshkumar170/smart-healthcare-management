"""
Creates an educational RandomForest classifier using SYNTHETIC training data.
This is only for demonstrating an AI/ML pipeline in a student project.
It is not a medically validated model.
"""
import os
import pickle
import random
import numpy as np
from sklearn.ensemble import RandomForestClassifier

BASE = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE, "model")
os.makedirs(MODEL_DIR, exist_ok=True)

SYMPTOMS = [
    "fever", "cough", "fatigue", "headache", "sore_throat",
    "runny_nose", "body_pain", "nausea", "vomiting", "diarrhea",
    "abdominal_pain", "chest_pain", "shortness_of_breath",
    "dizziness", "skin_rash", "joint_pain", "loss_of_smell",
    "loss_of_taste", "frequent_urination", "increased_thirst"
]

PATTERNS = {
    "Common Cold": ["cough", "runny_nose", "sore_throat", "headache", "fatigue"],
    "Flu-like Illness": ["fever", "body_pain", "fatigue", "headache", "cough"],
    "Gastrointestinal Illness": ["nausea", "vomiting", "diarrhea", "abdominal_pain"],
    "Respiratory Illness": ["cough", "shortness_of_breath", "chest_pain", "fatigue"],
    "Possible Diabetes Risk": ["frequent_urination", "increased_thirst", "fatigue", "dizziness"],
    "Allergy-like Symptoms": ["skin_rash", "runny_nose", "sore_throat", "headache"],
}

random.seed(42)
X, y = [], []

for label, core in PATTERNS.items():
    core = set(core)
    for _ in range(300):
        row = []
        for symptom in SYMPTOMS:
            p = 0.75 if symptom in core else 0.07
            row.append(1 if random.random() < p else 0)
        X.append(row)
        y.append(label)

X = np.array(X)
model = RandomForestClassifier(
    n_estimators=250,
    max_depth=12,
    random_state=42,
    class_weight="balanced"
)
model.fit(X, y)

path = os.path.join(MODEL_DIR, "disease_model.pkl")
with open(path, "wb") as f:
    pickle.dump(model, f)

print("Model created:", path)
print("Classes:", list(model.classes_))
