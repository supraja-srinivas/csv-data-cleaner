import streamlit as st
import pandas as pd
import re
import csv
import itertools

st.title("CSV Data Cleaner & Data Quality Analyzer")

uploaded_file = st.file_uploader("Upload your CSV file", type=["csv"])

# =========================
# 📌 RECOMMENDATIONS
# =========================
st.subheader("Recommendations for Input File")

st.write("""
❌ Avoid repeated special characters (e.g., !!!, ###)  
❌ Avoid newline characters inside fields  
❌ Avoid duplicate rows  
❌ Avoid special characters in column names  
❌ Avoid inconsistent data types  
❌ Avoid null values in mandatory fields  

✅ Use clean and standardized data before upload  
""")

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)

    st.success("File uploaded successfully!")

    # =========================
    # 🧹 STEP 1: CLEAN COLUMN NAMES
    # =========================
    df.columns = [
        re.sub(r'[^A-Za-z0-9]+', '_', col).strip('_')
        for col in df.columns
    ]

    # =========================
    # 🧹 STEP 2: REMOVE FULLY NULL ROWS
    # =========================
    before_null = len(df)
    df = df.dropna(how='all')
    after_null = len(df)

    # =========================
    # 🧹 STEP 3: REMOVE NEWLINE CHARACTERS
    # =========================

    for col in df.select_dtypes(include='object').columns:
        df[col] = df[col].astype(str).apply(
            lambda x: re.sub(r'[\n\r]+', ' ', x)
        )

    # =========================
    # 🔍 SPECIAL CHARACTER ANALYSIS (BEFORE CLEANING)
    # =========================
    st.subheader("Repeated Special Character Analysis (Before Cleaning)")

    def count_repeated_special_chars(row):
        total = 0
        for val in row:
            if isinstance(val, str):
                matches = re.findall(r'([^A-Za-z0-9\s])\1+', val)
                total += len(matches)
        return total

    special_char_counts = df.apply(count_repeated_special_chars, axis=1)
    problematic_rows = df[special_char_counts > 0]

    if not problematic_rows.empty:
        row_numbers = sorted(set([int(i) + 1 for i in problematic_rows.index.tolist()]))
        st.warning(f"Rows with repeated special characters: {len(problematic_rows)}")
        st.write(f"Row numbers: {row_numbers}")

        display_df = problematic_rows.copy()
        display_df["Repeated_Special_Char_Count"] = special_char_counts[special_char_counts > 0]
        st.dataframe(display_df)
    else:
        st.success("No repeated special character issues found!")

    # =========================
    # 🧹 STEP 4: REMOVE REPEATED SPECIAL CHARACTERS
    # =========================
    def clean_repeated_special_chars(value):
        if isinstance(value, str):
            return re.sub(r'([^A-Za-z0-9\s])\1+', '', value)
        return value

    for col in df.select_dtypes(include='object').columns:
        df[col] = df[col].apply(clean_repeated_special_chars)

    # =========================
    # 🔍 DUPLICATE CHECK AFTER CLEANING
    # =========================
    st.subheader("Duplicate Row Details")

    duplicate_rows = df[df.duplicated(keep=False)]

    if not duplicate_rows.empty:
        duplicate_indices = duplicate_rows.index.to_list()
        row_numbers = sorted(set([int(i) + 1 for i in duplicate_indices]))

        st.warning(f"Duplicate rows found: {duplicate_rows.shape[0]}")
        st.write(f"Duplicate row numbers: {row_numbers}")
        st.dataframe(duplicate_rows)
    else:
        st.success("No duplicate rows found!")

    # =========================
    # 🧹 REMOVE DUPLICATES
    # =========================
    before = len(df)
    df = df.drop_duplicates()
    after = len(df)

    # =========================
    # 🔍 PRIMARY KEY DETECTION
    # =========================
    st.subheader("Primary Key Detection")

    potential_keys = []

    # Single column check
    for col in df.columns:
        if df[col].isnull().sum() == 0 and df[col].nunique() == len(df):
            potential_keys.append((col,))

    # Combination check (2 columns max for performance)
    cols = list(df.columns)
    for combo in itertools.combinations(cols, 2):
        subset = df[list(combo)]
        if subset.isnull().sum().sum() == 0 and subset.drop_duplicates().shape[0] == len(df):
            potential_keys.append(combo)

    if potential_keys:
        st.success("Possible Primary Keys Found:")
        for key in potential_keys:
            st.write(" + ".join(key))
    else:
        st.warning("No primary key found (even with combinations)")

    # =========================
    # 📊 DATA SUMMARY
    # =========================
    st.subheader("Data Summary")
    st.write(f"Total records after cleaning: {len(df)}")

    # =========================
    # 🧹 CLEANING SUMMARY
    # =========================
    st.subheader("Data Cleaning Activities Performed")

    st.write("✔️ Column names cleaned")
    st.write(f"✔️ Fully null rows removed: {before_null - after_null}")
    st.write("✔️ Newline characters removed")
    st.write("✔️ Repeated special characters removed")
    st.write(f"✔️ Duplicate rows removed: {before - after}")

    # =========================
    # 🧹 STEP 1: CLEAN COLUMN NAMES
    # =========================
    df.columns = [
        re.sub(r'[^A-Za-z0-9]+', '_', col).strip('_')
        for col in df.columns
    ]

    # =========================
    # 🧾 SHOW COLUMN NAMES + DATA TYPES
    # =========================
    st.subheader("Column Names & Data Types")
    df = df.convert_dtypes()

    column_info_df = pd.DataFrame({
        "Column Name": df.columns,
        "Data Type": df.dtypes.astype(str)
    })

    st.dataframe(column_info_df, use_container_width=True)

    # =========================
    # 📤 DOWNLOAD
    # =========================
    output_file_name = st.text_input(
        "Enter output file name (without extension)",
        value="processed_file"
    )

    if output_file_name:
        csv_data = df.to_csv(
            sep='|',
            index=False,
            quoting=csv.QUOTE_ALL
        ).encode('utf-8')

        st.download_button(
            label="Download Processed CSV",
            data=csv_data,
            file_name=f"{output_file_name}.csv",
            mime="text/csv"
        )

    # =========================
    # 👀 PREVIEW
    # =========================
    st.subheader("Preview")
    st.dataframe(df.head(50))