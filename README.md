
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

   ## Simulated provider

   The default provider is a deterministic local simulator. Its responses use the same provider contract as future marketplace integrations and are clearly marked with `source: simulator`; they are not data from Amazon, Flipkart, or any other real store.

   Seed 60 products, five marketplace listings per product, and 60 days of history:

   `python manage.py seed_simulator_data`

   Optional controls are `--count`, `--days`, `--seed`, and `--reset`.

   Generate a new price and history point for every listing:

   `python manage.py update_simulated_prices`

   ## Provider configuration

   Copy `.env.example` to `.env` and set `ECOMMERCE_PROVIDER=simulator`. The Django settings read future Amazon and Flipkart credentials from environment variables only. To add a real integration, implement the four methods in `AmazonProvider` or `FlipkartProvider`; the models, services, templates, and views consume the shared provider interface.

   ## Data model

   `Product` stores the shared catalog item. `ProductListing` stores marketplace-specific IDs, sellers, URLs, availability, and current prices. `PriceHistory` stores timestamped prices for each listing, which keeps comparison and ML inputs independent from the provider implementation.
  