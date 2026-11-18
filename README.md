# FinSight - Personal Finance & Investment Intelligence Platform

## Run on Windows using VS Code
1. Extract this ZIP.
2. In VS Code choose File > Open Folder and select `FinSight_Project`.
3. Open Terminal > New Terminal.
4. Run these commands one by one:

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
py app.py
```

If PowerShell blocks activation, run:
`Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`
then activate again.

5. Open `http://127.0.0.1:5000` in Chrome.
6. Select Create an account. The first account receives sample demonstration records.

## Dataset
No external dataset is required for the core application. The user's own transactions, budgets, investments and goals are entered through the website forms and stored in SQLite (`finsight.db`). A sample CSV is provided in `static/sample_transactions.csv`. CSV columns must be:
`date,kind,category,description,amount`
The `kind` field must be `Income` or `Expense`.

## Included modules
1. Authentication with hashed passwords
2. Income and expense recording
3. Monthly category budgets and overspending display
4. Investment entries and simple gain/loss calculation
5. Savings goals and progress display
6. Spending chart, rule-based health score and recommendations
7. CSV import and PDF/Excel reports

## Database
SQLite creates `finsight.db` automatically when the app starts. Tables: users, transactions, budgets, investments, goals.

## Academic project limitations
This is a local academic demonstration, not a production financial service. Investments are manually entered; live market data is not connected. The health score and insights are simple rule-based calculations, not a trained machine-learning model or financial advice. For real deployment, add CSRF protection, stronger secrets, HTTPS, rate limiting, backups, and security review.
