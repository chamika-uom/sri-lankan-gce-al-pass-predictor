"""Create a simple code-only notebook for submission."""

from pathlib import Path

import nbformat as nbf


ROOT = Path(__file__).resolve().parents[1]
nb = nbf.v4.new_notebook()
cells = []

cells.append(nbf.v4.new_code_cell(
    """# Load the data and project functions
from pathlib import Path
import sys
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

ROOT = Path.cwd()
if not (ROOT / 'data').exists():
    ROOT = ROOT.parent
sys.path.append(str(ROOT / 'src'))
from train_model import FEATURES, load_and_prepare

# Use the prepared sample so the notebook runs on a normal laptop
data_path = ROOT / 'data' / 'sl_al_2020_sample.csv'
X, y, frame = load_and_prepare(data_path)
X = X.fillna('Unknown').astype(str)
print('Rows:', len(frame))
print('Features:', FEATURES)
frame.head()"""
))

cells.append(nbf.v4.new_code_cell(
    """# Check the data and target classes
print('Data types:')
print(frame.dtypes)
print()
print('Missing values:')
print(frame[FEATURES + ['ge_r']].isna().sum())
print()
print('Target counts:')
print(y.map({0: 'Non-pass', 1: 'Pass'}).value_counts())

sns.countplot(
    x=y.map({0: 'Non-pass', 1: 'Pass'}),
    order=['Pass', 'Non-pass'],
    palette=['#2a9d8f', '#e76f51'],
)
plt.title('General English target distribution')
plt.show()"""
))

cells.append(nbf.v4.new_code_cell(
    """# Split the data into training and test parts
from sklearn.model_selection import train_test_split

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.20, stratify=y, random_state=42
)
print('Training rows:', len(X_train))
print('Test rows:', len(X_test))"""
))

cells.append(nbf.v4.new_code_cell(
    """# Train and compare the three models
from train_model import tune_models, make_categorical_nb_pipeline, fit_and_score

rf_search, xgb_search = tune_models(X_train, y_train)
models = {
    'Random Forest': rf_search.best_estimator_,
    'XGBoost': xgb_search.best_estimator_,
    'Categorical Naive Bayes': make_categorical_nb_pipeline(),
}

metrics = fit_and_score(models, X_train, X_test, y_train, y_test)
metrics_df = pd.DataFrame(metrics).sort_values('f1_macro', ascending=False)
metrics_df"""
))

cells.append(nbf.v4.new_code_cell(
    """# Print the settings selected for the two searches
print('Tuned Random Forest parameters:')
print(rf_search.best_params_)
print()
print('Tuned XGBoost parameters:')
print(xgb_search.best_params_)"""
))

cells.append(nbf.v4.new_code_cell(
    """# Create SHAP and LIME explanations for the new algorithm
from train_model import explain_with_shap, explain_with_lime

explain_with_shap(models['Categorical Naive Bayes'], X_test)
explain_with_lime(models['Categorical Naive Bayes'], X_train, X_test)

from IPython.display import Image, display
display(Image(filename=str(ROOT / 'outputs' / 'shap_summary.png')))"""
))

cells.append(nbf.v4.new_code_cell(
    """# Test one left-out record
best_name = metrics_df.iloc[0]['model']
best_model = models[best_name]
one_row = X_test.iloc[[0]]
prediction = int(best_model.predict(one_row)[0])
probability = float(best_model.predict_proba(one_row)[0, 1])

print('Best model:', best_name)
print('Predicted target:', 'Pass' if prediction == 1 else 'Non-pass')
print('Pass probability:', round(probability, 3))
one_row"""
))

cells.append(nbf.v4.new_code_cell(
    """# A short summary for the assignment
print('Categorical Naive Bayes is the additional algorithm used in this project.')
print('The data comes from the 2020 Sri Lankan GCE A/L examination.')
print('The model is for learning and should not be used for high-stakes decisions.')"""
))

nb['cells'] = cells
nb['metadata'] = {
    'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'},
    'language_info': {'name': 'python', 'version': '3'},
}
out = ROOT / 'notebooks' / 'assignment_notebook.ipynb'
out.parent.mkdir(exist_ok=True)
nbf.write(nb, out)
print(out)
