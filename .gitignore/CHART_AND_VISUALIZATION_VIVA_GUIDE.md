# PricePulse: Chart & Visualization Architecture
## Technical Viva Guide: Chart Generation, Libraries & Frontend Data Pipelines

---

# 1. Primary Charting Library Used

In this project, data visualizations and interactive price graphs are built using **Chart.js (v4.4 via CDN)** supplemented with **CSS3 Hardware-Accelerated Conic Gradients** for platform distribution donuts.

* **Library Name**: `Chart.js` (Version 4.4.x)
* **Source / Delivery**: Loaded via CDN: `https://cdn.jsdelivr.net/npm/chart.js`
* **Rendering Engine**: HTML5 `<canvas>` element utilizing 2D hardware-accelerated rasterization.
* **Why Chart.js was Chosen over D3.js or Plotly**:
  1. **Lightweight Footprint**: Chart.js is ~180KB minified, whereas Plotly is >3.5MB.
  2. **High Rendering Performance**: Canvas rendering easily handles hundreds of daily time-series price points without DOM overhead.
  3. **Native Touch & Mobile Responsiveness**: Out-of-the-box touch gesture tooltips and dynamic viewport scaling.
  4. **Elegant Aesthetics**: Smooth bezier curve interpolation, gradient fills, and customizable multi-axis charts.

---

# 2. How Charts are Formed: The 4-Stage Data Pipeline

```
[ Stage 1: Database Query & Aggregation (Django ORM in views.py) ]
   Queries PriceHistory, ProductListing, and AIPricePrediction
                                │
                                ▼
[ Stage 2: JSON Serialization (Python json.dumps) ]
   Converts Python datetime objects to formatted strings ('05 May')
   and Decimal prices to float arrays [49999.0, 48500.0]
                                │
                                ▼
[ Stage 3: Template Context Injection (Django Template Engine) ]
   Transfers JSON data into HTML5 data attributes or inline scripts
   using the |safe filter: {{ chart_history_json|safe }}
                                │
                                ▼
[ Stage 4: Client-Side Canvas Rendering (Chart.js Engine) ]
   Instantiates new Chart(ctx, config) on <canvas id='...'>
   Applies linear gradients, dashed stroke styling, and INR currency formatting
```

---

# 3. Detailed Breakdown of Every Chart in the Application

### Chart 1: Interactive Price History & AI Forecast Dual-Line Graph (`product_detail.html`)
* **Location**: Product Detail Page (`/product/<id>/`)
* **Visual Concept**: Displays actual historical prices in solid blue alongside future AI forecasted prices in dashed purple.
* **How it is Formed**:
  1. Backend queries the last 30 daily price points from `PriceHistory`.
  2. Model Manager generates predictions for 7-day, 14-day, and 30-day horizons.
  3. Combines labels: `['01 May', ..., '30 May', '06 Jun (7d)', '13 Jun (14d)', '29 Jun (30d)']`.
  4. Uses two separate datasets with `spanGaps: true` and `null` padding so the dashed forecast line starts exactly from the last historical actual point.

```javascript
new Chart(ctx, {
  type: 'line',
  data: {
    labels: ['01 May', '15 May', '30 May', '06 Jun (7d)', '13 Jun (14d)', '29 Jun (30d)'],
    datasets: [
      { label: 'Actual Price', data: [52000, 50500, 49999, null, null, null], borderColor: '#3b82f6' },
      { label: 'AI Forecast', data: [null, null, 49999, 48200, 47500, 46900], borderDash: [6,6], borderColor: '#8b5cf6' }
    ]
  }
});
```

---

### Chart 2: Dashboard Home Price Trend with Dynamic Switching (`dashboard_home.html`)
* **Location**: Home Dashboard (`/`)
* **Visual Concept**: Interactive smooth line graph with gradient area fill, product selector dropdown, and time range toggles (`30d`, `60d`, `All`).
* **How it is Formed**:
  1. Backend aggregates historical points for candidate tracked products and serializes into `chart_products_json`.
  2. On dropdown change or period button click, JavaScript slices the dataset and calls `chartInstance.destroy()` followed by re-rendering with new canvas linear gradients.

---

### Chart 3: Monthly Savings & Price Drops Dual-Axis Chart (`analytics.html`)
* **Location**: Analytics Page (`/analytics/`)
* **Visual Concept**: Dual-axis combination chart showing consumer savings volume (INR) as a smooth line and count of active deals as bar columns.
* **How it is Formed**:
  * Uses `yAxisID: 'y'` (left axis in INR) for savings and `yAxisID: 'y1'` (right axis) for deals count.

---

### Chart 4: AI Recommendation Distribution Doughnut (`analytics.html`)
* **Location**: Analytics Page (`/analytics/`)
* **Visual Concept**: Doughnut chart with a 70% cutout displaying the proportion of Strong Buy (Green), Buy (Emerald), Wait (Amber), and Strong Wait (Red).

---

### Chart 5: Store Price Index & Category Ranking Bar Charts (`analytics.html`)
* **Location**: Analytics Page (`/analytics/`)
* **Visual Concept**: Vertical multi-color bar chart comparing average discounts across Amazon, Flipkart, Myntra, Croma, and Reliance Digital, paired with a horizontal bar chart ranking product categories.

---

### Chart 6: Platform Distribution Donut (`dashboard_home.html`)
* **Technique**: Pure CSS3 Hardware-Accelerated Conic Gradient (No JS Library overhead).
* **How it is Formed**:
  * Backend calculates degree angles for each store: `degree = (store_products / total_products) * 360`.
  * Generates inline CSS: `background: conic-gradient(#ff9900 0 120deg, #2874f0 120deg 240deg, ...);`

---

# 4. Key Viva Questions & Answers on Visualization

### Q1: Which library did you use for drawing charts and why?
**Answer**: We used **Chart.js (v4.4 via CDN)**. We chose Chart.js because it renders via HTML5 Canvas (giving fast 60fps hardware-accelerated performance even with hundreds of data points), is lightweight (<200KB compared to Plotly's 3.5MB), is fully responsive on mobile/tablet, and supports dual-axis graphs and custom bezier curves.

### Q2: How do you transfer price data from Django SQL database into Chart.js?
**Answer**:
1. Django ORM queries the `PriceHistory` table for date and price values.
2. In `views.py`, Python formats dates (e.g. '15 May') and extracts price floats into Python lists.
3. `json.dumps()` converts the lists into JSON strings (e.g. `'["15 May", "16 May"]'` and `'[49999, 49500]'`).
4. The Django template injects the JSON using the `|safe` filter (`{{ chart_history_json|safe }}`) into JavaScript.
5. Chart.js consumes the parsed array directly in `datasets.data`.

### Q3: How do you show actual historical prices and future AI predictions on the same graph without connecting errors?
**Answer**: We define two distinct datasets on the same Chart.js instance:
* **Dataset 1 (Actual)**: `[P1, P2, P3, ..., P_today, null, null, null]` with solid blue line.
* **Dataset 2 (AI Forecast)**: `[null, null, ..., P_today, P_7d, P_14d, P_30d]` with `borderDash: [6,6]` purple line.
By having both datasets share `P_today` and setting `spanGaps: true` for nulls, the dashed prediction line seamlessly continues right from where the actual history ends!

### Q4: How did you make the charts responsive on mobile phones and tablets?
**Answer**:
1. Set `responsive: true` and `maintainAspectRatio: false` in Chart.js configuration.
2. Placed the `<canvas>` inside a CSS container with relative positioning and fluid heights (e.g. `height: clamp(220px, 35vw, 300px)`).
3. Configured `maxTicksLimit: 7` on the X-axis so date labels never collide on small mobile screens.

### Q5: How does changing the product dropdown on the Home Dashboard update the chart without reloading the page?
**Answer**: All candidate products' history points are pre-serialized into a JSON object (`chart_products_json`) when the page loads. When the user changes the dropdown, an event listener intercepts the change, looks up the product array in memory, updates the chart labels and data arrays, and calls `chartInstance.update()` or `chartInstance.destroy()` to redraw instantaneously.
