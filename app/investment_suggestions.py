"""Educational investment guidance based on horizon and risk preference.

This module provides general educational information, not personalized financial
advice or a promise of returns.
"""

import math


def _valid_nonnegative_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value >= 0
    )



def suggest_investment(
    monthly_income,
    monthly_expenses,
    savings_goal,
    time_horizon,
    risk_preference,
):
    if (
        not _valid_nonnegative_number(monthly_income)
        or not _valid_nonnegative_number(monthly_expenses)
        or not _valid_nonnegative_number(savings_goal)
    ):
        return {"error": "Income, expenses and savings goal must be valid non-negative numbers."}

    time_horizon = str(time_horizon).lower()
    risk_preference = str(risk_preference).lower()

    if time_horizon not in ["short", "medium", "long"]:
        return {"error": "Invalid time horizon."}

    if risk_preference not in ["low", "medium", "high"]:
        return {"error": "Invalid risk preference."}

    monthly_surplus = monthly_income - monthly_expenses

    result = {
        "monthly_surplus": round(monthly_surplus, 2),
        "savings_goal": round(savings_goal, 2),
        "time_horizon": time_horizon,
        "risk_preference": risk_preference,
        "options": [],
        "note": (
            "Educational information only. Returns are not guaranteed. "
            "Check current product terms, fees, tax rules and risks before investing."
        ),
    }

    if monthly_surplus <= 0:
        result["suggestion"] = (
            "Your expenses currently meet or exceed your income. "
            "Review your budget and emergency savings before investing."
        )
        return result

    # A practical monthly amount to explore, not a mandatory investment.
    monthly_budget = round(monthly_surplus * 0.20, 2)

    # Lower amounts should still receive useful options.
    amount_note = (
        f"Illustrative monthly budget: ₹{monthly_budget:,.2f}. "
        "This is a planning example, not a required investment."
    )

    options = []

    if time_horizon == "short":
        options = [
            {
                "name": "Savings account",
                "risk_level": "Low",
                "why": "Useful to learn about for money you may need soon.",
                "caution": "Compare interest, access and applicable deposit protections.",
            },
            {
                "name": "Short-term fixed deposit",
                "risk_level": "Low",
                "why": "Can suit a known near-term goal when the term matches your date.",
                "caution": "Check premature withdrawal rules, tax and institution protections.",
            },
        ]

        if risk_preference == "high":
            options.append({
                "name": "Market-linked funds — learn before considering",
                "risk_level": "High",
                "why": "Useful for understanding how market risk works.",
                "caution": "Not suitable for money you cannot afford to lose or need soon.",
            })

    elif time_horizon == "medium":
        options = [
            {
                "name": "Fixed deposits",
                "risk_level": "Low",
                "why": "A category to compare for goals with a defined timeline.",
                "caution": "Compare rates, lock-in, tax and withdrawal conditions.",
            },
            {
                "name": "Short-duration debt funds",
                "risk_level": "Low to Medium",
                "why": "A market-linked category to research for medium-term goals.",
                "caution": "Returns are not guaranteed; credit and interest-rate risks apply.",
            },
        ]

        if risk_preference in ["medium", "high"]:
            options.append({
                "name": "Diversified index funds",
                "risk_level": "High",
                "why": "Can provide broad equity-market exposure for suitable goals.",
                "caution": "Values can fall significantly; a medium horizon may be too short.",
            })

    else:
        options = [
            {
                "name": "Diversified index funds",
                "risk_level": "Medium to High",
                "why": "Worth researching for long-term goals and diversified exposure.",
                "caution": "Equity markets can fall sharply; returns are not guaranteed.",
            },
            {
                "name": "Recurring deposit or fixed deposit",
                "risk_level": "Low",
                "why": "Can be compared for the more stable part of a savings plan.",
                "caution": "Check whether returns keep pace with inflation after tax.",
            },
        ]

        if risk_preference in ["medium", "high"]:
            options.append({
                "name": "Diversified equity mutual funds",
                "risk_level": "High",
                "why": "A category to study for long horizons and equity exposure.",
                "caution": "Can lose value; understand costs and market volatility.",
            })

    if risk_preference == "low":
        options = [
            option for option in options
            if option["risk_level"] in ["Low", "Low to Medium"]
        ]

    result["suggestion"] = amount_note
    result["options"] = options
    return result
