"""Pure calculation functions for finance, budgets, and savings goals."""


def _is_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
    )


def calculate_finances(income_list, expense_list):
    """Calculate income, expenses, available balance, and remaining savings."""
    if not isinstance(income_list, (list, tuple)) or not isinstance(expense_list, (list, tuple)):
        raise TypeError("income_list and expense_list must be lists or tuples")
    if not all(_is_number(x) for x in income_list):
        raise ValueError("All income values must be numbers")
    if not all(_is_number(x) for x in expense_list):
        raise ValueError("All expense values must be numbers")
    if any(x < 0 for x in income_list):
        raise ValueError("Income values cannot be negative")
    if any(x < 0 for x in expense_list):
        raise ValueError("Expense values cannot be negative")

    total_income = sum(income_list)
    total_expenses = sum(expense_list)
    available_balance = total_income - total_expenses

    return {
        "total_income": round(total_income, 2),
        "total_expenses": round(total_expenses, 2),
        "available_balance": round(available_balance, 2),
        "savings": round(available_balance, 2),
    }


def calculate_budget(spent, budget_limit):
    """Return budget usage and a simple status label."""
    if not _is_number(spent) or not _is_number(budget_limit):
        raise ValueError("spent and budget_limit must be numbers")
    if spent < 0:
        raise ValueError("spent cannot be negative")

    if budget_limit <= 0:
        return {
            "spent": spent,
            "budget_limit": budget_limit,
            "remaining": budget_limit - spent,
            "usage_percent": None,
            "status": "Invalid budget limit",
        }

    remaining = budget_limit - spent
    usage_percent = (spent / budget_limit) * 100

    if spent > budget_limit:
        status = "Overspending"
    elif spent == budget_limit:
        status = "Budget fully used"
    elif usage_percent >= 80:
        status = "Warning"
    else:
        status = "Within budget"

    return {
        "spent": round(spent, 2),
        "budget_limit": round(budget_limit, 2),
        "remaining": round(remaining, 2),
        "usage_percent": round(usage_percent, 2),
        "status": status,
    }


def calculate_savings_goal(target_amount, saved_amount):
    """Calculate remaining amount, progress, and goal status."""
    if not _is_number(target_amount) or not _is_number(saved_amount):
        return {
            "target_amount": target_amount,
            "saved_amount": saved_amount,
            "remaining_amount": None,
            "progress_percent": None,
            "status": "Invalid amount",
        }

    if target_amount <= 0:
        return {
            "target_amount": target_amount,
            "saved_amount": saved_amount,
            "remaining_amount": None,
            "progress_percent": None,
            "status": "Invalid target amount",
        }

    if saved_amount < 0:
        return {
            "target_amount": target_amount,
            "saved_amount": saved_amount,
            "remaining_amount": None,
            "progress_percent": None,
            "status": "Invalid saved amount",
        }

    remaining_amount = max(0, target_amount - saved_amount)
    progress = (saved_amount / target_amount) * 100
    status = "Goal Completed" if saved_amount >= target_amount else "In Progress"

    return {
        "target_amount": round(target_amount, 2),
        "saved_amount": round(saved_amount, 2),
        "remaining_amount": round(remaining_amount, 2),
        "progress_percent": round(min(progress, 100), 2),
        "status": status,
    }
