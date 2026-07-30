# EU Parliament Votes on Ukraine

An analysis and visualization of how EU Parliament political groups voted on 65 resolutions related to Ukraine, covering military support, financial aid, humanitarian assistance, and trade partnerships.

Source data is sourced from [howtheyvote.eu](https://howtheyvote.eu).

---

## What's in this repo

### SQL — Data preparation

- **`EU_Ukraine_bars.sql`** — Builds the `ukraine_votes` table. Creates a complete grid of votes by resolution, political group, country, and vote position (For / Against / Abstention / Did not vote), with counts and shares.

- **`EU_Ukraine_trend.sql`** — Builds the `eukraine_trend2` table. Parses vote dates, links each resolution to its `howtheyvote.eu` URL via vote ID, and computes the share of "For" votes per political group over time.

### Python — Interactive charts

- **`EU_Ukraine_bars_interactive_chart.py`** — Generates an HTML bar chart showing the average vote position share per political group. Users can filter simultaneously by **country** and **vote category**. Bars are ordered by "For" share.

- **`EU_Ukraine_trendilnes_interactive_chart.py`** — Generates an HTML scatter + trendline chart showing how each political group's "For" vote share evolved over time. Trendlines use weighted OLS regression. Clicking a dot opens the corresponding resolution on howtheyvote.eu.

---

## Requirements

- Python: `pandas`, `numpy`, `plotly`, `sqlalchemy`, `pymysql`, `scikit-learn`
- A local MySQL instance with the source tables loaded from the howtheyvote.eu CSV exports

## Output

Both Python scripts write a self-contained `.html` file and open it in the browser automatically.
