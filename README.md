# FinTrack — Personal Finance Tracker

FinTrack is a web-based personal finance application designed to help users track transactions, monitor budgets, understand spending patterns, and explore investment suggestions through a single dashboard.

## Features

- **Transaction Tracking:** Record and view income and expenses.
- **Budget Management:** Set budgets and monitor spending against them.
- **Spending Insights:** Understand spending patterns through financial summaries.
- **Transaction Categorization:** Categorize transactions to organize expenses.
- **Investment Suggestions:** Explore suggestions based on available user preferences.
- **Financial Calculations:** Perform calculations to support personal financial planning.
- **Email Notifications:** Receive budget-related alerts through email.
- **Interactive Dashboard:** Access financial information through a web-based interface.

## Tech Stack

| Component | Technologies |
|---|---|
| Frontend | HTML, CSS, JavaScript |
| Backend | Python, Flask |
| Database | MySQL |
| Email Notifications | Flask-Mail |
| Environment Configuration | python-dotenv |

## Project Structure

```text
FinTrack/
├── app/
│   ├── templates/
│   │   └── index.html
│   ├── __init__.py
│   ├── db.py
│   ├── email_utils.py
│   ├── errors.py
│   ├── finance_calculations.py
│   ├── investment_suggestions.py
│   ├── routes.py
│   ├── spending_insights.py
│   └── transaction_categorization.py
├── config.py
├── requirements.txt
├── run.py
└── .gitignore
```

*The structure above highlights the main application files; additional files may exist in the repository.*

## Getting Started

### Prerequisites

- Python 3.10 or later
- MySQL Server
- pip

### 1. Clone the repository

```bash
git clone https://github.com/atulyar645-debug/FinTrack.git
cd FinTrack
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it on Windows:

```bash
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root directory. Add the configuration values required by the application, such as:

```env
SECRET_KEY=your_secret_key
DB_HOST=localhost
DB_USER=your_mysql_username
DB_PASSWORD=your_mysql_password
DB_NAME=your_database_name
MAIL_USERNAME=your_email_address
MAIL_PASSWORD=your_email_app_password
```

**Important:** Use the exact variable names expected by the application code. These names are examples and may need adjustment to match your configuration.

Never upload your `.env` file or expose passwords, email credentials, or other secrets publicly.

### 5. Set up the database

Start MySQL and create the database configured in your environment variables. Ensure the required tables are created according to the application's database schema.

### 6. Run the application

```bash
python run.py
```

Open the local URL displayed in the terminal, commonly:

```text
http://127.0.0.1:5000
```

## Security

- Keep credentials in local environment variables.
- Do not commit `.env` files, passwords, or private keys.
- Keep virtual environments and Python cache files out of version control.

## Future Improvements

- More automated transaction categorization.
- Expanded financial analytics and visualizations.
- Additional investment research and planning tools.
- Improved validation and user experience.

## Disclaimer

FinTrack is an educational project intended for personal finance tracking and exploration. Investment suggestions are informational and should not be treated as professional financial advice.

## Author

**Atulya**  
B.Tech — Computer Science and Engineering

GitHub: [YOUR-GITHUB-PROFILE](https://github.com/YOUR-USERNAME)
