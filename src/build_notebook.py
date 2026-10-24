"""Create a readable Jupyter notebook for submission."""

from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
nb = nbf.v4.new_notebook()
cells = []

cells.append(nbf.v4.new_markdown_cell(
    """# Predicting General English Pass in the Sri Lankan GCE A/L dataset

**Student-level explanation:** I use a real Sri Lankan dataset and predict a binary categorical target: whether the General English grade is a pass. I use only non-identifying categorical inputs. The models are Random Forest, XGBoost and CatBoost. I compare their metrics, explain CatBoost using SHAP and LIME, and save the best model for a small app.

This notebook is written in simple steps so I can explain it in a short demo."""
))

cells.append(nbf.v4.new_markdown_cell(
    """## 1. Problem and dataset

The source is the 2020 GCE Advanced Level student performance dataset for Sri Lanka. The raw file has 337,553 records. For a fast and reproducible beginner demo, I use the provided stratified 80,000-row sample.

I do not use index, rank, birth, or gender fields. The prediction is for educational analysis only; it is not an admissions decision."""
))

cells.append(nbf.v4.new_code_cell(
    """from pathlib import Path
import sys
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

ROOT = Path.cwd()
if not (ROOT / 'data').exists():
    ROOT = ROOT.parent
sys.path.append(str(ROOT / 'src'))
from train_model import FEATURES, load_and_prepare

data_path = ROOT / 'data' / 'sl_al_2020_sample.csv'
X, y, frame = load_and_prepare(data_path)
X = X.fillna('Unknown').astype(str)
print('Rows:', len(frame))
print('Features:', FEATURES)
frame.head()"""
))

cells.append(nbf.v4.new_markdown_cell(
    """## 2. Data understanding and EDA

The original grade column `ge_r` is converted into the target. A, B, C and S are treated as Pass. F, Absent and Withheld are treated as Non-pass. A binary target is easier to explain than seven grade classes."""
))

cells.append(nbf.v4.new_code_cell(
    """print('Data types:')
print(frame.dtypes)
print()
print('Missing values:')
print(frame[FEATURES + ['ge_r']].isna().sum())
print()
print('Target counts:')
print(y.map({0: 'Non-pass', 1: 'Pass'}).value_counts())

sns.countplot(x=y.map({0: 'Non-pass', 1: 'Pass'}), order=['Pass', 'Non-pass'], palette=['#2a9d8f', '#e76f51'])
plt.title('General English target distribution')
plt.show()"""
))

cells.append(nbf.v4.new_markdown_cell(
    """## 3. Preprocessing and split

The input fields are categorical. For Random Forest and XGBoost I use most-frequent imputation, one-hot encoding and sparse scaling inside a pipeline. This prevents leakage because the transformations are fitted only on training data. CatBoost keeps the categories as strings because native categorical processing is its main advantage."""
))

cells.append(nbf.v4.new_code_cell(
    """from sklearn.model_selection import train_test_split

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.20, stratify=y, random_state=42
)
print(X_train.shape, X_test.shape)"""
))

cells.append(nbf.v4.new_markdown_cell(
    """## 4. Train and compare multiple models

The parameter values are chosen deliberately. A small randomized search tunes Random Forest and XGBoost using macro F1. CatBoost uses explicit iterations, depth, learning rate and regularisation values."""
))

cells.append(nbf.v4.new_code_cell(
    """from train_model import tune_models, make_catboost, fit_and_score

rf_search, xgb_search = tune_models(X_train, y_train)
models = {
    'Random Forest': rf_search.best_estimator_,
    'XGBoost': xgb_search.best_estimator_,
    'CatBoost': make_catboost(),
}
metrics = fit_and_score(models, X_train, X_test, y_train, y_test)
metrics_df = pd.DataFrame(metrics).sort_values('f1_macro', ascending=False)
metrics_df"""
))

cells.append(nbf.v4.new_code_cell(
    """print('Tuned Random Forest parameters:')
print(rf_search.best_params_)
print()
print('Tuned XGBoost parameters:')
print(xgb_search.best_params_)"""
))

cells.append(nbf.v4.new_markdown_cell(
    """## 5. Explainability with SHAP and LIME

CatBoost is a useful model for this categorical dataset. I use SHAP for a global view of feature contribution and LIME for a local explanation of one candidate row. The generated files are also saved in the `outputs` folder."""
))

cells.append(nbf.v4.new_code_cell(
    """from train_model import explain_with_shap, explain_with_lime

explain_with_shap(models['CatBoost'], X_test)
explain_with_lime(models['CatBoost'], X_train, X_test)
from IPython.display import Image, display
display(Image(filename=str(ROOT / 'outputs' / 'shap_summary.png')))"""
))

cells.append(nbf.v4.new_markdown_cell(
    """## 6. Single-row inference and saved model

I keep the test set separate. One test row is used as an example of inference. The final training script saves the best model and metadata to `artifacts/model_bundle.joblib`, which is loaded by `app.py`."""
))

cells.append(nbf.v4.new_code_cell(
    """best_name = metrics_df.iloc[0]['model']
best_model = models[best_name]
one_row = X_test.iloc[[0]]
prediction = int(best_model.predict(one_row)[0])
probability = float(best_model.predict_proba(one_row)[0, 1])
print('Best model:', best_name)
print('Predicted target:', 'Pass' if prediction == 1 else 'Non-pass')
print('Pass probability:', round(probability, 3))
one_row"""
))

cells.append(nbf.v4.new_markdown_cell(
    """## 7. Final interpretation

The models are all tree ensembles, so they can learn interactions between stream, subject choice and grade categories. XGBoost is selected if it has the best macro F1 on the held-out test set. CatBoost is still important because its categorical handling is natural and its SHAP/LIME explanations are easy to demonstrate.

Limitations: the data is from the 2020 examination, the target is based on the same exam result record, and the sample is not a causal or early-warning study. The model should not be used for high-stakes decisions."""
))

nb['cells'] = cells
nb['metadata'] = {'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'}, 'language_info': {'name': 'python', 'version': '3'}}
out = ROOT / 'notebooks' / 'assignment_notebook.ipynb'
out.parent.mkdir(exist_ok=True)
nbf.write(nb, out)
print(out)
