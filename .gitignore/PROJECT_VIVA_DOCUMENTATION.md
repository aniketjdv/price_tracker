# PricePulse: Intelligent E-Commerce Price Tracking & AI Forecasting System
## Complete Viva & Technical Architecture Documentation

---

# 1. Executive Summary & Project Overview

### Project Title
**PricePulse — Intelligent Multi-Marketplace E-Commerce Price Tracking, Anomaly Detection & AI Forecasting System**

### Problem Statement
In modern e-commerce (Amazon, Flipkart, Myntra, Croma, Reliance Digital), product prices fluctuate dynamically due to algorithmic pricing, flash sales, seasonal demand, and marketplace competition. Consumers frequently struggle with:
1. Identifying whether a current price is genuinely a good deal or an artificial mark-up.
2. Knowing whether to **BUY NOW** or **WAIT** for an imminent price drop.
3. Tracking prices across multiple fragmented e-commerce platforms simultaneously.

### Solution
PricePulse is an enterprise-grade Django web application integrated with a **dedicated Machine Learning Engine (`ai_engine`)**. It continuously monitors product prices across multiple platforms, maintains historical price series, performs time-aware future price forecasting (7, 14, and 30 days), detects price anomalies (flash discounts and abnormal surges), and provides explainable **Buy/Wait recommendations**.

---

# 2. End-to-End System Architecture

```
+-----------------------------------------------------------------------------------+
|                           SIMULATED E-COMMERCE STORE                              |
|           (Realistic Multi-Marketplace Catalog: Amazon, Flipkart, Myntra, etc.)   |
+------------------------------------------+----------------------------------------+
                                           |
                                           v  [REST API / Provider Interface]
+-----------------------------------------------------------------------------------+
|                             PRICE TRACKER BACKEND                                 |
|                                                                                   |
|  1. URL Resolver: Matches product links/slugs to database entities                |
|  2. Historical Data Engine: Records time-stamped price points in DB               |
|  3. User Alert Engine: Dispatches notifications when target prices are met        |
+------------------------------------------+----------------------------------------+
                                           |
                                           v  [Historical Database Records]
+-----------------------------------------------------------------------------------+
|                        AI / MACHINE LEARNING PIPELINE                             |
|                                (ai_engine/)                                       |
|                                                                                   |
|  [Step 1] Data Preprocessing: Chronological sorting, cleaning, validation        |
|  [Step 2] Feature Engineering: Time-series lags (t-1..t-7), 7/14/30d rolling stats|
|                                 (STRICT ZERO LOOKAHEAD LEAKAGE ENFORCEMENT)       |
|                                                                                   |
|        +-------------------------+------------------------+                       |
|        |                         |                        |                       |
|        v                         v                        v                       |
|  [Price Forecast Model]   [Anomaly Detector]    [Buy/Wait Recommendation Engine]  |
|   - Random Forest          - Isolation Forest    - Multi-Factor Decision Matrix   |
|   - Linear Baseline        - Statistical IQR     - Dynamic Explainable Rationale  |
|   - 7d, 14d, 30d Horizons    & Z-Score Bands     - Strength: Strong Buy/Wait...   |
+------------------------------------------+----------------------------------------+
                                           |
                                           v  [Model Predictions & Serialized Joblib]
+-----------------------------------------------------------------------------------+
|                         USER DASHBOARD & PRESENTATION                             |
|                                                                                   |
|  1. Product Detail Page: Live AI Intelligence Card + Multi-Horizon Forecasts     |
|  2. Interactive Chart.js Graph: Historical Actuals + Purple Dashed AI Forecast    |
|  3. Catalog & Alerts Pages: Real-time AI Buy/Wait recommendation badges           |
|  4. REST APIs: JSON endpoints for external consumer integrations                  |
|  5. Django Admin: Model performance metrics & prediction audit log                |
+-----------------------------------------------------------------------------------+
```

---

# 3. Detailed Component Breakdown

## A. Simulated E-Commerce Store & Data Providers (`dashboard/data_providers/`)
- **Purpose**: Simulates realistic e-commerce marketplaces (Amazon, Flipkart, Myntra, Croma, Reliance Digital) providing catalog items, live prices, discounts, stock levels, and price history series.
- **Independence & Extensibility**: The system follows the **Abstract Provider Design Pattern** (`EcommerceProvider`). The AI engine does not know whether data comes from the simulator or real scraping APIs (e.g., Rainforest, ScrapingBee). Switching to live Amazon/Flipkart APIs only requires adding a provider class without altering the ML pipeline.
- **Realistic Price Patterns**: The simulator generates realistic economic cycles:
  - Long-term downward/upward trends
  - Periodic festival discounts & flash sales
  - Price recoveries and stability plateaus

## B. Product Tracking & URL Resolution (`dashboard/views.py` `track_new`)
- Users paste a product URL into the tracker.
- The system resolves internal store slugs (`/store/product/<slug>/`), external product IDs (`SIM-AMA-001`), or direct catalog URLs.
- Initiates automated monitoring and registers a `PriceAlert` for the user.

## C. Per-User Authentication & Isolation
- Each user has their own private watchlist and price alerts.
- Product tracking (`product.tracked_by.add(user)`) and alert notifications are isolated per user.
- Unauthenticated visitors are guided with sign-in prompts before tracking.

## D. Admin Product Management (`dashboard/views.py` `admin_dashboard`)
- Site administrators can edit product titles, brands, categories, current prices, MRPs, stock statuses, descriptions, and manual notes via interactive modal forms.
- If an admin manually lowers a product price below active user target prices, the system automatically marks alerts as `TRIGGERED` and dispatches notifications.

---

# 4. Deep-Dive: AI & Machine Learning Architecture (`ai_engine/`)

### 1. Data Preprocessing (`ai_engine/preprocessing.py`)
- **Extraction**: Fetches time-stamped price entries from `PriceHistory` linked to `ProductListing`.
- **Chronological Sorting**: Ensures strict ascending order by `recorded_at` to preserve temporal causality.
- **Cleaning & Validation**: Drops corrupt negative prices, eliminates consecutive duplicate daily records, and enforces the **Minimum Data Requirement** ($\ge 5$ records). If fewer records exist, the model returns a clear *"Insufficient historical data"* message rather than making erroneous predictions.

### 2. Feature Engineering & Zero-Leakage Guarantee (`ai_engine/feature_engineering.py`)
Time-series models must never peek into future data. All features for time index $t$ are derived **strictly from historical observations $\le t$**:
- **Lag Features**:
  - $P_{t-1}$ (Previous day price)
  - $P_{t-2}, P_{t-3}$ (Recent momentum)
  - $P_{t-7}$ (Weekly cycle lag)
- **Rolling Moving Averages**:
  - 7-Day Rolling Mean ($\mu_{7}$)
  - 14-Day Rolling Mean ($\mu_{14}$)
  - 30-Day Rolling Mean ($\mu_{30}$)
- **Rolling Volatility & Dispersion**:
  - 7-Day & 14-Day Rolling Standard Deviation ($\sigma_{7}, \sigma_{14}$)
  - 7-Day & 30-Day Rolling Min & Max ($P_{\text{min}, 30}, P_{\text{max}, 30}$)
- **Rate of Change & Relative Metrics**:
  - 1-Day Price Change Percentage: $\frac{P_t - P_{t-1}}{P_{t-1}} \times 100$
  - 7-Day Price Change Percentage: $\frac{P_t - P_{t-7}}{P_{t-7}} \times 100$
  - Difference from 30-Day Average: $\frac{P_t - \mu_{30}}{\mu_{30}} \times 100$
- **Calendar & Temporal Features**: Day of week ($0-6$), Day of month ($1-31$), Month ($1-12$), Days elapsed since start.

### 3. Multi-Horizon Price Forecasting (`ai_engine/price_prediction.py`)
- **Algorithms**:
  - **Random Forest Regressor** (Ensemble of 100 decision trees, `max_depth=6`, non-linear multi-feature interaction).
  - **Linear Regression** (Baseline reference model).
- **Target Variables**: Multi-output direct forecasting predicting target prices at $t+7$, $t+14$, and $t+30$ days.
- **Chronological Time-Split Validation**: Data is split chronologically ($80\%$ historical training, $20\%$ recent test) rather than random shuffle splitting to prevent future-to-past data leakage.

### 4. Anomaly Detection Engine (`ai_engine/anomaly_detection.py`)
- **Approach**: Combines **Isolation Forest** (unsupervised tree ensemble that isolates outliers) with **Statistical Interquartile Range ($\text{IQR}$)** and rolling $Z$-score bands:
  $$\text{IQR} = Q_3 - Q_1$$
  $$\text{Lower Bound} = Q_1 - 1.5 \times \text{IQR}$$
  $$\text{Upper Bound} = Q_3 + 1.5 \times \text{IQR}$$
- **Classification**:
  - If $P_{\text{current}} < \text{Lower Bound} \implies$ **`FLASH_DROP`** (*"Unusually low price detected. Potential flash sale or clearance."*)
  - If $P_{\text{current}} > \text{Upper Bound} \implies$ **`SURGE`** (*"Abnormal price surge detected. Above standard historical distribution."*)
  - Otherwise $\implies$ **`NORMAL`**.

### 5. AI Buy / Wait Recommendation Engine (`ai_engine/recommendation.py`)
Produces actionable decisions based on measurable economic and statistical parameters:
- **Decision Outputs**: `BUY NOW` or `WAIT`
- **Strength Classification**: `Strong Buy`, `Buy`, `Wait`, `Strong Wait`
- **Core Decision Logic Matrix**:
  1. **All-Time Low / Flash Sale**: Current price is $\le 2\%$ above all-time historical minimum $\implies$ **`BUY NOW` (`Strong Buy`)**.
  2. **Imminent Price Decline**: Forward model forecasts $\ge 3.5\%$ expected price reduction over next 14 days $\implies$ **`WAIT` (`Strong Wait` or `Wait`)**.
  3. **Significant Value Discount**: Current price is $\ge 5\%$ below 30-day average with stable forecast $\implies$ **`BUY NOW` (`Buy`)**.
  4. **Above-Average Pricing**: Current price is $\ge 4\%$ above historical mean with softening forecast $\implies$ **`WAIT` (`Wait`)**.
  5. **Dynamic Explanations**: Generates clear, customized English sentences referencing actual numbers (e.g., *"Price is trending downward. The AI forecasting model projects a further 5.6% decline over the next 14 days (target: ₹33,999)."*).

### 6. Model Evaluation & Metrics (`ai_engine/evaluation.py`)
The model computes standard academic regression metrics:
- **Mean Absolute Error ($\text{MAE}$)**: Average magnitude of prediction errors in Rupees:
  $$\text{MAE} = \frac{1}{n} \sum_{i=1}^{n} |y_i - \hat{y}_i|$$
- **Root Mean Squared Error ($\text{RMSE}$)**: Penalizes large outlier forecast errors:
  $$\text{RMSE} = \sqrt{\frac{1}{n} \sum_{i=1}^{n} (y_i - \hat{y}_i)^2}$$
- **Coefficient of Determination ($R^2$)**: Proportion of price variance explained by features:
  $$R^2 = 1 - \frac{\sum (y_i - \hat{y}_i)^2}{\sum (y_i - \bar{y})^2}$$

---

# 5. REST API Architecture

| Endpoint | HTTP Method | Output Data |
| :--- | :--- | :--- |
| `/api/ai/products/<id>/analysis/` | `GET` | Complete analysis (current price, 7d/14d/30d predictions, recommendation, strength, dynamic reasoning, anomaly status, historical min/avg/max). |
| `/api/ai/products/<id>/prediction/` | `GET` | Future price forecast points for 7, 14, and 30 days with trend status. |
| `/api/ai/products/<id>/recommendation/` | `GET` | BUY NOW / WAIT recommendation with strength and dynamic reasoning. |
| `/api/ai/products/<id>/anomaly/` | `GET` | Anomaly flag, score, anomaly type, and explanation. |
| `/api/ai/metrics/` | `GET` | Model evaluation metrics ($\text{MAE}$, $\text{RMSE}$, $R^2$, sample count). |

---

# 6. Database Schema & Entity Relationships

```
+----------------+          +--------------------+          +----------------+
|    Product     | 1      * |   ProductListing   | 1      * |  PriceHistory  |
|----------------|----------|--------------------|----------|----------------|
| id             |          | id                 |          | id             |
| name           |          | product_id (FK)    |          | listing_id (FK)|
| current_price  |          | platform_id (FK)   |          | price          |
| original_price |          | current_price      |          | recorded_at    |
| lowest_price   |          | last_updated       |          +----------------+
| tracked        |          +--------------------+
+-------+--------+
        |
        | 1
        |
        | *
+-------+--------------------+          +--------------------+
|  AIPricePrediction         |          |   AIModelMetric    |
|----------------------------|          |--------------------|
| product_id (FK)            |          | id                 |
| current_price              |          | model_name         |
| predicted_price_7_days     |          | model_type         |
| predicted_price_14_days    |          | mae                |
| predicted_price_30_days    |          | rmse               |
| trend                      |          | r2_score           |
| recommendation             |          | trained_samples    |
| recommendation_strength    |          | trained_at         |
| recommendation_reason      |          +--------------------+
| is_anomaly                 |
| anomaly_reason             |
| historical_average         |
| historical_minimum         |
+----------------------------+
```

---

# 7. Management Commands

### 1. Train and Evaluate ML Models
```bash
python manage.py train_price_model
```
- Extracts historical prices across all database listings.
- Generates leak-free time-series features.
- Trains Random Forest Regressor & Linear Regression models.
- Computes $\text{MAE}$, $\text{RMSE}$, and $R^2$.
- Serializes trained weights to `ai_engine/saved_models/price_predictor.joblib` and updates `AIModelMetric` table in DB.

### 2. Generate Catalog-Wide Predictions
```bash
python manage.py generate_ai_predictions
```
- Computes fresh 7d/14d/30d predictions, anomaly flags, and recommendations for all products in the catalog and stores them in `AIPricePrediction`.

### 3. Run Test Suite
```bash
python manage.py test
```
- Executes all 53 unit and integration tests across data preprocessing, feature engineering, models, APIs, and permissions.

---

# 8. Viva Questions & Model Answers

### Q1: Why did you use Random Forest and Linear Regression rather than Deep Learning (LSTM / GRU)?
**Answer**: E-commerce price tracking datasets for individual retail products typically consist of dozens to hundreds of daily observations rather than millions of high-frequency data points. Traditional Machine Learning models (Random Forest with lag and rolling window features) train in seconds, avoid severe overfitting on small-to-medium tabular series, require no GPU dependencies, and are highly explainable for business decisions.

### Q2: What is Data Leakage in time-series price forecasting and how did you prevent it?
**Answer**: Data leakage occurs when information from the future (e.g., future prices, future moving averages, or forward-filled values) inadvertently enters the feature matrix at time $t$, or when datasets are randomly shuffled during train/test splitting. We prevented data leakage by:
1. Calculating all rolling means, standard deviations, and lags strictly backward ($i \le t$).
2. Using a chronological time-based train/test split (earlier 80% data for training, later 20% data for testing).

### Q3: How does the Buy/Wait Recommendation Engine work? Is it hardcoded?
**Answer**: It is **not hardcoded**. The recommendation engine takes dynamic inputs from the trained model and historical price statistics:
- Current price vs historical all-time low.
- Predicted 14-day future price ($\Delta\%$).
- Current discount relative to 30-day average.
- Price trend slope.
It evaluates these differentials dynamically and produces custom narrative reasoning strings referencing exact calculated amounts.

### Q4: How does Anomaly Detection detect unusual prices?
**Answer**: We use an **Isolation Forest** ensemble combined with **Interquartile Range ($\text{IQR}$)** statistical thresholding. Prices falling below $Q_1 - 1.5 \times \text{IQR}$ (or above $Q_3 + 1.5 \times \text{IQR}$) are flagged as anomalous flash drops or abnormal surges.

### Q5: How does this system scale to real Amazon or Flipkart data in the future?
**Answer**: The system uses the **Abstract Provider Pattern** (`EcommerceProvider`). The AI engine and price history models are completely decoupled from data acquisition. To connect live Amazon/Flipkart APIs, we simply implement an `AmazonProvider` inheriting from `EcommerceProvider` that writes to `ProductListing` and `PriceHistory`. The ML models and dashboard function seamlessly without modification.
