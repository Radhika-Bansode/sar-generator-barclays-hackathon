import pandas as pd
import joblib
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
import numpy as np

df = pd.read_csv("/Users/shekharbansode/Desktop/sar_generator_barclays/data/training_data.csv")
print(f"Label Distribution: {df['label'].value_counts().to_dict()}")

# Total Rows: 50,000
# Expected: {1: 49994, 0: 6} (Hypothetically from my thought history)
