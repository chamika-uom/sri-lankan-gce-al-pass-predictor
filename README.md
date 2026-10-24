# Sri Lankan GCE A/L General English Pass Prediction

This is a beginner-level Applied Machine Learning assignment using a real Sri Lankan tabular dataset.

## Problem

Can a model predict whether a Sri Lankan GCE Advanced Level candidate receives a **Pass** in General English from the candidate's stream, syllabus, subject choices and grades in the other three subjects?

The target is deliberately simplified:

- `Pass`: General English grade is A, B, C or S.
- `Non-pass`: General English grade is F, Absent or Withheld.

This is an educational analysis, not an admissions or employment decision system.

## Dataset

The source dataset is **Student Performance (GCE AL Exam 2020 - Sri Lanka)**, collected from the Sri Lankan Department of Examinations result site and published by Sasika Amarasinghe on Kaggle. The downloaded source has 337,553 rows and 19 columns. This project keeps a reproducible 80,000-row stratified sample in `data/sl_al_2020_sample.csv` so that a beginner can run the project on a normal laptop.

The project removes identifiers, rank columns, birth information and gender. The retained inputs are categorical:

`stream`, `syllabus`, `sub1`, `sub1_r`, `sub2`, `sub2_r`, `sub3`, `sub3_r`

The target source column `ge_r` is not used as an input.

## Run

```bash
python3 -m pip install -r requirements.txt
python3 src/train_model.py
streamlit run app.py
```

The training script creates:

- `artifacts/model_bundle.joblib` - saved best model and preprocessing metadata
- `artifacts/model_bundle.pkl` - pickle export of the saved best model and preprocessing metadata
- `outputs/model_metrics.csv` - model comparison
- `outputs/eda_class_distribution.png` - target distribution
- `outputs/confusion_matrix.png` - best-model confusion matrix
- `outputs/shap_summary.png` - global SHAP explanation
- `outputs/lime_local.html` - local LIME explanation for one test row
- `outputs/single_inference.txt` - left-out-row prediction

## Models and preprocessing

1. Random Forest: one-hot encoding, frequent-value imputation and sparse standardisation.
2. XGBoost: the same one-hot pipeline, with manually selected boosting parameters.
3. CatBoost: native categorical processing with manually selected parameters.

The parameters are intentionally written in the code rather than relying on defaults. A small `RandomizedSearchCV` step tunes Random Forest and XGBoost using macro F1 on a training subset. CatBoost is configured using the selected final settings and compared on the same test set.

Tree models do not require numeric scaling for their splits. The one-hot pipelines still include `StandardScaler(with_mean=False)` to demonstrate a safe sparse scaling step; CatBoost is left in native categorical form because that is its main strength.

## Sources

- Dataset description: https://sasikaa073.github.io/projects/6-al_data/
- Kaggle dataset page: https://www.kaggle.com/datasets/sasikaamarasinghe/student-performance-gce-al-exam-2020-sri-lanka
- Sri Lankan Department of Examinations statistics: https://doenets.lk/statistics
