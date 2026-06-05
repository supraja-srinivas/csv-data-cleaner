import streamlit as st
import pandas as pd
import re
import csv
import numpy as np

st.set_page_config(page_title="Self Service Data Quality Platform", layout="wide")

st.title("Self Service Data Quality Platform")

uploaded_file = st.file_uploader(
    "Upload your file",
    type=["csv", "xlsx", "xls", "json", "xml"]
)

if uploaded_file is not None:

    try:
        # =========================
        # FILE READ
        # =========================
        file_name = uploaded_file.name
        file_type = file_name.split('.')[-1].lower()

        st.write("Uploaded File:", file_name)

        if file_type == "csv":
            df = pd.read_csv(uploaded_file)

        elif file_type == "xlsx":
            df = pd.read_excel(
                uploaded_file,
                engine="openpyxl"
            )

        elif file_type == "xls":
            df = pd.read_excel(
                uploaded_file,
                engine="xlrd"
            )

        elif file_type == "json":
            df = pd.read_json(uploaded_file)

        elif file_type == "xml":
            df = pd.read_xml(uploaded_file)

        else:
            st.error("Unsupported file type")
            st.stop()

    except Exception as e:
        st.error(f"Error reading file: {str(e)}")
        st.stop()

    st.success(f"{file_type.upper()} file uploaded successfully!")

    # =========================
    # CLEAN COLUMN NAMES
    # =========================
    df.columns = [
        re.sub(r'[^A-Za-z0-9]+', '_', str(col)).strip('_')
        for col in df.columns
    ]

    total_records = len(df)

    # =========================
    # BLANK VALUE CHECK
    # =========================
    st.subheader("Blank Value Analysis")

    blank_issues = []

    for col in df.columns:
        for idx, val in df[col].items():

            if pd.isna(val):

                blank_issues.append({
                    "Row": idx + 1,
                    "Column": col,
                    "Issue": "Null"
                })

            elif isinstance(val, str) and val.strip() == "":

                blank_issues.append({
                    "Row": idx + 1,
                    "Column": col,
                    "Issue": "Blank"
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
    df = df.dropna(how="all")
    after_null = len(df)

    # =========================
    # REMOVE NEWLINES
    # =========================
    object_cols = df.select_dtypes(include=["object"]).columns

    for col in object_cols:
        df[col] = df[col].astype(str).str.replace(
            r'[\n\r]+',
            ' ',
            regex=True
        )

    # =========================
    # SPECIAL CHARACTER CHECK
    # =========================
    st.subheader("Repeated Special Character Analysis")

    issues = []

    for idx, row in df.iterrows():

        for col in df.columns:

            value = row[col]

            if isinstance(value, str):

                matches = re.findall(
                    r'([^A-Za-z0-9\s])\1+',
                    value
                )

                for match in matches:
                    issues.append({
                        "Row": idx + 1,
                        "Column": col,
                        "Character": match
                    })

    if issues:

        st.warning(
            f"Repeated special character issues found: {len(issues)}"
        )

        st.dataframe(pd.DataFrame(issues))

        clean_choice = st.radio(
            "Remove repeated special characters?",
            ["No", "Yes"]
        )

        if clean_choice == "Yes":

            for col in object_cols:

                df[col] = df[col].apply(
                    lambda x: re.sub(
                        r'([^A-Za-z0-9\s])\1+',
                        '',
                        str(x)
                    )
                )

            st.success("Repeated special characters removed.")

    else:
        st.success("No repeated special character issues found.")

    # =========================
    # DUPLICATE CHECK
    # =========================
    st.subheader("Duplicate Check")

    duplicate_rows = df[df.duplicated(keep=False)]

    duplicate_count = len(duplicate_rows)

    if duplicate_count > 0:
        st.warning(f"Duplicate rows found: {duplicate_count}")
        st.dataframe(duplicate_rows)
    else:
        st.success("No duplicate rows found.")

    before_duplicates = len(df)

    df = df.drop_duplicates()

    after_duplicates = len(df)

    df = df.reset_index(drop=True)

    # =========================
    # OUTLIER DETECTION
    # =========================
    st.subheader("Outlier Detection")

    outlier_rows = []

    numeric_cols = df.select_dtypes(include=np.number).columns

    for col in numeric_cols:

        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)

        IQR = Q3 - Q1

        lower_bound = Q1 - (1.5 * IQR)
        upper_bound = Q3 + (1.5 * IQR)

        for idx, value in df[col].items():

            if pd.notna(value):

                if value < lower_bound or value > upper_bound:

                    outlier_rows.append({
                        "Row": idx + 1,
                        "Column": col,
                        "Value": value
                    })

    if outlier_rows:

        st.warning(
            f"Outliers detected: {len(outlier_rows)}"
        )

        st.dataframe(pd.DataFrame(outlier_rows))

    else:
        st.success("No outliers detected.")

    # =========================
    # DATA TYPE VALIDATION
    # =========================
    st.subheader("Data Type Validation")

    expected_types = {}

    for col in df.columns:

        expected_types[col] = st.selectbox(
            f"{col}",
            [
                "Auto Detect",
                "String",
                "Integer",
                "Float",
                "Date"
            ],
            key=col
        )

    validation_issues = []

    for col in df.columns:

        expected = expected_types[col]

        if expected == "Auto Detect":
            continue

        for idx, value in df[col].items():

            if pd.isna(value):
                continue

            try:

                if expected == "Integer":
                    int(value)

                elif expected == "Float":
                    float(value)

                elif expected == "Date":
                    pd.to_datetime(value)

                elif expected == "String":
                    str(value)

            except Exception:

                validation_issues.append({
                    "Row": idx + 1,
                    "Column": col,
                    "Value": value,
                    "Expected Type": expected
                })

    if validation_issues:

        st.warning(
            f"Data type validation issues: {len(validation_issues)}"
        )

        st.dataframe(pd.DataFrame(validation_issues))

    else:
        st.success("No data type validation issues found.")

    # =========================
    # DATA QUALITY SCORES
    # =========================
    st.subheader("Data Quality Score Breakdown")

    total_records = max(total_records, 1)

    blank_score = round(
        max(0, 100 - (len(blank_issues) / total_records * 100)),
        2
    )

    duplicate_score = round(
        max(0, 100 - (duplicate_count / total_records * 100)),
        2
    )

    special_score = round(
        max(0, 100 - (len(issues) / total_records * 100)),
        2
    )

    datatype_score = round(
        max(0, 100 - (len(validation_issues) / total_records * 100)),
        2
    )

    outlier_score = round(
        max(0, 100 - (len(outlier_rows) / total_records * 100)),
        2
    )

    overall_score = round(
        (
            blank_score +
            duplicate_score +
            special_score +
            datatype_score +
            outlier_score
        ) / 5,
        2
    )

    score_df = pd.DataFrame({
        "Quality Check": [
            "Blank Values",
            "Duplicates",
            "Special Characters",
            "Data Type Issues",
            "Outliers"
        ],
        "Score": [
            blank_score,
            duplicate_score,
            special_score,
            datatype_score,
            outlier_score
        ]
    })

    st.dataframe(score_df, use_container_width=True)

    # =========================
    # OVERALL SCORE
    # =========================
    st.subheader("Overall Data Quality Score")

    st.metric(
        label="Quality Score",
        value=f"{overall_score}/100"
    )

    # =========================
    # SUMMARY
    # =========================
    st.subheader("Data Summary")

    st.write(f"Total Records: {len(df)}")
    st.write(f"Columns: {len(df.columns)}")

    # =========================
    # DOWNLOAD
    # =========================
    st.subheader("Download Processed File")

    output_name = st.text_input(
        "Output File Name",
        "processed_file"
    )

    csv_output = df.to_csv(
        sep="|",
        index=False,
        quoting=csv.QUOTE_ALL
    ).encode("utf-8")

    st.download_button(
        label="Download CSV",
        data=csv_output,
        file_name=f"{output_name}.csv",
        mime="text/csv"
    )

    # =========================
    # PREVIEW
    # =========================
    st.subheader("Preview")

    st.dataframe(
        df.head(50),
        use_container_width=True
    )