"""Train and explain a beginner-friendly categorical ML project."""

from __future__ import annotations

import json
import pickle
import warnings
from pathlib import Path

import joblib
import lime.lime_tabular
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import shap
from catboost import CatBoostClassifier
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import RandomizedSearchCV, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier

warnings.filterwarnings("ignore")
SEED = 42
ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "sl_al_2020_sample.csv"
ARTIFACT_DIR = ROOT / "artifacts"
OUTPUT_DIR = ROOT / "outputs"
FEATURES = ["stream", "syllabus", "sub1", "sub1_r", "sub2", "sub2_r", "sub3", "sub3_r"]
GRADE_PASS = {"A", "B", "C", "S"}


def load_and_prepare(path: Path):
    raw = pd.read_csv(path, low_memory=False)
    required = set(FEATURES + ["ge_r"])
    missing = required.difference(raw.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    frame = raw[FEATURES + ["ge_r"]].copy()
    for col in FEATURES + ["ge_r"]:
        frame[col] = frame[col].astype("string")
        frame[col] = frame[col].replace({"-": pd.NA, "Major error": pd.NA, "": pd.NA})
    # Numeric encoding is required by XGBoost.  In the app and explanations,
    # 0 is translated back to Non-pass and 1 to Pass.
    y = frame["ge_r"].map(lambda value: 1 if value in GRADE_PASS else 0).astype(int)
    return frame[FEATURES].copy(), y, frame


def make_one_hot_pipeline(model):
    preprocessor = ColumnTransformer(
        transformers=[
            (
                "categorical",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("one_hot", OneHotEncoder(handle_unknown="ignore", sparse_output=True)),
                        ("scale", StandardScaler(with_mean=False)),
                    ]
                ),
                FEATURES,
            )
        ],
        remainder="drop",
    )
    return Pipeline(steps=[("preprocess", preprocessor), ("model", model)])


def make_catboost():
    return CatBoostClassifier(
        iterations=260,
        depth=6,
        learning_rate=0.08,
        l2_leaf_reg=4.0,
        loss_function="Logloss",
        eval_metric="AUC",
        auto_class_weights="Balanced",
        random_seed=SEED,
        verbose=False,
        allow_writing_files=False,
    )


def tune_models(X_train, y_train):
    """A small search, easy to explain and fast enough for a laptop."""
    n = max(12000, min(len(X_train), 24000))
    X_tune = X_train.sample(n=n, random_state=SEED)
    y_tune = y_train.loc[X_tune.index]

    rf_base = RandomForestClassifier(class_weight="balanced_subsample", random_state=SEED, n_jobs=-1)
    rf_search = RandomizedSearchCV(
        make_one_hot_pipeline(rf_base),
        {
            "model__n_estimators": [140, 200, 260],
            "model__max_depth": [12, 18, 24],
            "model__min_samples_leaf": [2, 3, 5],
            "model__max_features": ["sqrt", 0.7],
        },
        n_iter=3,
        scoring="f1_macro",
        cv=2,
        random_state=SEED,
        n_jobs=-1,
    )
    rf_search.fit(X_tune, y_tune)

    xgb_base = XGBClassifier(
        objective="binary:logistic", eval_metric="logloss", tree_method="hist", random_state=SEED, n_jobs=-1
    )
    xgb_search = RandomizedSearchCV(
        make_one_hot_pipeline(xgb_base),
        {
            "model__n_estimators": [160, 220, 280],
            "model__max_depth": [3, 5, 7],
            "model__learning_rate": [0.04, 0.08, 0.12],
            "model__subsample": [0.75, 0.85, 1.0],
            "model__colsample_bytree": [0.75, 0.85, 1.0],
        },
        n_iter=3,
        scoring="f1_macro",
        cv=2,
        random_state=SEED,
        n_jobs=-1,
    )
    xgb_search.fit(X_tune, y_tune)
    return rf_search, xgb_search


def fit_and_score(models, X_train, X_test, y_train, y_test):
    results = []
    for name, model in models.items():
        if name == "CatBoost":
            model.fit(X_train, y_train, cat_features=list(range(len(FEATURES))))
        else:
            model.fit(X_train, y_train)
        pred = np.asarray(model.predict(X_test)).reshape(-1)
        prob = model.predict_proba(X_test)[:, 1]
        results.append(
            {
                "model": name,
                "accuracy": accuracy_score(y_test, pred),
                "precision_macro": precision_score(y_test, pred, average="macro", zero_division=0),
                "recall_macro": recall_score(y_test, pred, average="macro", zero_division=0),
                "f1_macro": f1_score(y_test, pred, average="macro"),
                "roc_auc": roc_auc_score(y_test, prob),
            }
        )
    return results


def make_eda(y, frame):
    sns.set_theme(style="whitegrid")
    plt.figure(figsize=(7, 4))
    labels = y.map({0: "Non-pass", 1: "Pass"})
    ax = sns.countplot(x=labels, order=["Pass", "Non-pass"], palette=["#2a9d8f", "#e76f51"])
    ax.set_title("Target distribution: General English outcome")
    ax.set_xlabel("Target")
    ax.set_ylabel("Number of records")
    for container in ax.containers:
        ax.bar_label(container, fmt="%d")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "eda_class_distribution.png", dpi=160)
    plt.close()
    frame[FEATURES + ["ge_r"]].isna().sum().sort_values(ascending=False).to_csv(
        OUTPUT_DIR / "missing_values.csv", header=["missing_count"]
    )


def make_metric_plot(metrics):
    metric_frame = pd.DataFrame(metrics)
    metric_frame.to_csv(OUTPUT_DIR / "model_metrics.csv", index=False)
    long = metric_frame.melt(id_vars="model", value_vars=["accuracy", "f1_macro", "roc_auc"], var_name="metric", value_name="score")
    plt.figure(figsize=(9, 5))
    sns.barplot(data=long, x="model", y="score", hue="metric", palette="Set2")
    plt.ylim(0, 1)
    plt.title("Model comparison on the held-out test set")
    plt.ylabel("Score")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "model_comparison.png", dpi=160)
    plt.close()


def explain_with_shap(cat_model, X_test):
    sample = X_test.sample(n=min(220, len(X_test)), random_state=SEED)
    values = shap.TreeExplainer(cat_model).shap_values(sample)
    if isinstance(values, list):
        values = values[1]
    values = np.asarray(values)
    if values.ndim == 3:
        values = values[:, :, 1]
    shap.summary_plot(values, sample, plot_type="bar", show=False, max_display=10)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "shap_summary.png", dpi=160, bbox_inches="tight")
    plt.close()
    row = sample.iloc[0]
    order = np.argsort(np.abs(values[0]))[::-1]
    pd.DataFrame({"feature": np.array(FEATURES)[order], "shap_value": values[0][order], "value": row.astype(str).values[order]}).to_csv(
        OUTPUT_DIR / "shap_local_values.csv", index=False
    )


def explain_with_lime(cat_model, X_train, X_test):
    categories = {}
    train_codes = pd.DataFrame(index=X_train.index)
    for col in FEATURES:
        values = sorted(X_train[col].fillna("Unknown").astype(str).unique().tolist())
        categories[col] = values
        train_codes[col] = X_train[col].fillna("Unknown").astype(str).map({v: i for i, v in enumerate(values)}).fillna(0).astype(int)

    def decode(values):
        decoded = pd.DataFrame(index=range(len(values)))
        for i, col in enumerate(FEATURES):
            idx = np.clip(np.rint(values[:, i]).astype(int), 0, len(categories[col]) - 1)
            decoded[col] = [categories[col][j] for j in idx]
        return decoded

    def predict_fn(values):
        return cat_model.predict_proba(decode(values))

    explainer = lime.lime_tabular.LimeTabularExplainer(
        train_codes.values,
        feature_names=FEATURES,
        class_names=["Non-pass", "Pass"],
        categorical_features=list(range(len(FEATURES))),
        categorical_names={i: categories[col] for i, col in enumerate(FEATURES)},
        mode="classification",
        discretize_continuous=False,
        random_state=SEED,
    )
    row = X_test.iloc[0].fillna("Unknown").astype(str)
    encoded = [[categories[col].index(row[col]) if row[col] in categories[col] else 0 for col in FEATURES]]
    explanation = explainer.explain_instance(np.asarray(encoded[0]), predict_fn, num_features=len(FEATURES), top_labels=1)
    explanation.save_to_file(str(OUTPUT_DIR / "lime_local.html"))
    label = explanation.available_labels()[0]
    pd.DataFrame(explanation.as_list(label=label), columns=["feature", "weight"]).to_csv(OUTPUT_DIR / "lime_local_values.csv", index=False)


def main():
    ARTIFACT_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)
    X, y, frame = load_and_prepare(DATA_PATH)
    X = X.fillna("Unknown").astype(str)
    make_eda(y, frame)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.20, stratify=y, random_state=SEED)

    rf_search, xgb_search = tune_models(X_train, y_train)
    models = {
        "Random Forest": rf_search.best_estimator_,
        "XGBoost": xgb_search.best_estimator_,
        "CatBoost": make_catboost(),
    }
    metrics = fit_and_score(models, X_train, X_test, y_train, y_test)
    make_metric_plot(metrics)
    metric_frame = pd.DataFrame(metrics).sort_values("f1_macro", ascending=False)
    best_name = metric_frame.iloc[0]["model"]
    best_model = models[best_name]

    pred = np.asarray(best_model.predict(X_test)).reshape(-1)
    cm = confusion_matrix(y_test, pred, labels=[0, 1])
    plt.figure(figsize=(5, 4))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", xticklabels=["Non-pass", "Pass"], yticklabels=["Non-pass", "Pass"])
    plt.title(f"Confusion matrix: {best_name}")
    plt.xlabel("Predicted")
    plt.ylabel("Actual")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "confusion_matrix.png", dpi=160)
    plt.close()
    (OUTPUT_DIR / "classification_report.txt").write_text(classification_report(y_test, pred, zero_division=0), encoding="utf-8")

    explain_with_shap(models["CatBoost"], X_test)
    explain_with_lime(models["CatBoost"], X_train, X_test)

    inference_row = X_test.iloc[[0]]
    actual = "Pass" if y_test.iloc[0] == 1 else "Non-pass"
    inferred_value = int(np.asarray(best_model.predict(inference_row)).reshape(-1)[0])
    inferred = "Pass" if inferred_value == 1 else "Non-pass"
    probability = float(best_model.predict_proba(inference_row)[0, 1])
    (OUTPUT_DIR / "single_inference.txt").write_text(
        f"Left-out test row index: {inference_row.index[0]}\nActual target: {actual}\nPredicted target: {inferred}\nPredicted Pass probability: {probability:.3f}\nInput values:\n{inference_row.to_string()}\n",
        encoding="utf-8",
    )

    bundle = {
        "model": best_model,
        "model_name": best_name,
        "features": FEATURES,
        "categories": {col: sorted(X[col].fillna("Unknown").astype(str).unique().tolist()) for col in FEATURES},
        "class_names": ["Non-pass", "Pass"],
        "target_definition": "Pass if ge_r is A, B, C or S; otherwise Non-pass.",
        "seed": SEED,
    }
    joblib.dump(bundle, ARTIFACT_DIR / "model_bundle.joblib")
    with (ARTIFACT_DIR / "model_bundle.pkl").open("wb") as file:
        pickle.dump(bundle, file, protocol=pickle.HIGHEST_PROTOCOL)
    tuning = {"random_forest_best_params": rf_search.best_params_, "xgboost_best_params": xgb_search.best_params_}
    (OUTPUT_DIR / "tuning_parameters.json").write_text(json.dumps(tuning, indent=2, default=str), encoding="utf-8")
    (OUTPUT_DIR / "run_summary.json").write_text(json.dumps({"rows": len(X), "features": FEATURES, "best_model": best_name, "metrics": metrics}, indent=2, default=str), encoding="utf-8")
    print(metric_frame.to_string(index=False))
    print(f"Best model: {best_name}")


if __name__ == "__main__":
    main()
