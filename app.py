
import os
import io
import csv
import sqlite3
import math

from datetime import date, datetime
from functools import wraps

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, send_file
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from openpyxl import Workbook
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4


app = Flask(__name__)
app.secret_key = os.environ.get(
    "SECRET_KEY", "finsight-demo-change-this-key"
)

DB_PATH = os.path.join(app.root_path, "finsight.db")


# DATABASE CONNECTION

def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


# CREATE DATABASE TABLES

def init_db():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS transactions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            entry_date TEXT NOT NULL,
            kind TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            amount REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS budgets(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            month TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS investments(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            asset_type TEXT NOT NULL,
            invested REAL NOT NULL,
            current_value REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS goals(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            target REAL NOT NULL,
            saved REAL NOT NULL,
            due_date TEXT
        );
        """)


init_db()


# LOGIN PROTECTION

def signed_in(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("uid"):
            return redirect(url_for("login"))

        return fn(*args, **kwargs)

    return wrapper


# SAMPLE DEMONSTRATION DATA

def demo_data(uid):

    today = date.today()

    samples = [
        (today.isoformat(), "Income", "Salary",
         "Monthly salary", 35000),

        (today.isoformat(), "Expense", "Food",
         "Groceries and meals", 4500),

        (today.isoformat(), "Expense", "Travel",
         "Bus and fuel", 1800),

        (today.isoformat(), "Expense", "Shopping",
         "Personal shopping", 2500),

        (today.isoformat(), "Expense", "Bills",
         "Phone and electricity", 1600),

        (today.isoformat(), "Expense", "Education",
         "Books and courses", 1200)
    ]

    with db() as con:

        con.executemany("""
            INSERT INTO transactions
            (user_id, entry_date, kind, category, description, amount)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [(uid,) + item for item in samples])

        con.execute("""
            INSERT INTO budgets
            (user_id, month, category, amount)
            VALUES (?, ?, ?, ?)
        """, (uid, today.strftime("%Y-%m"), "Food", 6000))

        con.execute("""
            INSERT INTO budgets
            (user_id, month, category, amount)
            VALUES (?, ?, ?, ?)
        """, (uid, today.strftime("%Y-%m"), "Travel", 3000))

        con.execute("""
            INSERT INTO investments
            (user_id, name, asset_type, invested, current_value)
            VALUES (?, ?, ?, ?, ?)
        """, (
            uid, "Demo Mutual Fund",
            "Mutual Fund", 10000, 11200
        ))

        con.execute("""
            INSERT INTO goals
            (user_id, name, target, saved, due_date)
            VALUES (?, ?, ?, ?, ?)
        """, (
            uid, "Emergency Savings",
            50000, 12000, ""
        ))


# HOME PAGE

@app.route("/")
def home():

    if session.get("uid"):
        return redirect(url_for("dashboard"))

    return redirect(url_for("login"))


# USER REGISTRATION

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or len(password) < 6:

            flash(
                "Enter your name, email and a password "
                "with at least 6 characters."
            )

        else:

            try:

                with db() as con:

                    cur = con.execute("""
                        INSERT INTO users
                        (name, email, password_hash)
                        VALUES (?, ?, ?)
                    """, (
                        name,
                        email,
                        generate_password_hash(password)
                    ))

                    uid = cur.lastrowid

                demo_data(uid)

                session["uid"] = uid
                session["name"] = name

                flash("Account created successfully.")

                return redirect(url_for("dashboard"))

            except sqlite3.IntegrityError:

                flash(
                    "That email is already registered. "
                    "Please log in."
                )

    return render_template("auth.html", mode="register")


# USER LOGIN

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        with db() as con:

            user = con.execute(
                "SELECT * FROM users WHERE email = ?",
                (email,)
            ).fetchone()

        if user and check_password_hash(
            user["password_hash"], password
        ):

            session["uid"] = user["id"]
            session["name"] = user["name"]

            return redirect(url_for("dashboard"))

        flash("Email or password is incorrect.")

    return render_template("auth.html", mode="login")


# LOGOUT

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# FINANCIAL DASHBOARD

@app.route("/dashboard")
@signed_in
def dashboard():

    uid = session["uid"]
    month = date.today().strftime("%Y-%m")

    with db() as con:

        transactions = con.execute("""
            SELECT * FROM transactions
            WHERE user_id = ?
            ORDER BY entry_date DESC, id DESC
        """, (uid,)).fetchall()

        budgets = con.execute("""
            SELECT * FROM budgets
            WHERE user_id = ? AND month = ?
        """, (uid, month)).fetchall()

        investments = con.execute("""
            SELECT * FROM investments
            WHERE user_id = ?
        """, (uid,)).fetchall()

        goals = con.execute("""
            SELECT * FROM goals
            WHERE user_id = ?
        """, (uid,)).fetchall()

    income = sum(
        r["amount"] for r in transactions
        if r["kind"] == "Income"
    )

    expenses = sum(
        r["amount"] for r in transactions
        if r["kind"] == "Expense"
    )

    invested = sum(r["invested"] for r in investments)
    current = sum(r["current_value"] for r in investments)

    categories = {}

    for r in transactions:

        if r["kind"] == "Expense":

            categories[r["category"]] = (
                categories.get(r["category"], 0) + r["amount"]
            )

    budget_view = []

    for b in budgets:

        spent = categories.get(b["category"], 0)

        pct = (
            min(100, round(spent / b["amount"] * 100))
            if b["amount"] else 0
        )

        budget_view.append({
            "category": b["category"],
            "amount": b["amount"],
            "spent": spent,
            "pct": pct,
            "over": spent > b["amount"]
        })

    score = (
        max(
            0,
            min(
                100,
                round(50 + (income - expenses) / income * 50)
            )
        )
        if income else 0
    )

    insights = []

    if income and expenses > income:

        insights.append(
            "Your recorded expenses are higher than your income."
        )

    if any(x["over"] for x in budget_view):

        insights.append(
            "One or more categories have exceeded the monthly budget."
        )

    if current > invested:

        insights.append(
            "Your manually entered investment values show "
            "a positive recorded difference."
        )

    if not insights:

        insights.append(
            "Continue recording your income and expenses "
            "to receive more useful summaries."
        )

    return render_template(
        "dashboard.html",
        transactions=transactions[:12],
        income=income,
        expenses=expenses,
        balance=income - expenses,
        invested=invested,
        current=current,
        goals=goals,
        budget_view=budget_view,
        score=score,
        insights=insights,
        labels=list(categories.keys()),
        values=list(categories.values())
    )


# ADD TRANSACTION

@app.route("/transaction/add", methods=["POST"])
@signed_in
def transaction_add():

    try:

        amount = float(request.form["amount"])
        kind = request.form["kind"]
        entry_date = request.form["entry_date"]
        category = request.form["category"].strip()
        description = request.form.get("description", "").strip()

        date.fromisoformat(entry_date)

        if (
            not math.isfinite(amount)
            or amount <= 0
            or kind not in ("Income", "Expense")
            or not category
        ):
            raise ValueError()

        with db() as con:

            con.execute("""
                INSERT INTO transactions
                (user_id, entry_date, kind, category, description, amount)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                session["uid"],
                entry_date,
                kind,
                category,
                description,
                amount
            ))

        flash("Transaction saved successfully.")

    except (ValueError, KeyError):

        flash("Please enter valid transaction details.")

    return redirect(url_for("dashboard"))


# DELETE TRANSACTION

@app.route("/transaction/delete/<int:tid>", methods=["POST"])
@signed_in
def transaction_delete(tid):

    with db() as con:

        con.execute("""
            DELETE FROM transactions
            WHERE id = ? AND user_id = ?
        """, (tid, session["uid"]))

    flash("Transaction deleted.")

    return redirect(url_for("dashboard"))


# ADD BUDGET

@app.route("/budget/add", methods=["POST"])
@signed_in
def budget_add():

    try:

        amount = float(request.form["amount"])
        month = request.form["month"]
        category = request.form["category"].strip()

        if (
            not math.isfinite(amount)
            or amount <= 0
            or not category
        ):
            raise ValueError()

        if len(month) != 7 or month[4] != "-":
            raise ValueError()

        with db() as con:

            con.execute("""
                INSERT INTO budgets
                (user_id, month, category, amount)
                VALUES (?, ?, ?, ?)
            """, (
                session["uid"],
                month,
                category,
                amount
            ))

        flash("Budget saved successfully.")

    except (ValueError, KeyError):

        flash("Please enter a valid budget amount.")

    return redirect(url_for("dashboard"))


# ADD INVESTMENT

@app.route("/investment/add", methods=["POST"])
@signed_in
def investment_add():

    try:

        invested = float(request.form["invested"])
        current_value = float(request.form["current_value"])

        name = request.form["name"].strip()
        asset_type = request.form["asset_type"].strip()

        if (
            not math.isfinite(invested)
            or not math.isfinite(current_value)
            or invested < 0
            or current_value < 0
            or not name
            or not asset_type
        ):
            raise ValueError()

        with db() as con:

            con.execute("""
                INSERT INTO investments
                (user_id, name, asset_type, invested, current_value)
                VALUES (?, ?, ?, ?, ?)
            """, (
                session["uid"],
                name,
                asset_type,
                invested,
                current_value
            ))

        flash("Investment saved successfully.")

    except (ValueError, KeyError):

        flash("Please enter valid investment values.")

    return redirect(url_for("dashboard"))


# ADD SAVINGS GOAL

@app.route("/goal/add", methods=["POST"])
@signed_in
def goal_add():

    try:

        target = float(request.form["target"])
        saved = float(request.form["saved"])

        name = request.form["name"].strip()
        due_date = request.form.get("due_date", "").strip()

        if (
            not math.isfinite(target)
            or not math.isfinite(saved)
            or target <= 0
            or saved < 0
            or not name
        ):
            raise ValueError()

        if due_date:
            date.fromisoformat(due_date)

        with db() as con:

            con.execute("""
                INSERT INTO goals
                (user_id, name, target, saved, due_date)
                VALUES (?, ?, ?, ?, ?)
            """, (
                session["uid"],
                name,
                target,
                saved,
                due_date
            ))

        flash("Savings goal saved successfully.")

    except (ValueError, KeyError):

        flash("Please enter valid goal values.")

    return redirect(url_for("dashboard"))



# IMPORT CSV FILE

@app.route("/csv/import", methods=["POST"])
@signed_in
def csv_import():

    f = request.files.get("dataset")

    if not f or not f.filename:
        flash("Please select a CSV file.")
        return redirect(url_for("dashboard"))

    if not f.filename.lower().endswith(".csv"):
        flash("Please upload a CSV file.")
        return redirect(url_for("dashboard"))

    try:
        content = f.stream.read().decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(content))

        if not reader.fieldnames:
            raise ValueError("Empty CSV")

        reader.fieldnames = [
            (name or "").strip().lower()
            for name in reader.fieldnames
        ]

        required = {
            "date",
            "description",
            "amount",
            "category",
            "transactiontype"
        }

        if not required.issubset(set(reader.fieldnames)):
            flash("Required CSV columns are missing.")
            return redirect(url_for("dashboard"))

        imported = 0
        skipped = 0

        with db() as con:

            for row in reader:

                try:
                    raw_date = (row.get("date") or "").strip()

                    # Convert DD-MM-YYYY into YYYY-MM-DD
                    try:
                        entry_date = datetime.strptime(
                            raw_date, "%d-%m-%Y"
                        ).date().isoformat()
                    except ValueError:
                        entry_date = date.fromisoformat(
                            raw_date
                        ).isoformat()

                    description = (
                        row.get("description") or ""
                    ).strip()

                    category = (
                        row.get("category") or ""
                    ).strip()

                    transaction_type = (
                        row.get("transactiontype") or ""
                    ).strip().lower()

                    amount = float(row.get("amount", ""))

                    # Convert transaction type
                    if transaction_type in ("debit", "expense"):
                        kind = "Expense"

                    elif transaction_type in ("credit", "income"):
                        kind = "Income"

                    else:
                        skipped += 1
                        continue

                    if (
                        not math.isfinite(amount)
                        or amount <= 0
                        or not category
                    ):
                        skipped += 1
                        continue

                    con.execute("""
                        INSERT INTO transactions
                        (user_id, entry_date, kind,
                         category, description, amount)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        session["uid"],
                        entry_date,
                        kind,
                        category,
                        description,
                        amount
                    ))

                    imported += 1

                except (ValueError, TypeError):
                    skipped += 1

        flash(
            f"Imported {imported} records. "
            f"Skipped {skipped} invalid rows."
        )

    except (UnicodeDecodeError, csv.Error, ValueError):
        flash("Unable to process the CSV file. Check its format.")

    return redirect(url_for("dashboard"))


# EXPORT EXCEL REPORT

@app.route("/export/excel")
@signed_in
def export_excel():

    with db() as con:

        rows = con.execute("""
            SELECT entry_date, kind, category, description, amount
            FROM transactions
            WHERE user_id = ?
            ORDER BY entry_date
        """, (session["uid"],)).fetchall()

    wb = Workbook()
    ws = wb.active

    ws.title = "Transactions"

    ws.append([
        "Date",
        "Type",
        "Category",
        "Description",
        "Amount"
    ])

    for row in rows:

        ws.append(list(row))

    output = io.BytesIO()

    wb.save(output)

    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name="FinSight_Report.xlsx",
        mimetype=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )
    )


# EXPORT PDF REPORT

@app.route("/export/pdf")
@signed_in
def export_pdf():

    with db() as con:

        rows = con.execute("""
            SELECT entry_date, kind, category, description, amount
            FROM transactions
            WHERE user_id = ?
            ORDER BY entry_date
        """, (session["uid"],)).fetchall()

    output = io.BytesIO()

    pdf = canvas.Canvas(output, pagesize=A4)

    page_width, page_height = A4

    y = page_height - 40

    pdf.setFont("Helvetica-Bold", 17)

    pdf.drawString(
        45, y,
        "FinSight - Financial Report"
    )

    y -= 25

    pdf.setFont("Helvetica", 10)

    pdf.drawString(
        45, y,
        "Account: " + session.get("name", "")
    )

    y -= 30

    pdf.setFont("Helvetica-Bold", 9)

    pdf.drawString(
        45, y,
        "DATE       TYPE       CATEGORY       DESCRIPTION       AMOUNT"
    )

    y -= 20

    pdf.setFont("Helvetica", 8)

    for row in rows:

        line = (
            f"{row['entry_date']}  "
            f"{row['kind']}  "
            f"{row['category']}  "
            f"{(row['description'] or '')[:22]}  "
            f"Rs.{row['amount']:.2f}"
        )

        pdf.drawString(45, y, line[:110])

        y -= 17

        if y < 55:

            pdf.showPage()

            y = page_height - 40

            pdf.setFont("Helvetica", 8)

    pdf.save()

    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name="FinSight_Report.pdf",
        mimetype="application/pdf"
    )


# RUN FLASK APPLICATION

if __name__ == "__main__":

    app.run(debug=True)
