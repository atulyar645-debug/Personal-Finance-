from app import db
from app.email_utils import send_email_notification
from calendar import month
from werkzeug.security import generate_password_hash, check_password_hash

from flask import Blueprint, current_app, request, jsonify, render_template
from app.db import get_db_connection

from datetime import date, date, datetime
from decimal import Decimal, InvalidOperation

from app.transaction_categorization import categorize_transaction, get_category
from app.finance_calculations import calculate_finances, calculate_budget, calculate_savings_goal
from app.spending_insights import spending_insights
from app.investment_suggestions import suggest_investment


def is_valid_positive_number(value):
    try:
        value = Decimal(str(value))
        return value > 0
    except (InvalidOperation, ValueError, TypeError):
        return False


def is_valid_non_negative_number(value):
    try:
        value = Decimal(str(value))
        return value >= 0
    except (InvalidOperation, ValueError, TypeError):
        return False


def is_valid_date(date_string):
    try:
        datetime.strptime(date_string, "%Y-%m-%d")
        return True
    except (ValueError, TypeError):
        return False


def is_valid_month(month_string):
    try:
        datetime.strptime(month_string, "%Y-%m")
        return True
    except (ValueError, TypeError):
        return False

main = Blueprint("main", __name__)


@main.route("/")
def home():
    return render_template("index.html")



@main.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "A valid JSON body is required"}), 400

    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if not all(
        isinstance(value, str) and value.strip()
        for value in (username, email, password)
    ):
        return jsonify({"error": "Username, email and password are required"}), 400

    username = username.strip()
    email = email.strip()

    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    db = get_db_connection()
    cursor = db.cursor()

    try:
        cursor.execute(
            "SELECT id FROM users WHERE username = %s OR email = %s",
            (username, email)
        )

        if cursor.fetchone():
            return jsonify({
                "error": "Username or email already exists"
            }), 409

        hashed_password = generate_password_hash(password)

        cursor.execute(
            """
            INSERT INTO users (username, email, password)
            VALUES (%s, %s, %s)
            """,
            (username, email, hashed_password)
        )

        db.commit()

        return jsonify({
            "message": "User registered successfully"
        }), 201

    except Exception:
        db.rollback()
        current_app.logger.exception("Registration failed")
        return jsonify({"error": "Registration failed"}), 500

    finally:
        cursor.close()
        db.close()


@main.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "A valid JSON body is required"}), 400

    username = data.get("username")
    password = data.get("password")

    if not isinstance(username, str) or not username.strip() or not isinstance(password, str) or not password:
        return jsonify({
            "error": "Username and password are required"
        }), 400

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT id, username, email, password
            FROM users
            WHERE username = %s OR email = %s
            """,
            (username.strip(), username.strip())
        )

        user = cursor.fetchone()

        if not user:
            return jsonify({
                "error": "Invalid username or password"
            }), 401

        stored_password = user["password"]

        # Support existing accounts that still have plain-text passwords.
        try:
            password_matches = check_password_hash(
                stored_password, password
            )
        except (TypeError, ValueError):
            password_matches = False

        if not password_matches and stored_password == password:
            # Upgrade the old password to a secure hash after successful login.
            hashed_password = generate_password_hash(password)
            cursor.execute(
                "UPDATE users SET password = %s WHERE id = %s",
                (hashed_password, user["id"])
            )
            db.commit()
            password_matches = True

        if not password_matches:
            return jsonify({
                "error": "Invalid username or password"
            }), 401

        return jsonify({
            "message": "Login successful",
            "user": {
                "id": user["id"],
                "username": user["username"],
                "email": user["email"]
            }
        }), 200

    except Exception:
        db.rollback()
        current_app.logger.exception("Login failed")
        return jsonify({"error": "Login failed"}), 500

    finally:
        cursor.close()
        db.close()


@main.route("/expenses", methods=["POST"])
def add_expense():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "A valid JSON body is required"}), 400

    user_id = data.get("user_id")
    category = data.get("category")
    amount = data.get("amount")
    expense_date = data.get("date")
    description = data.get("description", "")

    if user_id is None or amount is None or not expense_date:
        return jsonify({
            "error": "user_id, amount and date are required"
        }), 400
    if not isinstance(description, str):
        return jsonify({"error": "description must be a string"}), 400

    # Backwards compatible: keep an explicitly supplied category; infer it if omitted/blank.
    if not isinstance(category, str) or not category.strip():
        category = categorize_transaction(description)
    else:
        category = category.strip()

    if not is_valid_positive_number(amount):
        return jsonify({
            "error": "amount must be a positive number"
    }), 400

    if not is_valid_date(expense_date):
        return jsonify({
            "error": "date must be in YYYY-MM-DD format"
    }), 400

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute(
        """
        INSERT INTO expenses
        (user_id, category, amount, date, description)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (user_id, category, amount, expense_date, description)
    )

    
    db.commit()
    expense_id = cursor.lastrowid

    # Send an email when this expense crosses the monthly category budget.
    try:
        month_key = expense_date[:7]

        cursor.execute(
            "SELECT email FROM users WHERE id = %s",
            (user_id,)
        )
        user_row = cursor.fetchone()

        cursor.execute(
            """
            SELECT limit_amount
            FROM budgets
            WHERE user_id = %s AND category = %s AND month = %s
            """,
            (user_id, category, month_key)
        )
        budget_row = cursor.fetchone()

        if user_row and user_row[0] and budget_row:
            limit_amount = Decimal(str(budget_row[0]))

            cursor.execute(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM expenses
                WHERE user_id = %s
                AND category = %s
                AND DATE_FORMAT(date, '%Y-%m') = %s
                """,
                (user_id, category, month_key)
            )
            spent_after = Decimal(str(cursor.fetchone()[0] or 0))
            spent_before = spent_after - Decimal(str(amount))
        current_app.logger.warning(
        "BUDGET EMAIL DEBUG: category=%s, budget=%s, before=%s, after=%s",
        category, limit_amount, spent_before, spent_after
        )
        if spent_before <= limit_amount < spent_after:
                send_email_notification(
                    user_row[0],
                    f"FinTrack Budget Alert: {category}",
                    f"Your {category} budget has been exceeded.\n\n"
                    f"Monthly budget: ₹{limit_amount:.2f}\n"
                    f"Total spent: ₹{spent_after:.2f}\n"
                    f"Month: {month_key}\n\n"
                    "Please review your spending in FinTrack."
                )

    except Exception:
        current_app.logger.exception(
            "Failed to process budget email alert"
        )

    cursor.close()
    db.close()


    return jsonify({
            "message": "Expense added successfully",
            "expense_id": expense_id
        }), 201

@main.route("/expenses/<int:user_id>", methods=["GET"])
def get_expenses(user_id):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT id, category, amount, date, description, created_at
        FROM expenses
        WHERE user_id = %s
        ORDER BY date DESC
        """,
        (user_id,)
    )

    expenses = cursor.fetchall()

    cursor.close()
    db.close()

    return jsonify(expenses), 200

@main.route("/expenses/<int:expense_id>", methods=["PUT"])
def update_expense(expense_id):
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "A valid JSON body is required"}), 400

    category = data.get("category")
    amount = data.get("amount")
    expense_date = data.get("date")
    description = data.get("description", "")

    if amount is None or not expense_date:
        return jsonify({
            "error": "amount and date are required"
        }), 400
    if not isinstance(description, str):
        return jsonify({"error": "description must be a string"}), 400
    if not isinstance(category, str) or not category.strip():
        category = categorize_transaction(description)
    else:
        category = category.strip()

    if not is_valid_positive_number(amount):
        return jsonify({
            "error": "amount must be a positive number"
        }), 400

    if not is_valid_date(expense_date):
        return jsonify({
            "error": "date must be in YYYY-MM-DD format"
        }), 400

    db = get_db_connection()
    cursor = db.cursor()

    try:
        cursor.execute(
            """
            UPDATE expenses
            SET category = %s,
                amount = %s,
                date = %s,
                description = %s
            WHERE id = %s
            """,
            (category, amount, expense_date, description, expense_id)
        )

        db.commit()

        if cursor.rowcount == 0:
            return jsonify({"error": "Expense not found"}), 404

        return jsonify({
            "message": "Expense updated successfully"
        }), 200

    except Exception:
        db.rollback()
        return jsonify({"error": "Failed to update expense"}), 500

    finally:
        cursor.close()
        db.close()

@main.route("/expenses/<int:expense_id>", methods=["DELETE"])
def delete_expense(expense_id):
    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute(
        "DELETE FROM expenses WHERE id = %s",
        (expense_id,)
    )

    db.commit()

    if cursor.rowcount == 0:
        cursor.close()
        db.close()
        return jsonify({"error": "Expense not found"}), 404

    cursor.close()
    db.close()

    return jsonify({
        "message": "Expense deleted successfully"
    }), 200

@main.route("/incomes", methods=["POST"])
def add_income():
    data = request.get_json()

    user_id = data.get("user_id")
    source = data.get("source")
    amount = data.get("amount")
    date = data.get("date")
    description = data.get("description", "")
    income_type = data.get("income_type", "regular")

    if not is_valid_positive_number(amount):
        return jsonify({
            "error": "amount must be a positive number"
    }), 400

    if not is_valid_date(date):
        return jsonify({
            "error": "date must be in YYYY-MM-DD format"
    }), 400

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute(
        """
        INSERT INTO incomes
        (user_id, source, amount, date, description, income_type)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (user_id, source, amount, date, description, income_type)
    )

    db.commit()
    income_id = cursor.lastrowid

    cursor.close()
    db.close()

    return jsonify({
        "message": "Income added successfully",
        "income_id": income_id
    }), 201

@main.route("/incomes/<int:user_id>", methods=["GET"])
def get_incomes(user_id):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT id, source, amount, date, description, income_type, created_at
        FROM incomes
        WHERE user_id = %s
        ORDER BY date DESC
        """,
        (user_id,)
    )

    incomes = cursor.fetchall()

    cursor.close()
    db.close()

    return jsonify(incomes), 200

@main.route("/incomes/<int:income_id>", methods=["PUT"])
def update_income(income_id):
    data = request.get_json()

    source = data.get("source")
    amount = data.get("amount")
    date = data.get("date")
    description = data.get("description", "")
    income_type = data.get("income_type", "regular")

    if not is_valid_positive_number(amount):
            return jsonify({
                "error": "amount must be a positive number"
        }), 400
    
    if not is_valid_date(date):
        return jsonify({
            "error": "date must be in YYYY-MM-DD format"
        }), 400

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute(
        """
        UPDATE incomes
        SET source = %s,
            amount = %s,
            date = %s,
            description = %s,
            income_type = %s
        WHERE id = %s
        """,
        (source, amount, date, description, income_type, income_id)
    )

    db.commit()

    if cursor.rowcount == 0:
        cursor.close()
        db.close()
        return jsonify({"error": "Income not found"}), 404

    cursor.close()
    db.close()

    return jsonify({
        "message": "Income updated successfully"
    }), 200

@main.route("/incomes/<int:income_id>", methods=["DELETE"])
def delete_income(income_id):
    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute(
        "DELETE FROM incomes WHERE id = %s",
        (income_id,)
    )

    db.commit()

    if cursor.rowcount == 0:
        cursor.close()
        db.close()
        return jsonify({"error": "Income not found"}), 404

    cursor.close()
    db.close()

    return jsonify({
        "message": "Income deleted successfully"
    }), 200

@main.route("/savings", methods=["POST"])
def add_saving():
    data = request.get_json()

    user_id = data.get("user_id")
    goal = data.get("goal")
    amount = data.get("amount")
    target_amount = data.get("target_amount")
    month = data.get("month")

    if not user_id or not goal or amount is None or target_amount is None or not month:
        return jsonify({
            "error": "user_id, goal, amount, target_amount and month are required"
    }), 400

    if not is_valid_non_negative_number(amount):
        return jsonify({
            "error": "amount cannot be negative"
    }), 400

    if not is_valid_positive_number(target_amount):
        return jsonify({
            "error": "target_amount must be a positive number"
    }), 400

    if not is_valid_month(month):
        return jsonify({
            "error": "month must be in YYYY-MM format"
    }), 400

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute(
        """
        INSERT INTO savings
        (user_id, goal, amount, target_amount, month)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (user_id, goal, amount, target_amount, month)
    )

    db.commit()

    savings_id = cursor.lastrowid

    cursor.close()
    db.close()

    return jsonify({
        "message": "Savings added successfully",
        "savings_id": savings_id
    }), 201

@main.route("/savings/<int:user_id>", methods=["GET"])
def get_savings(user_id):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT id, goal, amount, target_amount, month, created_at
        FROM savings
        WHERE user_id = %s
        ORDER BY month DESC
        """,
        (user_id,)
    )

    savings = cursor.fetchall()

    cursor.close()
    db.close()

    for item in savings:
        progress = calculate_savings_goal(
            float(item.get("target_amount") or 0), float(item.get("amount") or 0)
        )
        item.update(progress)
    return jsonify(savings), 200

@main.route("/savings/<int:savings_id>", methods=["PUT"])
def update_saving(savings_id):
    data = request.get_json(silent=True) or {}

    user_id = data.get("user_id")
    goal = data.get("goal")
    amount = data.get("amount")
    target_amount = data.get("target_amount")
    month = data.get("month")

    if (
        user_id is None
        or not isinstance(goal, str)
        or not goal.strip()
        or amount is None
        or target_amount is None
        or not month
    ):
        return jsonify({
            "error": "user_id, goal, amount, target_amount and month are required"
        }), 400

    if not is_valid_non_negative_number(amount):
        return jsonify({"error": "amount cannot be negative"}), 400

    if not is_valid_positive_number(target_amount):
        return jsonify({
            "error": "target_amount must be a positive number"
        }), 400

    if not is_valid_month(month):
        return jsonify({
            "error": "month must be in YYYY-MM format"
        }), 400

    db = get_db_connection()
    cursor = db.cursor()

    try:
        cursor.execute(
            "SELECT id FROM savings WHERE id = %s AND user_id = %s",
            (savings_id, user_id)
        )

        if cursor.fetchone() is None:
            return jsonify({"error": "Savings record not found"}), 404

        cursor.execute(
            """
            UPDATE savings
            SET goal = %s,
                amount = %s,
                target_amount = %s,
                month = %s
            WHERE id = %s AND user_id = %s
            """,
            (goal, amount, target_amount, month, savings_id, user_id)
        )

        db.commit()

        return jsonify({
            "message": "Savings updated successfully"
        }), 200

    except Exception:
        db.rollback()
        raise

    finally:
        cursor.close()
        db.close()



@main.route("/savings/<int:savings_id>", methods=["DELETE"])
def delete_saving(savings_id):
    db = get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute("DELETE FROM savings WHERE id = %s", (savings_id,))
        db.commit()
        if cursor.rowcount == 0:
            return jsonify({"error": "Savings goal not found"}), 404
        return jsonify({"message": "Savings goal deleted successfully"}), 200
    except Exception:
        db.rollback()
        current_app.logger.exception("Failed to delete savings goal")
        return jsonify({"error": "Failed to delete savings goal"}), 500
    finally:
        cursor.close()
        db.close()

@main.route("/budgets", methods=["POST"])
def add_budget():
    data = request.get_json()

    user_id = data.get("user_id")
    category = data.get("category")
    limit_amount = data.get("limit_amount")
    month = data.get("month")

    if not user_id or not category or limit_amount is None or not month:
        return jsonify({
            "error": "user_id, category, limit_amount and month are required"
    }), 400

    if not is_valid_positive_number(limit_amount):
        return jsonify({
            "error": "limit_amount must be a positive number"
    }), 400

    if not is_valid_month(month):
        return jsonify({
            "error": "month must be in YYYY-MM format"
    }), 400

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute(
        """
        INSERT INTO budgets
        (user_id, category, limit_amount, month)
        VALUES (%s, %s, %s, %s)
        """,
        (user_id, category, limit_amount, month)
    )

    db.commit()

    budget_id = cursor.lastrowid

    cursor.close()
    db.close()

    return jsonify({
        "message": "Budget added successfully",
        "budget_id": budget_id
    }), 201

@main.route("/budgets/<int:user_id>", methods=["GET"])
def get_budgets(user_id):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT id, category, limit_amount, month, created_at
        FROM budgets
        WHERE user_id = %s
        ORDER BY month DESC
        """,
        (user_id,)
    )

    budgets = cursor.fetchall()
    for budget in budgets:
        cursor.execute(
            """SELECT COALESCE(SUM(amount), 0) AS spent FROM expenses
               WHERE user_id = %s AND category = %s AND DATE_FORMAT(date, '%Y-%m') = %s""",
            (user_id, budget["category"], budget["month"]),
        )
        row = cursor.fetchone()
        spent = float(row["spent"] if isinstance(row, dict) else row[0])
        budget.update(calculate_budget(spent, float(budget["limit_amount"])))

    cursor.close()
    db.close()
    return jsonify(budgets), 200


@main.route("/budgets/<int:budget_id>", methods=["PUT"])
def update_budget(budget_id):
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "A valid JSON body is required"
        }), 400

    category = data.get("category")
    limit_amount = data.get("limit_amount")
    month = data.get("month")

    if not category or limit_amount is None or not month:
        return jsonify({
            "error": "category, limit_amount and month are required"
        }), 400

    if not is_valid_positive_number(limit_amount):
        return jsonify({
            "error": "limit_amount must be a positive number"
        }), 400

    if not is_valid_month(month):
        return jsonify({
            "error": "month must be in YYYY-MM format"
        }), 400

    db = get_db_connection()
    cursor = db.cursor()

    try:
        cursor.execute(
            """
            UPDATE budgets
            SET category = %s,
                limit_amount = %s,
                month = %s
            WHERE id = %s
            """,
            (category, limit_amount, month, budget_id)
        )

        db.commit()

        if cursor.rowcount == 0:
            return jsonify({
                "error": "Budget not found or no changes made"
            }), 404

        return jsonify({
            "message": "Budget updated successfully"
        }), 200

    except Exception:
        db.rollback()
        return jsonify({
            "error": "Failed to update budget"
        }), 500

    finally:
        cursor.close()
        db.close()


@main.route("/budgets/<int:budget_id>", methods=["DELETE"])
def delete_budget(budget_id):
    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute(
        "DELETE FROM budgets WHERE id = %s",
        (budget_id,)
    )

    db.commit()

    if cursor.rowcount == 0:
        cursor.close()
        db.close()
        return jsonify({"error": "Budget not found"}), 404

    cursor.close()
    db.close()

    return jsonify({
        "message": "Budget deleted successfully"
    }), 200

@main.route("/investments", methods=["POST"])
def add_investment():
    data = request.get_json()

    user_id = data.get("user_id")
    investment_type = data.get("type")
    risk_level = data.get("risk_level", "Medium")
    amount = data.get("amount")
    duration = data.get("duration")
    returns_expected = data.get("returns_expected")
    status = data.get("status", "Suggested")
    notes = data.get("notes")

    if not user_id or not investment_type or amount is None:
        return jsonify({
            "error": "user_id, type and amount are required"
    }), 400

    if not is_valid_positive_number(amount):
        return jsonify({
            "error": "amount must be a positive number"
    }), 400

    if risk_level not in ["Low", "Medium", "High"]:
        return jsonify({
            "error": "risk_level must be Low, Medium or High"
    }), 400

    if status not in ["Suggested", "Planned", "Active", "Completed"]:
        return jsonify({
            "error": "invalid investment status"
    }), 400

    if returns_expected is not None and not is_valid_non_negative_number(returns_expected):
        return jsonify({
            "error": "returns_expected cannot be negative"
    }), 400

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute(
        """
        INSERT INTO investments
        (user_id, type, risk_level, amount, duration,
         returns_expected, status, notes)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            user_id,
            investment_type,
            risk_level,
            amount,
            duration,
            returns_expected,
            status,
            notes
        )
    )

    db.commit()

    investment_id = cursor.lastrowid

    cursor.close()
    db.close()

    return jsonify({
        "message": "Investment added successfully",
        "investment_id": investment_id
    }), 201


@main.route("/investments/<int:investment_id>", methods=["PUT"])
def update_investment(investment_id):
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "A valid JSON body is required"
        }), 400

    investment_type = data.get("type")
    risk_level = data.get("risk_level", "Medium")
    amount = data.get("amount")
    duration = data.get("duration")
    returns_expected = data.get("returns_expected")
    status = data.get("status", "Suggested")
    notes = data.get("notes")

    if not investment_type or amount is None:
        return jsonify({
            "error": "type and amount are required"
        }), 400

    if not is_valid_positive_number(amount):
        return jsonify({
            "error": "amount must be a positive number"
        }), 400

    if risk_level not in ["Low", "Medium", "High"]:
        return jsonify({
            "error": "risk_level must be Low, Medium or High"
        }), 400

    if status not in ["Suggested", "Planned", "Active", "Completed"]:
        return jsonify({
            "error": "invalid investment status"
        }), 400

    if (
        returns_expected is not None
        and not is_valid_non_negative_number(returns_expected)
    ):
        return jsonify({
            "error": "returns_expected cannot be negative"
        }), 400

    db = get_db_connection()
    cursor = db.cursor()

    try:
        cursor.execute(
            """
            UPDATE investments
            SET type = %s,
                risk_level = %s,
                amount = %s,
                duration = %s,
                returns_expected = %s,
                status = %s,
                notes = %s
            WHERE id = %s
            """,
            (
                investment_type,
                risk_level,
                amount,
                duration,
                returns_expected,
                status,
                notes,
                investment_id
            )
        )

        db.commit()

        if cursor.rowcount == 0:
            return jsonify({
                "error": "Investment not found or no changes made"
            }), 404

        return jsonify({
            "message": "Investment updated successfully"
        }), 200

    except Exception:
        db.rollback()
        return jsonify({
            "error": "Failed to update investment"
        }), 500

    finally:
        cursor.close()
        db.close()


@main.route("/investments/<int:user_id>", methods=["GET"])
def get_investments(user_id):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT id, type, risk_level, amount, duration,
               returns_expected, status, notes, created_at
        FROM investments
        WHERE user_id = %s
        ORDER BY created_at DESC
        """,
        (user_id,)
    )

    investments = cursor.fetchall()

    cursor.close()
    db.close()

    return jsonify(investments), 200

@main.route("/investments/<int:investment_id>", methods=["DELETE"])
def delete_investment(investment_id):
    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute(
        "DELETE FROM investments WHERE id = %s",
        (investment_id,)
    )

    db.commit()

    if cursor.rowcount == 0:
        cursor.close()
        db.close()
        return jsonify({
            "error": "Investment not found"
        }), 404

    cursor.close()
    db.close()

    return jsonify({
        "message": "Investment deleted successfully"
    }), 200

@main.route("/investment-preferences", methods=["POST"])
def add_investment_preferences():
    data = request.get_json()

    user_id = data.get("user_id")
    risk_tolerance = data.get("risk_tolerance")
    preferred_types = data.get("preferred_types")
    investment_horizon = data.get("investment_horizon")
    monthly_investment_budget = data.get("monthly_investment_budget")

    if risk_tolerance not in ["Low", "Medium", "High"]:
        return jsonify({
        "error": "risk_tolerance must be Low, Medium or High"
    }), 400

    if (
    monthly_investment_budget is not None
    and not is_valid_non_negative_number(monthly_investment_budget)
):
        return jsonify({
        "error": "monthly_investment_budget cannot be negative"
    }), 400

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute(
        """
        INSERT INTO investment_preferences
        (user_id, risk_tolerance, preferred_types,
         investment_horizon, monthly_investment_budget)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (
            user_id,
            risk_tolerance,
            preferred_types,
            investment_horizon,
            monthly_investment_budget
        )
    )

    db.commit()
    preference_id = cursor.lastrowid

    cursor.close()
    db.close()

    return jsonify({
        "message": "Investment preferences added successfully",
        "preference_id": preference_id
    }), 201

@main.route("/investment-preferences/<int:user_id>", methods=["GET"])
def get_investment_preferences(user_id):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT id, risk_tolerance, preferred_types,
               investment_horizon, monthly_investment_budget,
               created_at, updated_at
        FROM investment_preferences
        WHERE user_id = %s
        """,
        (user_id,)
    )

    preferences = cursor.fetchone()

    cursor.close()
    db.close()

    if not preferences:
        return jsonify({
            "error": "Investment preferences not found"
        }), 404

    return jsonify(preferences), 200

@main.route("/investment-preferences/<int:user_id>", methods=["PUT"])
def update_investment_preferences(user_id):
    data = request.get_json()

    risk_tolerance = data.get("risk_tolerance")
    preferred_types = data.get("preferred_types")
    investment_horizon = data.get("investment_horizon")
    monthly_investment_budget = data.get("monthly_investment_budget")

    if risk_tolerance not in ["Low", "Medium", "High"]:
            return jsonify({
            "error": "risk_tolerance must be Low, Medium or High"
        }), 400
    
    if (
        monthly_investment_budget is not None
        and not is_valid_non_negative_number(monthly_investment_budget)
    ):
            return jsonify({
            "error": "monthly_investment_budget cannot be negative"
        }), 400

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute(
        """
        UPDATE investment_preferences
        SET risk_tolerance = %s,
            preferred_types = %s,
            investment_horizon = %s,
            monthly_investment_budget = %s
        WHERE user_id = %s
        """,
        (
            risk_tolerance,
            preferred_types,
            investment_horizon,
            monthly_investment_budget,
            user_id
        )
    )

    db.commit()

    if cursor.rowcount == 0:
        cursor.close()
        db.close()
        return jsonify({
            "error": "Investment preferences not found"
        }), 404

    cursor.close()
    db.close()

    return jsonify({
        "message": "Investment preferences updated successfully"
    }), 200

@main.route("/taxes", methods=["POST"])
def add_tax():
    data = request.get_json()

    user_id = data.get("user_id")
    tax_year = data.get("tax_year")
    income = data.get("income")
    deductions = data.get("deductions", 0)
    estimated_tax = data.get("estimated_tax")
    tax_status = data.get("tax_status", "Estimated")

    if not user_id or not tax_year or income is None or estimated_tax is None:
        return jsonify({
        "error": "user_id, tax_year, income and estimated_tax are required"
    }), 400

    if not is_valid_non_negative_number(income):
        return jsonify({
        "error": "income cannot be negative"
    }), 400

    if not is_valid_non_negative_number(deductions):
        return jsonify({
        "error": "deductions cannot be negative"
    }), 400

    if not is_valid_non_negative_number(estimated_tax):
        return jsonify({
        "error": "estimated_tax cannot be negative"
    }), 400

    if tax_status not in ["Estimated", "Filed", "Paid"]:
        return jsonify({
        "error": "invalid tax status"
    }), 400

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute(
        """
        INSERT INTO taxes
        (user_id, tax_year, income, deductions, estimated_tax, tax_status)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            user_id,
            tax_year,
            income,
            deductions,
            estimated_tax,
            tax_status
        )
    )

    db.commit()
    tax_id = cursor.lastrowid

    cursor.close()
    db.close()

    return jsonify({
        "message": "Tax record added successfully",
        "tax_id": tax_id
    }), 201

@main.route("/taxes/<int:tax_id>", methods=["PUT"])
def update_tax(tax_id):
    data = request.get_json(silent=True) or {}

    user_id = data.get("user_id")
    tax_year = data.get("tax_year")
    income = data.get("income")
    deductions = data.get("deductions", 0)
    estimated_tax = data.get("estimated_tax")
    tax_status = data.get("tax_status", "Estimated")

    if (
        user_id is None
        or not tax_year
        or income is None
        or estimated_tax is None
    ):
        return jsonify({
            "error": "user_id, tax_year, income and estimated_tax are required"
        }), 400

    if (
        isinstance(tax_year, bool)
        or not str(tax_year).isdigit()
        or len(str(tax_year)) != 4
        or not 1901 <= int(tax_year) <= 2155
    ):
        return jsonify({
            "error": "tax_year must be a valid four-digit year"
        }), 400

    if not is_valid_non_negative_number(income):
        return jsonify({"error": "income cannot be negative"}), 400

    if not is_valid_non_negative_number(deductions):
        return jsonify({"error": "deductions cannot be negative"}), 400

    if not is_valid_non_negative_number(estimated_tax):
        return jsonify({"error": "estimated_tax cannot be negative"}), 400

    if tax_status not in ["Estimated", "Filed", "Paid"]:
        return jsonify({"error": "invalid tax status"}), 400

    db = get_db_connection()
    cursor = db.cursor()

    try:
        cursor.execute(
            "SELECT id FROM taxes WHERE id = %s AND user_id = %s",
            (tax_id, user_id)
        )

        if cursor.fetchone() is None:
            return jsonify({"error": "Tax record not found"}), 404

        cursor.execute(
            """
            UPDATE taxes
            SET tax_year = %s,
                income = %s,
                deductions = %s,
                estimated_tax = %s,
                tax_status = %s
            WHERE id = %s AND user_id = %s
            """,
            (
                tax_year,
                income,
                deductions,
                estimated_tax,
                tax_status,
                tax_id,
                user_id
            )
        )

        db.commit()

        return jsonify({
            "message": "Tax record updated successfully"
        }), 200

    except Exception:
        db.rollback()
        raise

    finally:
        cursor.close()
        db.close()

@main.route("/taxes/<int:user_id>", methods=["GET"])
def get_taxes(user_id):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT id, tax_year, income, deductions,
               estimated_tax, tax_status, created_at
        FROM taxes
        WHERE user_id = %s
        ORDER BY tax_year DESC
        """,
        (user_id,)
    )

    taxes = cursor.fetchall()

    cursor.close()
    db.close()

    return jsonify(taxes), 200

@main.route("/taxes/<int:tax_id>", methods=["DELETE"])
def delete_tax(tax_id):
    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute(
        "DELETE FROM taxes WHERE id = %s",
        (tax_id,)
    )

    db.commit()

    if cursor.rowcount == 0:
        cursor.close()
        db.close()

        return jsonify({
            "error": "Tax record not found"
        }), 404

    cursor.close()
    db.close()

    return jsonify({
        "message": "Tax record deleted successfully"
    }), 200

@main.route("/notifications", methods=["POST"])
def add_notification():
    data = request.get_json()

    user_id = data.get("user_id")
    title = data.get("title")
    message = data.get("message")
    trigger_type = data.get("trigger_type")
    status = data.get("status", "Unread")
    scheduled_at = data.get("scheduled_at")

    if status not in ["Unread", "Read", "Dismissed"]:
        return jsonify({
        "error": "invalid notification status"
    }), 400
    if not title.strip() or not message.strip():
        return jsonify({
        "error": "title and message cannot be empty"
    }), 400

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute(
        """
        INSERT INTO notifications
        (user_id, title, message, trigger_type, status, scheduled_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            user_id,
            title,
            message,
            trigger_type,
            status,
            scheduled_at
        )
    )

    db.commit()
    notification_id = cursor.lastrowid

    cursor.close()
    db.close()

    return jsonify({
        "message": "Notification created successfully",
        "notification_id": notification_id
    }), 201

@main.route("/notifications/<int:user_id>", methods=["GET"])
def get_notifications(user_id):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT id, title, message, trigger_type,
               status, scheduled_at, created_at
        FROM notifications
        WHERE user_id = %s
        ORDER BY created_at DESC
        """,
        (user_id,)
    )

    notifications = cursor.fetchall()

    cursor.close()
    db.close()

    return jsonify(notifications), 200

@main.route("/notifications/<int:notification_id>", methods=["PUT"])
def update_notification(notification_id):
    data = request.get_json()

    title = data.get("title")
    message = data.get("message")
    trigger_type = data.get("trigger_type")
    status = data.get("status", "Unread")
    scheduled_at = data.get("scheduled_at")

    if status not in ["Unread", "Read", "Dismissed"]:
            return jsonify({
            "error": "invalid notification status"
        }), 400
    if not title.strip() or not message.strip():
            return jsonify({
            "error": "title and message cannot be empty"
        }), 400

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute(
        """
        UPDATE notifications
        SET title = %s,
            message = %s,
            trigger_type = %s,
            status = %s,
            scheduled_at = %s
        WHERE id = %s
        """,
        (
            title,
            message,
            trigger_type,
            status,
            scheduled_at,
            notification_id
        )
    )

    db.commit()

    if cursor.rowcount == 0:
        cursor.close()
        db.close()

        return jsonify({
            "error": "Notification not found"
        }), 404

    cursor.close()
    db.close()

    return jsonify({
        "message": "Notification updated successfully"
    }), 200

@main.route("/notifications/<int:notification_id>", methods=["DELETE"])
def delete_notification(notification_id):
    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute(
        "DELETE FROM notifications WHERE id = %s",
        (notification_id,)
    )

    db.commit()

    if cursor.rowcount == 0:
        cursor.close()
        db.close()

        return jsonify({
            "error": "Notification not found"
        }), 404

    cursor.close()
    db.close()

    return jsonify({
        "message": "Notification deleted successfully"
    }), 200

    return jsonify({"message": "User registered successfully"}), 201

@main.route("/finance-summary/<int:user_id>", methods=["GET"])
def get_finance_summary(user_id):
    """Return all-time income/expense totals for the user's dashboard."""
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("SELECT COALESCE(SUM(amount), 0) AS total FROM incomes WHERE user_id = %s", (user_id,))
        income_row = cursor.fetchone() or {}
        cursor.execute("SELECT COALESCE(SUM(amount), 0) AS total FROM expenses WHERE user_id = %s", (user_id,))
        expense_row = cursor.fetchone() or {}
        result = calculate_finances([float(income_row.get("total") or 0)], [float(expense_row.get("total") or 0)])
        return jsonify(result), 200
    except Exception:
        __import__("logging").getLogger(__name__).exception("Failed to calculate finance summary")
        return jsonify({"error": "Failed to calculate finance summary"}), 500
    finally:
        cursor.close()
        db.close()


@main.route("/spending-insights/<int:user_id>", methods=["GET"])
def get_spending_insights(user_id):
    """Return category/month spending analytics based on saved expenses."""
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            """SELECT id, category, amount, date, description FROM expenses
               WHERE user_id = %s ORDER BY date ASC""",
            (user_id,),
        )
        rows = cursor.fetchall()
        transactions = []
        for row in rows:
            expense_date = row.get("date")
            month_key = expense_date.strftime("%Y-%m") if hasattr(expense_date, "strftime") else str(expense_date)[:7]
            transactions.append({
                "id": row.get("id"), "category": row.get("category") or "Unknown / Other",
                "amount": float(row.get("amount") or 0), "month": month_key,
                "date": str(expense_date), "description": row.get("description") or "",
            })
        return jsonify(spending_insights(transactions)), 200
    except Exception:
        __import__("logging").getLogger(__name__).exception("Failed to calculate spending insights")
        return jsonify({"error": "Failed to calculate spending insights"}), 500
    finally:
        cursor.close()
        db.close()


@main.route("/investment-suggestions/<int:user_id>", methods=["GET"])
def get_investment_suggestions(user_id):
    """Educational investment suggestions based on current-month totals and saved preferences."""
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            """SELECT COALESCE(SUM(amount), 0) AS total FROM incomes
               WHERE user_id = %s AND DATE_FORMAT(date, '%Y-%m') = DATE_FORMAT(CURDATE(), '%Y-%m')""",
            (user_id,),
        )
        monthly_income = float((cursor.fetchone() or {}).get("total") or 0)
        cursor.execute(
            """SELECT COALESCE(SUM(amount), 0) AS total FROM expenses
               WHERE user_id = %s AND DATE_FORMAT(date, '%Y-%m') = DATE_FORMAT(CURDATE(), '%Y-%m')""",
            (user_id,),
        )
        monthly_expenses = float((cursor.fetchone() or {}).get("total") or 0)
        cursor.execute("SELECT risk_tolerance, investment_horizon, monthly_investment_budget FROM investment_preferences WHERE user_id = %s ORDER BY id DESC LIMIT 1", (user_id,))
        preferences = cursor.fetchone() or {}
        risk = str(preferences.get("risk_tolerance") or "Medium").lower()
        horizon = str(preferences.get("investment_horizon") or "medium").lower()
        horizon_aliases = {"short-term": "short", "short term": "short", "medium-term": "medium", "medium term": "medium", "long-term": "long", "long term": "long"}
        horizon = horizon_aliases.get(horizon, horizon)
        risk_aliases = {"low risk": "low", "moderate": "medium", "medium risk": "medium", "high risk": "high"}
        risk = risk_aliases.get(risk, risk)
        savings_goal = float(preferences.get("monthly_investment_budget") or 0)
        result = suggest_investment(monthly_income, monthly_expenses, savings_goal, horizon, risk)
        if isinstance(result, str):
            return jsonify({"error": result}), 400
        return jsonify(result), 200
    except Exception:
        __import__("logging").getLogger(__name__).exception("Failed to generate investment suggestions")
        return jsonify({"error": "Failed to generate investment suggestions"}), 500
    finally:
        cursor.close()
        db.close()
