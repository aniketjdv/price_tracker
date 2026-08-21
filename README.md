
  # Price Tracker Dashboard

  This project is a Django-based price tracking dashboard with SQLite persistence.

  ## Running the code

  1. Create and activate your Python virtual environment, if not already active:
     - Windows PowerShell: `python -m venv .venv` and `.\.venv\Scripts\Activate.ps1`
     - Windows Command Prompt: `python -m venv .venv` and `.\.venv\Scripts\activate.bat`

  2. Install dependencies:
     - `pip install -r requirements.txt`

  3. Apply database migrations:
     - `python manage.py migrate`

  4. Run the development server:
     - `python manage.py runserver`

  5. Open the app in your browser at `http://127.0.0.1:8000/`.

  ## Notes

  - The React/Vite frontend has been removed and replaced with Django templates using Bootstrap.
  - The app stores data in `db.sqlite3`.
  