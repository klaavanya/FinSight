
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# PROJECT PATH
BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "transactions.csv"
OUTPUT_DIR = BASE_DIR / "outputs"

OUTPUT_DIR.mkdir(exist_ok=True)

# LOAD COMPLETE DATASET
df = pd.read_csv(CSV_PATH)

df.columns = df.columns.str.strip().str.lower()

df["amount"] = pd.to_numeric(
    df["amount"], errors="coerce"
)

df["date"] = pd.to_datetime(
    df["date"], errors="coerce"
)

print("Dataset loaded successfully!")
print("Original dataset shape:", df.shape)

# DATA CLEANING
print("\nDATA CLEANING")

print("Missing values before cleaning:")
print(df.isnull().sum())

print("Duplicate records:", df.duplicated().sum())

df = df.drop_duplicates()
df = df.dropna(subset=["date", "amount"])

print("Records after cleaning:", len(df))

# SAVE CLEANED DATA
df.to_csv(
    OUTPUT_DIR / "cleaned_transactions.csv",
    index=False
)

# CATEGORY ANALYSIS
print("\nCATEGORY ANALYSIS")

category_analysis = df.groupby("category").agg(
    Total_Transactions=("amount", "count"),
    Total_Spending=("amount", "sum"),
    Average_Spending=("amount", "mean")
).round(2)

category_analysis.to_csv(
    OUTPUT_DIR / "category_analysis.csv"
)

plt.figure(figsize=(10, 5))
category_analysis["Total_Spending"].plot(kind="bar")
plt.title("Category-wise Spending")
plt.xlabel("Category")
plt.ylabel("Total Spending")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "category_analysis.png")
plt.close()

# PAYMENT ANALYSIS
print("\nPAYMENT ANALYSIS")

payment_analysis = df.groupby("paymentmethod").agg(
    Transaction_Count=("amount", "count"),
    Total_Amount=("amount", "sum")
).round(2)

payment_analysis.to_csv(
    OUTPUT_DIR / "payment_analysis.csv"
)

plt.figure(figsize=(8, 5))
payment_analysis["Transaction_Count"].plot(
    kind="pie", autopct="%1.1f%%"
)
plt.title("Payment Method Distribution")
plt.ylabel("")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "payment_analysis.png")
plt.close()

# MONTHLY ANALYSIS
print("\nMONTHLY ANALYSIS")

df["month_year"] = df["date"].dt.to_period("M").astype(str)

monthly_analysis = df.groupby("month_year").agg(
    Transaction_Count=("amount", "count"),
    Total_Spending=("amount", "sum")
).round(2)

monthly_analysis.to_csv(
    OUTPUT_DIR / "monthly_analysis.csv"
)

plt.figure(figsize=(10, 5))
monthly_analysis["Total_Spending"].plot(
    kind="line", marker="o"
)
plt.title("Monthly Spending Trend")
plt.xlabel("Month")
plt.ylabel("Total Spending")
plt.xticks(rotation=45)
plt.grid(True)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "monthly_analysis.png")
plt.close()

# LOCATION ANALYSIS
print("\nLOCATION ANALYSIS")

location_analysis = df.groupby("location").agg(
    Transaction_Count=("amount", "count"),
    Total_Spending=("amount", "sum")
).round(2)

location_analysis.to_csv(
    OUTPUT_DIR / "location_analysis.csv"
)

plt.figure(figsize=(10, 5))
location_analysis["Total_Spending"].plot(kind="bar")
plt.title("Location-wise Spending")
plt.xlabel("Location")
plt.ylabel("Total Spending")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "location_analysis.png")
plt.close()

# FINAL REPORT
print("\nFINSIGHT FINAL REPORT")

print("Total Transactions:", len(df))
print("Total Spending:", round(df["amount"].sum(), 2))
print("Average Transaction:", round(df["amount"].mean(), 2))
print("Highest Transaction:", df["amount"].max())
print("Lowest Transaction:", df["amount"].min())

print(
    "Highest Spending Category:",
    category_analysis["Total_Spending"].idxmax()
)

print(
    "Most Used Payment Method:",
    payment_analysis["Transaction_Count"].idxmax()
)

# SAVE SUMMARY
summary = pd.DataFrame({
    "Metric": [
        "Total Transactions",
        "Total Spending",
        "Average Transaction",
        "Highest Transaction",
        "Lowest Transaction"
    ],
    "Value": [
        len(df),
        round(df["amount"].sum(), 2),
        round(df["amount"].mean(), 2),
        df["amount"].max(),
        df["amount"].min()
    ]
})

summary.to_csv(OUTPUT_DIR / "summary_report.csv", index=False)

print("\nAll reports generated successfully!")
print("Check the outputs folder.")


from flask import Flask, render_template, request
import pandas as pd
from pathlib import Path

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = BASE_DIR / "outputs" / "cleaned_transactions.csv"

# LOAD COMPLETE CLEANED DATASET
def load_data():
    df = pd.read_csv(CSV_PATH)

    df["date"] = pd.to_datetime(
        df["date"], errors="coerce"
    )

    df["amount"] = pd.to_numeric(
        df["amount"], errors="coerce"
    )

    return df.dropna(subset=["date", "amount"])


@app.route("/")
def home():
    return render_template("login.html")


@app.route("/dashboard")
def dashboard():

    df = load_data()

    # SUMMARY
    total_transactions = len(df)
    total_spending = round(df["amount"].sum(), 2)
    average_spending = round(df["amount"].mean(), 2)

    # CATEGORY ANALYSIS
    category_data = (
        df.groupby("category")["amount"]
        .sum()
        .round(2)
        .to_dict()
    )

    # PAYMENT ANALYSIS
    payment_data = (
        df["paymentmethod"]
        .value_counts()
        .to_dict()
    )

    # MONTHLY ANALYSIS
    df["month_year"] = df["date"].dt.to_period("M").astype(str)

    monthly_data = (
        df.groupby("month_year")["amount"]
        .sum()
        .round(2)
        .to_dict()
    )

    # LOCATION ANALYSIS
    location_data = (
        df.groupby("location")["amount"]
        .sum()
        .round(2)
        .to_dict()
    )

    # SHOW ALL RECORDS, NOT ONLY FIVE
    transactions = df.sort_values(
        "date", ascending=False
    ).to_dict(orient="records")

    return render_template(
        "dashboard.html",
        total_transactions=total_transactions,
        total_spending=total_spending,
        average_spending=average_spending,
        category_data=category_data,
        payment_data=payment_data,
        monthly_data=monthly_data,
        location_data=location_data,
        transactions=transactions
    )


if __name__ == "__main__":
    app.run(debug=True)
