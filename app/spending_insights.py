"""Aggregate expense transactions into category and monthly insights."""

from collections import defaultdict
from datetime import datetime
import math


def spending_insights(transactions):
    """Summarize transactions with amount, category, and YYYY-MM month fields."""
    if not transactions:
        return {
            "total_expenses": 0,
            "category_totals": {},
            "highest_category": None,
            "monthly_totals": {},
            "monthly_change_percent": None,
            "unusual_expenses": [],
            "message": "No expense records available",
        }

    category_totals = defaultdict(float)
    monthly_totals = defaultdict(float)
    expense_amounts = []

    for index, transaction in enumerate(transactions):
        if not isinstance(transaction, dict):
            raise ValueError(f"Transaction at index {index} must be a dictionary")

        try:
            amount = float(transaction["amount"])
            category = transaction["category"]
            month = transaction["month"]
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                f"Transaction at index {index} needs valid amount, category, and month"
            ) from exc

        if not math.isfinite(amount) or amount < 0:
            raise ValueError("Expense amounts must be finite and non-negative")
        if not isinstance(category, str) or not category.strip():
            raise ValueError("Transaction category must be a non-empty string")
        if not isinstance(month, str):
            raise ValueError("Transaction month must use YYYY-MM format")
        try:
            parsed_month = datetime.strptime(month, "%Y-%m")
            if parsed_month.strftime("%Y-%m") != month:
                raise ValueError
        except ValueError as exc:
            raise ValueError("Transaction month must use YYYY-MM format") from exc

        category_totals[category] += amount
        monthly_totals[month] += amount
        expense_amounts.append(amount)

    total_expenses = sum(expense_amounts)
    highest_category = max(category_totals, key=category_totals.get)
    months = sorted(monthly_totals)

    change = None
    if len(months) >= 2:
        previous = monthly_totals[months[-2]]
        current = monthly_totals[months[-1]]
        if previous > 0:
            change = ((current - previous) / previous) * 100
        elif current == 0:
            change = 0.0

    average = total_expenses / len(expense_amounts)
    unusual_expenses = [
        transaction for transaction in transactions
        if float(transaction["amount"]) > 2 * average
    ]

    return {
        "total_expenses": round(total_expenses, 2),
        "category_totals": {k: round(v, 2) for k, v in category_totals.items()},
        "highest_category": highest_category,
        "monthly_totals": {k: round(v, 2) for k, v in monthly_totals.items()},
        "monthly_change_percent": round(change, 2) if change is not None else None,
        "unusual_expenses": unusual_expenses,
    }
