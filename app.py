"""Small Streamlit interface for the saved model bundle."""

from pathlib import Path

import pickle
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
BUNDLE_PATH = ROOT / "artifacts" / "model_bundle.pkl"

st.set_page_config(page_title="Sri Lankan GCE A/L Predictor", page_icon="📚")
st.title("Sri Lankan GCE A/L General English Predictor")
st.write("Enter categorical values. The saved model predicts Pass or Non-pass.")
st.caption("This is an educational demo, not an admissions decision tool.")

if not BUNDLE_PATH.exists():
    st.error("The saved model was not found. Run: python3 src/train_model.py")
    st.stop()

with BUNDLE_PATH.open("rb") as file:
    bundle = pickle.load(file)
model = bundle["model"]
features = bundle["features"]
categories = bundle["categories"]

values = {}
for feature in features:
    options = categories[feature]
    default = "Unknown" if "Unknown" in options else options[0]
    values[feature] = st.selectbox(feature, options, index=options.index(default))

if st.button("Predict", type="primary"):
    row = pd.DataFrame([values], columns=features)
    predicted_value = int(model.predict(row)[0])
    prediction = "Pass" if predicted_value == 1 else "Non-pass"
    pass_probability = float(model.predict_proba(row)[0, 1])
    st.subheader(f"Prediction: {prediction}")
    st.metric("Estimated Pass probability", f"{pass_probability:.1%}")
    st.write("The prediction is based on the same categorical fields used during training.")
