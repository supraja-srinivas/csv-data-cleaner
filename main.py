import streamlit as st
import pandas as pd
import re
import csv
import itertools
import numpy as np

st.set_page_config(page_title="Self Service Data Quality Platform", layout="wide")

st.title("Self Service Data Quality Platform")

uploaded_file = st.file_uploader(
    "Upload your file",
    type=["csv", "xlsx", "json", "xml"]
)

if uploaded_file is not None:

    # =========================
    # FILE READ
    # =========================
    file_type = uploaded_file.name.split('.')[-1].lower()

    if file_type == "csv":
        df = pd.read_csv(uploaded_file)
    elif file_type in ["xlsx", "xls"]:
        df = pd.read_excel(uploaded_file)
    elif file_type == "json":
        df = pd.read_json(uploaded_file)
    elif file_type == "xml":
        df = pd.read_xml(uploaded_file)
    else:
        st.error("Unsupported file type")
        st.stop()

    st.success(f"{file_type.upper()} file uploaded successfully!")

    # =========================
    # CLEAN COLUMN NAMES
    # =========================
    df.columns = [re.sub(r'[^A-Za-z0-9]+', '_', col).strip('_') for col in df.columns]

    total_records = len(df)

    # =========================
    # BLANK VALUE CHECK
    # =========================
    st.subheader("Blank Value Analysis")

    blank_issues = []

    for col in df.columns:
        for idx, val in df[col].items():
            if pd.isna(val) or str(val).strip() == "":
                blank_issues.append({
                    "Row": idx + 1,
                    "Column": col
                })

    if blank_issues:
        st.warning(f"Blank values found: {len(blank_issues)}")
        st.dataframe(pd.DataFrame(blank_issues))
    else:
        st.success("No blank values found!")

    # =========================
    # REMOVE FULL NULL ROWS
    # =========================
    before_null = len(df)
    df = df.dropna(how='all')
    after_null = len(df)

    # =========================
    # REMOVE NEWLINES
    # =========================
    for col in df.select_dtypes(include='object').columns:
        df[col] = df[col].astype(str).apply(lambda x: re.sub(r'[\n\r]+', ' ', x))

    # =========================
    # SPECIAL CHAR DETECTION
    # =========================
    st.subheader("Repeated Special Character Analysis")

    repeated_char_cleaned = False
    issues = []

    for idx, row in df.iterrows():
        for col in df.columns:
            val = row[col]
            if isinstance(val, str):
                matches = re.findall(r'([^A-Za-z0-9\s])\1+', val)
                for match in matches:
                    issues.append({"Row": idx + 1, "Column": col, "Character": match})

    if issues:
        st.warning(f"Special character issues: {len(issues)}")
        st.dataframe(pd.DataFrame(issues))

        user_choice = st.radio("Remove repeated special characters?", ["No", "Yes"])

        if user_choice == "Yes":
            for col in df.select_dtypes(include='object').columns:
                df[col] = df[col].apply(lambda x: re.sub(r'([^A-Za-z0-9\s])\1+', '', x))
            repeated_char_cleaned = True

    else:
        st.success("No special character issues")

    # =========================
    # DUPLICATE CHECK
    # =========================
    duplicate_rows = df[df.duplicated(keep=False)]
    duplicate_count = len(duplicate_rows)

    st.subheader("Duplicate Check")
    if duplicate_count > 0:
        st.warning(f"Duplicate rows: {duplicate_count}")
        st.dataframe(duplicate_rows)
    else:
        st.success("No duplicates")

    before = len(df)
    df = df.drop_duplicates()
    after = len(df)

    # ✅ FIX: Reset index so row numbers match UI
    df = df.reset_index(drop=True)

    # =========================
    # OUTLIER DETECTION (IQR)
    # =========================
    st.subheader("Outlier Detection")

    outlier_rows = []

    numeric_cols = df.select_dtypes(include=np.number).columns

    for col in numeric_cols:
        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1

        lower = Q1 - 1.5 * IQR
        upper = Q3 + 1.5 * IQR

        for idx, val in df[col].items():
            if pd.notna(val) and (val < lower or val > upper):
                outlier_rows.append({
                    "Row": idx + 1,
                    "Column": col,
                    "Value": val
                })

    if outlier_rows:
        st.warning(f"Outliers found: {len(outlier_rows)}")
        st.dataframe(pd.DataFrame(outlier_rows))
    else:
        st.success("No outliers detected")

    # =========================
    # DATA TYPE VALIDATION
    # =========================
    st.subheader("Data Type Validation")

    expected_types = {}

    for col in df.columns:
        expected_types[col] = st.selectbox(
            col,
            ["Auto Detect", "String", "Integer", "Float", "Date"],
            key=col
        )

    validation_issues = []

    for col in df.columns:
        expected = expected_types[col]

        if expected == "Auto Detect":
            continue

        for idx, val in df[col].items():
            if pd.isna(val):
                continue

            try:
                if expected == "Integer":
                    int(val)
                elif expected == "Float":
                    float(val)
                elif expected == "Date":
                    pd.to_datetime(val)
                elif expected == "String":
                    str(val)
            except:
                validation_issues.append({
                    "Row": idx + 1,
                    "Column": col,
                    "Value": val,
                    "Expected": expected
                })

    if validation_issues:
        st.warning(f"Data type issues: {len(validation_issues)}")
        st.dataframe(pd.DataFrame(validation_issues))
    else:
        st.success("No data type issues")

    # =========================
    # DATA QUALITY SCORE (SECTION-WISE)
    # =========================
    st.subheader("Data Quality Score Breakdown")

    # Avoid division by zero
    total_records = max(1, total_records)

    # Individual Scores
    blank_score = max(0, 100 - (len(blank_issues) / total_records) * 100)
    duplicate_score = max(0, 100 - (duplicate_count / total_records) * 100)
    special_char_score = max(0, 100 - (len(issues) / total_records) * 100)
    datatype_score = max(0, 100 - (len(validation_issues) / total_records) * 100)
    outlier_score = max(0, 100 - (len(outlier_rows) / total_records) * 100)

    # Round scores
    blank_score = round(blank_score, 2)
    duplicate_score = round(duplicate_score, 2)
    special_char_score = round(special_char_score, 2)
    datatype_score = round(datatype_score, 2)
    outlier_score = round(outlier_score, 2)

    # Total Score (average)
    total_score = round(
        (blank_score + duplicate_score + special_char_score + datatype_score + outlier_score) / 5,
        2
    )

    # =========================
    # DISPLAY SCORES
    # =========================
    score_df = pd.DataFrame({
        "Quality Check": [
            "Blank Values",
            "Duplicates",
            "Special Characters",
            "Data Type Issues",
            "Outliers"
        ],
        "Score (0-100)": [
            blank_score,
            duplicate_score,
            special_char_score,
            datatype_score,
            outlier_score
        ]
    })

    st.dataframe(score_df, use_container_width=True)

    # =========================
    # FINAL SCORE
    # =========================
    st.subheader("Overall Data Quality Score")
    st.metric("Score", f"{total_score} / 100")

    # =========================
    # SUMMARY
    # =========================
    st.subheader("Data Summary")
    st.write(f"Total records: {len(df)}")

    # =========================
    # DOWNLOAD
    # =========================
    output_file_name = st.text_input("Enter output file name", "processed_file")

    if output_file_name:
        csv_data = df.to_csv(sep='|', index=False, quoting=csv.QUOTE_ALL).encode('utf-8')

        st.download_button(
            "Download Processed CSV",
            csv_data,
            f"{output_file_name}.csv"
        )

    # =========================
    # PREVIEW
    # =========================
    st.subheader("Preview")
    st.dataframe(df.head(50))