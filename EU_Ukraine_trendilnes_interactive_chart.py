# With this python code, we will create an interactive trendline chart to visualize the votes of
#  the EU Parliament on Ukraine, per political group, over time. The data come csv exports 
# from howtheyvote.eu, based on which, we have created the table `eukraine_trend2` in SQL. 
# We will use plotly and make the chart with a javascript snippets, in order to have a better 
# control of the chart and its interactivity.

# %%
import mysql.connector
import sqlalchemy
from sqlalchemy import create_engine, text
from mysql.connector import Error
from getpass import getpass
import pandas as pd
import numpy as np
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go
from pathlib import Path
import webbrowser
import ipywidgets as widgets
from IPython.display import display, clear_output
import json
import re
from sklearn.metrics import r2_score

# %%
user = "brutalist"
password = getpass("MySQL password: ")
database = "my_database_2"

engine = create_engine(f"mysql+pymysql://{user}:{password}@localhost/{database}")

try:
    with engine.connect() as conn:
        # Wrap query in text() function
        result = conn.execute(text("SELECT '✅ Connection successful' AS status"))
        print(result.scalar())  # Fetch the first column of first row
except Exception as e:
    print(f"❌ Connection failed: {e}")

# %%
query = "SELECT * FROM eukraine_trend2"

# %%
df = pd.read_sql (query, engine)

# %%
df['date_col'] = pd.to_datetime(df['date_col'])

# %%
df = df.sort_values(['member.group.label', 'date_col'])

# %%
df[df.duplicated(subset=['pr_key', 'member.group.label'])]   # should be empty — one row per resolution per group

# %%
def weighted_trend(g):
    x = (g['date_col'] - g['date_col'].min()).dt.days.values
    y = g['pct_for'].values
    w = g['total_votes'].values

    # weighted least squares slope
    slope, intercept = np.polyfit(x, y, 1, w=w)

    # weighted R²
    y_pred = slope * x + intercept
    ss_res = np.sum(w * (y - y_pred)**2)
    ss_tot = np.sum(w * (y - np.average(y, weights=w))**2)
    r2 = 1 - ss_res / ss_tot

    return pd.Series({
        'slope_per_year': slope * 365,
        'r2': r2,
        'avg_turnout': g['total_votes'].mean(),
        'n_dates': len(g)
    })

summary = df.groupby('member.group.label').apply(weighted_trend).reset_index()
summary = summary.sort_values('r2', ascending=False)
summary

# %%
color_map = {
    "European People's Party": "#077EED",
    "Socialists and Democrats": "#ED2500",
    "Renew Europe": "#C89B1D",
    "Greens/European Free Alliance": "#3E9A47",
    "European Conservatives and Reformists": "#996250",
    "The Left": "#F78181",
    "Identity and Democracy": "#1F4E8A",
    "Patriots for Europe": "#8B9ED6",
    "Europe of Sovereign Nations": "#0D0401",
    "Non-attached Members": "#9E9E9E"
}

group_order = [
    "European People's Party",
    "Socialists and Democrats",
    "Renew Europe",
    "Greens/European Free Alliance",
    "European Conservatives and Reformists",
    "The Left",
    "Identity and Democracy",
    "Patriots for Europe",
    "Europe of Sovereign Nations",
    "Non-attached Members",
]

fig = px.scatter(
    df,
    x='date_col',
    y='pct_for',
    color='member.group.label',
    color_discrete_map=color_map,
    category_orders={'member.group.label': group_order},
    custom_data=['vote_url'],
    trendline='ols',
    trendline_scope='trace',
    opacity=0.6,
    labels={'pct_for': "% 'For' votes", 'date_col': 'Date'},
    title="'For' vote share over time, by political group",
    height=760
)

fig.update_layout(
    template="plotly_white",
    title=dict(
        text=(
            "<b>Share of 'For' Vote over Time</b>"
            "<br>"
            "<span style='font-size:14px; font-weight:normal;'>"
            "Double-click a group in the legend to isolate it · Click on any other to compare" "<br>" 
            "Double-click to show all again · Click on any dot to open the resolution"
            "</span>"
        ),
        x=0.5,
        y=0.95,
        font=dict(size=20)   # NEW — bigger main title; the subtitle span overrides its own size/weight
    ),
    plot_bgcolor = "#FAFAF8",
    paper_bgcolor = "#C3D2E0",
    margin=dict(l=90, r=90, t=120, b=70),
    hovermode="closest",
    dragmode=False,
    legend=dict(
        orientation="v",
        x=1.02,
        y=1,
        xanchor="left",
        yanchor="top",
        # bgcolor="#EEF3F7",
        bgcolor="rgba(219,219,211,0.7)",
        bordercolor="black",
        borderwidth=1,
        traceorder="normal",
        title_text=""
    ),
)

fig.add_shape(
    type="rect",
    xref="paper", yref="paper",
    x0=-0.11, x1=1.3,
    y0=-0.98, y1=1.03,
    fillcolor="#E6DCB0",
    line_width=0,
    layer="below"
)

fig.add_shape(
    type="rect",
    xref="x domain", yref="y domain",
    x0=0, x1=1, y0=0, y1=1,
    fillcolor="#E8E8E2",
    line_width=0,
    layer="below"
)

code_map = df.drop_duplicates('member.group.label').set_index('member.group.label')['group_code'].to_dict()
full_name_map = {v: k for k, v in code_map.items()}  # code → full name, for the tooltip step

for trace in fig.data:
    if trace.mode == 'markers':
        trace.marker.size = 9
        group_full_name = full_name_map.get(trace.name, trace.name)  # trace.name is now the code, so look up the full name
        trace.hovertemplate = (
            f"<b>{group_full_name}</b><br>"
            "<b>%{x|%b %d, %Y}<b><br>"
            "%{y}% 'For'<extra></extra>"
        )

r2_by_group = summary.set_index('member.group.label')['r2'].round(3).to_dict()
slope_by_group = summary.set_index('member.group.label')['slope_per_year'].round(2).to_dict()


for trace in fig.data:
    if trace.mode == 'lines':
        r2_value = r2_by_group.get(trace.name, 'N/A')
        slope_value = slope_by_group.get(trace.name, 'N/A')
        trace.hovertemplate = (
            "<b>OLS trendline</b><br>"
            f"{trace.name}<br>"
            f"Slope={slope_value} pts/year<br>"
            f"R²={r2_value}<br>"
            "%{x}<br>"
            "%{y} (trend)<extra></extra>"
        )

for trace in fig.data:
    base_name = trace.name.split(',')[0].strip()
    if base_name in code_map:
        trace.name = code_map[base_name]

html_enhancements = """
<style>
  html, body {
    margin: 0;
    padding: 0;
    background-color: #C3D2E0;
  }

  .plotly-graph-div {
    width: 100% !important;
    height: 100vh !important;
  }
  #open-fullpage-btn {
    position: fixed;
    top: 12px;
    right: 12px;
    z-index: 9999;
    padding: 8px 10px;
    font: 14px/1.2 Arial, sans-serif;
    background: rgba(255,255,255,0.85);
    border: 1px solid rgba(0,0,0,0.25);
    border-radius: 6px;
    cursor: pointer;
  }

  #open-fullpage-btn:hover {
    background: rgba(255,255,255,0.98);
  }
</style>

<button id="open-fullpage-btn" type="button" title="Open in a new tab">
  Open full page ↗
</button>

<script>
window.addEventListener('load', function () {
    const plotDiv = document.querySelector('.plotly-graph-div');
    const btn = document.getElementById('open-fullpage-btn');
    
    if (!plotDiv) return;

    function setOverlayCursor(value) {
        plotDiv.querySelectorAll('.draglayer rect, .draglayer path').forEach(function (el) {
            el.style.cursor = value;
        });
    }

    setOverlayCursor('default');

    plotDiv.on('plotly_hover', function () {
        setOverlayCursor('pointer');
    });

    plotDiv.on('plotly_unhover', function () {
        setOverlayCursor('default');
    });

    plotDiv.on('plotly_afterplot', function () {
        setOverlayCursor('default');
    });

    if (btn) {
        const embedded = (window.self !== window.top);

        if (!embedded) {
            btn.style.display = 'none';
        } else {
            btn.addEventListener('click', function () {
                window.open(window.location.href, '_blank', 'noopener');
            });
        }
    }
});
</script>
<script>
document.addEventListener('DOMContentLoaded', function() {
    var plotDiv = document.querySelector('.plotly-graph-div');

    plotDiv.on('plotly_click', function(data) {
        var point = data.points[0];
        if (point.data.mode && point.data.mode.includes('markers') && point.customdata && point.customdata[0]) {
            window.open(point.customdata[0], '_blank');
        }
    });

    plotDiv.on('plotly_hover', function(data) {
        var point = data.points[0];
        if (point.data.mode && point.data.mode.includes('markers')) {
            plotDiv.style.cursor = 'pointer';
        }
    });

    plotDiv.on('plotly_unhover', function() {
        plotDiv.style.cursor = '';
    });
});
</script>
"""

legend_tooltip_script = f"""
<script>
function addLegendTooltips() {{
    var fullNames = {json.dumps(full_name_map)};
    var legendItems = document.querySelectorAll('.legend .traces');
    legendItems.forEach(function(item) {{
        var textEl = item.querySelector('.legendtext');
        if (textEl) {{
            var code = textEl.textContent.trim();
            if (fullNames[code]) {{
                // Remove any existing <title> child first, to avoid duplicates on re-run
                var existing = item.querySelector('title');
                if (existing) existing.remove();

                var titleEl = document.createElementNS('http://www.w3.org/2000/svg', 'title');
                titleEl.textContent = fullNames[code];
                item.appendChild(titleEl);
            }}
        }}
    }});
}}
document.addEventListener('DOMContentLoaded', function() {{
    var plotDiv = document.querySelector('.plotly-graph-div');
    addLegendTooltips();
    plotDiv.on('plotly_relayout', addLegendTooltips);
}});
</script>
"""


html_enhancements += legend_tooltip_script
html_enhancements += "<title>Share of 'For' Vote over Time</title>"

output_file = "Ukraine_votes_trend2.html"

html_string = fig.to_html(
    include_plotlyjs="cdn",
    full_html=True,
    config={"displayModeBar": False, "scrollZoom": False},
)

html_string = html_string.replace('</body>', html_enhancements + '</body>')

with open(output_file, 'w', encoding='utf-8') as f:
    f.write(html_string)

webbrowser.open(output_file)