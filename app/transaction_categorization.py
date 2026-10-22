"""Rule-based transaction categorization and per-process merchant preferences.

Note: merchant_preferences is in-memory only. Use a database table for persistence
across server restarts and multiple workers.
"""

CATEGORY_KEYWORDS = {
    "Food & Dining": (
        "dominos", "pizza", "restaurant", "cafe", "food", "swiggy", "zomato"
    ),
    "Transport": (
        "uber", "ola", "metro", "bus", "train", "petrol", "fuel"
    ),
    "Shopping": (
        "shopping", "clothes", "flipkart", "mall"
    ),
    "Bills & Utilities": (
        "electricity", "wifi", "mobile recharge", "water bill"
    ),
    "Entertainment & Subscriptions": (
        "netflix", "spotify", "movie", "subscription"
    ),
    "Health": (
        "pharmacy", "medicine", "clinic", "hospital"
    ),
    "Education": (
        "college fee", "books", "course", "tuition", "stationery"
    ),
}

merchant_preferences = {}


def categorize_transaction(description):
    """Return a keyword-based category, or 'Unknown / Other'."""
    if not isinstance(description, str) or not description.strip():
        return "Unknown / Other"

    normalized = description.lower().strip()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(word in normalized for word in keywords):
            return category
    return "Unknown / Other"


def normalize_merchant(merchant):
    """Normalize whitespace and case in a merchant name."""
    if not isinstance(merchant, str):
        return ""
    return " ".join(merchant.lower().strip().split())


def learn_category(user_id, merchant, corrected_category):
    """Remember a user's category correction in process memory."""
    if user_id is None:
        return "User ID is required."
    if not isinstance(merchant, str) or not merchant.strip():
        return "Merchant is required."
    if not isinstance(corrected_category, str) or not corrected_category.strip():
        return "Category is required."

    key = (user_id, normalize_merchant(merchant))
    merchant_preferences[key] = corrected_category.strip()
    return f"Learned: {merchant} -> {corrected_category.strip()}"


def get_category(user_id, merchant, suggested_category):
    """Prefer a saved in-memory correction, otherwise return the suggestion."""
    key = (user_id, normalize_merchant(merchant))
    return merchant_preferences.get(key, suggested_category)
