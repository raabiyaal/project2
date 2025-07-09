import pandas as pd
from dash import Dash, dcc, html, Input, Output
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Load data
interest_df = pd.read_excel("All Prop Type.xlsx", header=1)
recession_df = pd.read_excel("Recession Data.xlsx", header=1)
recession_df['observation_date'] = pd.to_datetime(recession_df['observation_date'])
rf_df = pd.read_excel("Rf.xlsx", header=1)
rf_df['Quarter'] = pd.to_datetime(rf_df['Quarter'])
rf_df['Rf'] = rf_df['Rf'].astype(str).str.replace('%', '').astype(float)

# Load returns data
def clean_percent(x):
    if isinstance(x, str):
        return float(x.replace('%', '')) if '%' in x else float(x)
    return x

returns_df = pd.read_excel("NCREIF.xlsx", header=0)
for col in returns_df.columns[:7]:  # includes Returns + leading/lagging
    returns_df[col] = pd.to_datetime(returns_df[col])
for col in returns_df.columns[7:]:
    returns_df[col] = returns_df[col].apply(clean_percent)

# Process interest data
if 'Unnamed: 0' in interest_df.columns:
    interest_df.drop(columns=['Unnamed: 0'], inplace=True)
interest_df['Quarter'] = pd.to_datetime(interest_df['Quarter'])
for col in ['Rf', 'g', 'LTV: 25%', 'LTV: 50%', 'LTV: 75%']:
    interest_df[col] = interest_df[col].astype(str).str.replace('%', '').astype(float)
interest_df['Loan Committed'] = interest_df['Loan Committed'].astype(str).str.replace(',', '').astype(float).astype(int)

melted = interest_df.melt(
    id_vars=['Property Type', 'Quarter', 'Loan Committed'],
    value_vars=['LTV: 25%', 'LTV: 50%', 'LTV: 75%'],
    var_name='LTV', value_name='Interest Rate')

# Colors
base_colors = {
    'LTV: 75%': '#3222CE',
    'LTV: 50%': '#7030A0',
    'LTV: 25%': '#00B050'
}

gamma_color = '#C9C9C9'
rf_color = '#A6A6A6'

def darken_color(hex_color, amt=0.5):
    # Convert hex to RGB tuple
    hex_color = hex_color.lstrip('#')
    r, g, b = int(hex_color[0:2],16), int(hex_color[2:4],16), int(hex_color[4:6],16)
    r = int(r * amt)
    g = int(g * amt)
    b = int(b * amt)
    return f'rgb({r},{g},{b})'

leading_lagging_options = [
    {"label": "None", "value": "None"},
    {"label": "Returns", "value": "Returns"},
    {"label": "Leading (1year)", "value": "Leading (1year)"},
    {"label": "Leading (3years)", "value": "Leading (3years)"},
    {"label": "Leading (5years)", "value": "Leading (5years)"},
    {"label": "Lagging (1year)", "value": "Lagging (1year)"},
    {"label": "Lagging (3years)", "value": "Lagging (3years)"},
    {"label": "Lagging (5years)", "value": "Lagging (5years)"}
]

app = Dash(__name__)

app.layout = html.Div([

    html.Label("Select LTVs:"),
    dcc.Checklist(id='ltv-checklist', inline=True,
        options=[{'label': l, 'value': l} for l in ['LTV: 25%', 'LTV: 50%', 'LTV: 75%']],
        value=['LTV: 25%', 'LTV: 50%', 'LTV: 75%']),

    html.Label("Select Add-ons:"),
    dcc.Checklist(id='addon-checklist', inline=True,
        options=[
            {'label': 'Structural Differences', 'value': 'gamma'},
            {'label': 'Risk-Free Rate', 'value': 'rf'},
            {'label': 'Loan Volume', 'value': 'loan'}
        ], value=['gamma', 'rf', 'loan']),

    html.Label("Select NCREIF Return Series to Overlay:"),
    dcc.RadioItems(
        id='return-series-radio',
        options=leading_lagging_options,
        value="None",
        inline=True
    ),

    dcc.Graph(id='main-graph')
])

@app.callback(
    Output('main-graph', 'figure'),
    Input('ltv-checklist', 'value'),
    Input('addon-checklist', 'value'),
    Input('return-series-radio', 'value')
)
def update_graph(ltvs, addons, return_series):
    prop = "Apartment"
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    ordered_ltvs = ['LTV: 75%', 'LTV: 50%', 'LTV: 25%']

    # Plot LTV fills with opaque colors and solid lines
    for ltv in ordered_ltvs:
        if ltv in ltvs:
            df_sub = melted[(melted['Property Type'] == prop) & (melted['LTV'] == ltv)]
            fig.add_trace(go.Scatter(
                x=df_sub['Quarter'], y=df_sub['Interest Rate'], mode='lines',
                name=f"{prop} - {ltv}",
                line=dict(color=base_colors[ltv], width=2),
                fill='tozeroy',
                fillcolor=base_colors[ltv]
            ), secondary_y=False)

    # Structural Differences area and line
    if 'gamma' in addons:
        df_g = interest_df[interest_df['Property Type'] == prop]
        fig.add_trace(go.Scatter(
            x=df_g['Quarter'], y=df_g['g'], name=f"{prop} Structural Diff.",
            mode='lines',
            line=dict(color=gamma_color, width=2),
            fill='tozeroy',
            fillcolor=gamma_color
        ), secondary_y=False)

    # Loan volume on secondary y-axis
    if 'loan' in addons:
        df_l = interest_df[interest_df['Property Type'] == prop]
        fig.add_trace(go.Scatter(
            x=df_l['Quarter'], y=df_l['Loan Committed'] / 1e9,
            name=f"{prop} Loan Volume",
            line=dict(color=darken_color(gamma_color, 0.5), width=2)
        ), secondary_y=True)

    # Risk Free Rate area and line
    if 'rf' in addons:
        fig.add_trace(go.Scatter(
            x=rf_df['Quarter'], y=rf_df['Rf'],
            name='Risk-Free Rate',
            mode='lines',
            line=dict(color=rf_color, width=2),
            fill='tozeroy',
            fillcolor=rf_color
        ), secondary_y=False)

    # Add return/leading/lagging line on top if selected (and not "None")
    if return_series and return_series != "None":
        return_col = "Apt Total Returns"
        x_vals, y_vals = [], []
        for _, row in returns_df.iterrows():
            x_date = row[return_series]
            y_val = row.get(return_col)
            if pd.notna(x_date) and pd.notna(y_val):
                x_vals.append(x_date)
                y_vals.append(y_val)
        if x_vals:
            fig.add_trace(go.Scatter(
                x=x_vals, y=y_vals,
                mode='lines',
                name=f"{prop} - {return_series}",
                line=dict(color='red', width=2),
                fill=None
            ), secondary_y=False)

    # Recession vertical lines
    for rec_qtr in recession_df[recession_df['USREC'] == 1]['observation_date']:
        fig.add_shape(
            type='line', x0=rec_qtr, x1=rec_qtr, y0=0, y1=1,
            xref='x', yref='paper', line=dict(color='gray', width=5), layer='below')

    fig.update_layout(
        # Title removed as requested
        yaxis_title="Interest Rate / Return", yaxis2_title="Loan Volume (Billion USD)",
        template="plotly_white", height=650, hovermode="x unified",
        hoverlabel=dict(
            namelength=50,  # increase max chars shown for trace names
            font=dict(size=13),
            bgcolor="white",
            bordercolor="black"
        )
    )

    fig.update_yaxes(tickformat=".0%", secondary_y=False)

    # Align secondary y-axis 0 with primary y-axis 0
    primary_y_vals = []
    secondary_y_vals = []

    for trace in fig.data:
        if not hasattr(trace, 'y') or trace.y is None:
            continue
        if getattr(trace, 'yaxis', 'y') == 'y2':
            secondary_y_vals.extend([y for y in trace.y if y is not None])
        else:
            primary_y_vals.extend([y for y in trace.y if y is not None])

    if primary_y_vals and secondary_y_vals:
        y1_min, y1_max = min(primary_y_vals), max(primary_y_vals)
        y2_max = max(secondary_y_vals)
        zero_ratio = abs(y1_min) / (y1_max - y1_min) if y1_min < 0 else 0
        y2_min = y2_max * -zero_ratio / (1 - zero_ratio) if zero_ratio < 1 else 0
        fig.update_yaxes(range=[y1_min, y1_max], secondary_y=False)
        fig.update_yaxes(range=[y2_min, y2_max], secondary_y=True)

    return fig

if __name__ == '__main__':
    app.run(debug=True)
