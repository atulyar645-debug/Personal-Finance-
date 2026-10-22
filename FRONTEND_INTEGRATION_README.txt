FinTrack frontend + Flask integration (local development)

WHAT CHANGED
- The updated dashboard HTML is served by Flask at http://127.0.0.1:5000/ (not opened as a standalone file).
- Login/register call the Flask API; login accepts username or email.
- Expenses/incomes, budgets, savings goals, and notifications are connected to existing API routes.
- Expense category inference remains handled by the backend when the category is blank.
- Added a DELETE route for savings goals.
- Kept the uploaded UI design and its investment/tax calculators; tax estimator results are still client-side unless saved through the existing taxes API.

RUN
1. Back up your current FinTrack folder first.
2. Extract this ZIP; open the FinTrack folder in VS Code.
3. Keep your own existing MySQL password/config if it differs; app/__init__.py still uses the project's local configuration.
4. Activate your existing virtual environment and install requirements if needed: pip install -r requirements.txt
5. Ensure MySQL is running and finance_app tables exist.
6. Run: python run.py
7. Open: http://127.0.0.1:5000/

IMPORTANT
- Do not double-click index.html. It must be served by Flask so /login and other API routes use the same origin.
- This is not production-secure authentication: APIs use a user_id in URL/body and do not yet enforce server-side session authorization. Use only for local project testing.
- Please test with a new test account first, then verify that expenses/income persist after logout/login.
