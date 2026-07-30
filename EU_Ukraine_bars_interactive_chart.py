# With this python code, we will create an interactive chart for the EU Parliament votes 
# on Ukraine. The data come csv exports from howtheyvote.eu, based on which, we have created 
# the table `ukraine_votes` in SQL. We will use plotly and make the chart with a javascript 
# snipppet, in order to have a better control of the chart and its interactivity.

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
query = "SELECT * FROM ukraine_votes"

# %%
df = pd.read_sql(query, engine)

# %%
plot_df = df[
    ['pr_key', 'Category', 'country', 'political_group', 'position', 'position_count', 'total_count']
].copy()

for c in ['Category', 'country', 'political_group', 'position']:
    plot_df[c] = plot_df[c].astype(str).str.strip().str.rstrip(';')

plot_df['position_count'] = pd.to_numeric(plot_df['position_count'], errors='coerce')
plot_df['total_count'] = pd.to_numeric(plot_df['total_count'], errors='coerce')

plot_df = plot_df.dropna(subset=['pr_key', 'Category', 'country', 'political_group', 'position', 'position_count', 'total_count'])

valid_positions = {
    'VotePosition.FOR', 'VotePosition.AGAINST',
    'VotePosition.ABSTENTION', 'VotePosition.DID_NOT_VOTE'
}
plot_df = plot_df[plot_df['position'].isin(valid_positions)].copy()

records = plot_df.to_dict(orient='records')

with open("ukraine_votes_records.json", "w", encoding="utf-8") as f:
    json.dump(records, f, ensure_ascii=False)

print("Saved: ukraine_votes_records.json")
print("Rows:", len(plot_df))

# %%
# Load records
with open("ukraine_votes_records.json", "r", encoding="utf-8") as f:
    records = json.load(f)

html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>EU Parliament Votes on Ukraine</title>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
  <style>
  
    body {{
      font-family: Arial, sans-serif;
      margin: 0;
      padding: 16px;
      background: #C3D2E0; 
      color: #222;
    }}
    .controls {{
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      margin-bottom: 12px;
    }}
    .control-box {{
      min-width: 260px;
    }}
    label {{
      display: block;
      font-size: 13px;
      margin-bottom: 4px;
      font-weight: 600;
    }}
    select {{
      width: 100%;
      padding: 8px;
      font-size: 14px;
      background: #EDEAE5;
      color: #222;
      border: 1px solid #cfd6e4;
    }}
    chart {{
      width: 100%;
      height: 760px;
    }}
    .hint {{
      font-size: 12px;
      color: #666;
      margin-top: 6px;
    }}
  </style>
</head>
<body>
  <h2 style="margin: 0 0 14px 0; text-align: center;">EU Parliament Votes on Ukraine</h2>

  <div class="controls">
    <div class="control-box">
      <label for="countrySelect">Country</label>
      <select id="countrySelect"></select>
    </div>
    <div class="control-box">
      <label for="categorySelect">Category</label>
      <select id="categorySelect"></select>
    </div>
  </div> 
  
  <div class="hint">Tip: choose Country and Category together (simultaneous filtering).</div>

  <div id="chart" style="width:100%; min-height:760px;"></div>

  <script>
    const raw = {json.dumps(records, ensure_ascii=False)};

    const BAR_PX = 28;
    const GAP_RATIO = 0.45;
    const TOP_BOTTOM_PX = 220;

    const positionOrder = [
      "VotePosition.FOR",
      "VotePosition.AGAINST",
      "VotePosition.ABSTENTION",
      "VotePosition.DID_NOT_VOTE"
    ];

    const positionLabel = {{
      "VotePosition.FOR": "For",
      "VotePosition.AGAINST": "Against",
      "VotePosition.ABSTENTION": "Abstention",
      "VotePosition.DID_NOT_VOTE": "Did not vote"
    }};

    const colors = {{
      "VotePosition.FOR": "#1F5C4A",
      "VotePosition.AGAINST": "#B0413E",
      "VotePosition.ABSTENTION": "#C9A227",
      "VotePosition.DID_NOT_VOTE": "#6E6A64",
    }};

    const countrySelect = document.getElementById("countrySelect");
    const categorySelect = document.getElementById("categorySelect");

    function uniqueSorted(arr) {{
      return [...new Set(arr)].sort((a,b) => String(a).localeCompare(String(b)));
    }}

    const allCountries = ["All", ...uniqueSorted(raw.map(d => d.country))];
//    const allCategories = ["All", ...uniqueSorted(raw.map(d => d.Category))];
    const categoryOrder = [
      "Political - Military Support",
      "Financial Support",
      "Immigration - Humanitarian Aid",
      "Trade and Partnerships"
    ];
    const allCategories = ["All", ...categoryOrder.filter(c => raw.some(d => d.Category === c))];

    function fillSelect(sel, values) {{
      sel.innerHTML = "";
      values.forEach(v => {{
        const opt = document.createElement("option");
        opt.value = v;
        opt.textContent = v;
        sel.appendChild(opt);
      }});
    }}

    fillSelect(countrySelect, allCountries);
    fillSelect(categorySelect, allCategories);
    countrySelect.value = "All";
    categorySelect.value = "All";

    function filterData() {{
      const country = countrySelect.value;
      const category = categorySelect.value;

      return raw.filter(d =>
        (country === "All" || d.country === country) &&
        (category === "All" || d.Category === category)
      );
    }}

        function aggregate(filtered) {{
      // Get unique total_count per (pr_key, political_group, country, Category)
      const totUnique = new Map();
      for (const d of filtered) {{
        const subKey = d.pr_key + "|||" + d.political_group + "|||" + d.country + "|||" + d.Category;
        if (!totUnique.has(subKey)) {{
          totUnique.set(subKey, {{
            pr_key: d.pr_key,
            political_group: d.political_group,
            total_count: Number(d.total_count) || 0
          }});
        }}
      }}
    
      // Sum total_count per (pr_key, political_group) from the unique subgroups
      const totByRes = new Map();
      for (const o of totUnique.values()) {{
        const key = o.pr_key + "|||" + o.political_group;
        totByRes.set(key, (totByRes.get(key) || 0) + o.total_count);
      }}
    
      // Sum position_count per (pr_key, political_group, position)
      const posMap = new Map();
      for (const d of filtered) {{
        const key = d.pr_key + "|||" + d.political_group + "|||" + d.position;
        posMap.set(key, (posMap.get(key) || 0) + (Number(d.position_count) || 0));
      }}
    
      // Compute per-resolution pct = pos_count / tot_count(pr_key, group)
      const perResPct = [];
      for (const [key, posCount] of posMap.entries()) {{
        const parts = key.split("|||");
        const pr_key = parts[0];
        const political_group = parts[1];
        const position = parts[2];
        const totKey = pr_key + "|||" + political_group;
        const totCount = totByRes.get(totKey) || 0;
        perResPct.push({{
          pr_key: pr_key,
          political_group: political_group,
          position: position,
          pct: totCount ? (100 * posCount / totCount) : 0
        }});
      }}
    
      // Average pct equally across pr_key, per (political_group, position)
      const keyMap = new Map();
      for (const r of perResPct) {{
        const key = r.political_group + "|||" + r.position;
        if (!keyMap.has(key)) {{
          keyMap.set(key, {{ political_group: r.political_group, position: r.position, sum_pct: 0, n: 0 }});
        }}
        const o = keyMap.get(key);
        o.sum_pct += r.pct;
        o.n += 1;
      }}
    
      let rows = Array.from(keyMap.values()).map(o => ({{
        political_group: o.political_group,
        position: o.position,
        position_pct: o.n ? o.sum_pct / o.n : 0
      }}));
    
      // Ensure all party-position combinations exist
      const parties = uniqueSorted(rows.map(r => r.political_group));
      const byKey = new Map(rows.map(r => [r.political_group + "|||" + r.position, r]));
    
      const full = [];
      for (const p of parties) {{
        for (const pos of positionOrder) {{
          const k = p + "|||" + pos;
          if (byKey.has(k)) {{
            full.push(byKey.get(k));
          }} else {{
            full.push({{
              political_group: p,
              position: pos,
              position_pct: 0
            }});
          }}
        }}
      }}
    
      // Normalize to 100 per party (robust)
      const sums = new Map();
      for (const r of full) {{
        sums.set(r.political_group, (sums.get(r.political_group) || 0) + Number(r.position_pct || 0));
      }}
      for (const r of full) {{
        const s = sums.get(r.political_group) || 0;
        r.position_pct = s ? (100 * r.position_pct / s) : 0;
      }}
    
      return full;
    }}

    function partyOrderByFor(rows) {{
      const forRows = rows.filter(r => r.position === "VotePosition.FOR");
      return forRows
        .sort((a,b) => b.position_pct - a.position_pct)
        .map(r => r.political_group);
    }}

    const cursorStyle = document.createElement('style');
    document.head.appendChild(cursorStyle);

    function setOverlayCursor(value) {{
      cursorStyle.textContent = '#chart .drag {{ cursor: ' + value + ' !important; }}';
    }}

    function makeFigure() {{
      const filtered = filterData();

      if (filtered.length === 0) {{
        Plotly.newPlot("chart", [], {{
          template: "plotly_white",
          title: "No data for selected filters"
        }}, {{responsive: true}});
        return;
      }}

      const rows = aggregate(filtered);
      const parties = partyOrderByFor(rows);
      const dynamicHeight = TOP_BOTTOM_PX + parties.length * BAR_PX * (1 + GAP_RATIO);

      const traces = positionOrder.map(pos => {{
        const partRows = rows.filter(r => r.position === pos);

        // map party -> row
        const m = new Map(partRows.map(r => [r.political_group, r]));
        const x = parties.map(p => (m.get(p)?.position_pct ?? 0));
        const y = parties;
        const customdata = parties.map(p => [positionLabel[pos]]);

        return {{
          type: "bar",
          orientation: "h",
          name: positionLabel[pos],
          marker: {{color: colors[pos]}},
          x: x,
          y: y,
          customdata: customdata,
          hovertemplate:
            "<b>%{{y}}</b><br>" +
            "Position: %{{customdata[0]}}<br>" +
            "Share: %{{x:.2f}}%<br>" +
            "<extra></extra>"
        }};
      }});

      const country = countrySelect.value;
      const category = categorySelect.value;

      const layout = {{
        barmode: "stack",
        template: "plotly_white",
        plot_bgcolor: "#DBDBD3",
        paper_bgcolor: "#E6DCB0",
        height: dynamicHeight,
        bargap: GAP_RATIO,
        title: `Country: ${{country}} | Category: ${{category}}`,
        xaxis: {{
          title: "Share of Votes (%)",
          range: [0, 100]
        }},
        yaxis: {{
          automargin: false,
          autorange: "reversed",
          categoryorder: "array",
          categoryarray: parties,
          tickangle: -25,
          ticklabelstandoff: 8
        }},
        legend: {{
          orientation: "h",
          x: 0.18,
          xanchor: "center",
          y: 1.01,
          yanchor: "bottom",
          title: {{text: ""}},
          traceorder: "normal"
        }},
        margin: {{l: 240, r: 20, t: 80, b: 120}},
        dragmode: false,
      }};

      Plotly.newPlot("chart", traces, layout, {{
        responsive: true,
        displayModeBar: false,
        scrollZoom: false,
        staticPlot: false
      }}).then(function(gd) {{

        setOverlayCursor('default');
        gd.on('plotly_hover', function() {{ setOverlayCursor('pointer'); }});
        gd.on('plotly_unhover', function() {{ setOverlayCursor('default'); }});
      }});
    }} 

    countrySelect.addEventListener("change", makeFigure);
    categorySelect.addEventListener("change", makeFigure);

    makeFigure();
  </script>
  <style>
  #open-fullpage-btn {{
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
  }}

  #open-fullpage-btn:hover {{
    background: rgba(255,255,255,0.98);
  }}
  </style>

  <button id="open-fullpage-btn" type="button" title="Open in a new tab">
    Open full page ↗
  </button>

  <script>
  window.addEventListener('load', function () {{
      const btn = document.getElementById('open-fullpage-btn');
      if (btn) {{
          const embedded = (window.self !== window.top);
          if (!embedded) {{
              btn.style.display = 'none';
          }} else {{
              btn.addEventListener('click', function () {{
                  window.open(window.location.href, '_blank', 'noopener');
              }});
          }}
      }}
  }});
  </script>
</body>
</html>
"""

output_file = "ukraine_votes_interactive_final_3.html"

with open(output_file, "w", encoding="utf-8") as f:
    f.write(html)

webbrowser.open(output_file)

print("Saved: ukraine_votes_interactive.html")