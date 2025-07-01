import pandas as pd
from dash import Dash, dcc, html, Input, Output
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Load data
file_path = r"All Prop Type.xlsx"
df = pd.read_excel(file_path, header=1)

# Load recession data
recession_file_path = r"Recession Data.xlsx"
recession_df = pd.read_excel(recession_file_path, header=1)
recession_df['observation_date'] = pd.to_datetime(recession_df['observation_date'])

# Load risk-free rate and structural differences data
rf_file_path = r"Rf.xlsx"
rf_df = pd.read_excel(rf_file_path, header=1)
rf_df['Quarter'] = pd.to_datetime(rf_df['Quarter'])
rf_df['Rf'] = rf_df['Rf'].astype(str).str.replace('%', '').astype(float)
rf_df['Structural Differences'] = rf_df['Structural Differences'].astype(str).str.replace('%', '').astype(float)

# Clean data
if 'Unnamed: 0' in df.columns:
    df = df.drop(columns=['Unnamed: 0'])

df['Quarter'] = pd.to_datetime(df['Quarter'])

for col in ['Rf', 'g', 'LTV: 25%', 'LTV: 50%', 'LTV: 75%']:
    df[col] = df[col].astype(str).str.replace('%', '').astype(float)

df['Loan Committed'] = df['Loan Committed'].astype(str).str.replace(',', '').astype(float).astype(int)

# Melt LTV columns for plotting
melted = df.melt(id_vars=['Property Type', 'Quarter', 'Loan Committed'],
                 value_vars=['LTV: 25%', 'LTV: 50%', 'LTV: 75%'],
                 var_name='LTV', value_name='Interest Rate')

# Base RGB colors for each property type
base_colors = {
    'Industrial': '255, 165, 0',
    'Office': '70, 130, 180',
    'Retail': '255, 105, 180',
    'Apartment': '60, 179, 113',
    'Core': '255, 215, 0'
}

# Fill colors with opacity
fill_colors = {
    'Apartment': {
        'LTV: 25%': 'rgba(60,179,113,0.5)',
        'LTV: 50%': 'rgba(60,179,113,0.3)',
        'LTV: 75%': 'rgba(60,179,113,0.15)'
    },
    'Core': {
        'LTV: 25%': 'rgba(255,215,0,0.5)',
        'LTV: 50%': 'rgba(255,215,0,0.3)',
        'LTV: 75%': 'rgba(255,215,0,0.15)'
    },
    'Industrial': {
        'LTV: 25%': 'rgba(255,165,0,0.5)',
        'LTV: 50%': 'rgba(255,165,0,0.3)',
        'LTV: 75%': 'rgba(255,165,0,0.15)'
    },
    'Office': {
        'LTV: 25%': 'rgba(70,130,180,0.5)',
        'LTV: 50%': 'rgba(70,130,180,0.3)',
        'LTV: 75%': 'rgba(70,130,180,0.15)'
    },
    'Retail': {
        'LTV: 25%': 'rgba(255,105,180,0.5)',
        'LTV: 50%': 'rgba(255,105,180,0.3)',
        'LTV: 75%': 'rgba(255,105,180,0.15)'
    }
}

def get_line_color(prop_type):
    rgb = base_colors.get(prop_type, '100,100,100')
    return f'rgba({rgb},1)'

def darken_color(rgb_str, amount=0.5):
    r, g, b = [int(x.strip()) for x in rgb_str.split(',')]
    r_d = max(0, int(r * amount))
    g_d = max(0, int(g * amount))
    b_d = max(0, int(b * amount))
    return f'rgba({r_d},{g_d},{b_d},1)'

def get_loan_color(prop_type):
    rgb = base_colors.get(prop_type, '100,100,100')
    return darken_color(rgb, amount=0.5)

app = Dash(__name__)

app.layout = html.Div([
    # html.H2("  "),

    html.Label("Select Property Type(s):"),
    dcc.Dropdown(
        id='property-type-dropdown',
        options=[{'label': pt, 'value': pt} for pt in df['Property Type'].unique()],
        value=['Apartment'],
        multi=True,
        clearable=False,
    ),

    html.Br(),

    html.Label("Select LTV Levels:"),
    dcc.Checklist(
        id='ltv-checklist',
        options=[
            {'label': 'LTV: 25%', 'value': 'LTV: 25%'},
            {'label': 'LTV: 50%', 'value': 'LTV: 50%'},
            {'label': 'LTV: 75%', 'value': 'LTV: 75%'}
        ],
        value=['LTV: 25%', 'LTV: 50%', 'LTV: 75%'],
        inline=True
    ),

    html.Br(),

    html.Label("Select Additional Lines:"),
    dcc.Checklist(
        id='additional-lines-checklist',
        options=[
            {'label': 'Structural Differences', 'value': 'structural_diff'},
            {'label': 'Risk-Free Rate (Rf)', 'value': 'rf'},
            {'label': 'Loan Volume', 'value': 'loan'}
        ],
        value=['structural_diff', 'rf', 'loan'],
        inline=True
    ),

    dcc.Graph(
        id='interest-loan-graph',
        style={
            'border': '1px solid lightgray',
            'padding': '10px',
            'borderRadius': '8px'
        }
    )
])

@app.callback(
    Output('interest-loan-graph', 'figure'),
    Input('property-type-dropdown', 'value'),
    Input('ltv-checklist', 'value'),
    Input('additional-lines-checklist', 'value')
)
def update_graph(selected_properties, selected_ltvs, additional_lines):
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    if not selected_properties or not selected_ltvs:
        return go.Figure()

    for prop_type in selected_properties:
        # LTV lines with area fill
        for ltv in selected_ltvs:
            sub_df = melted[(melted['Property Type'] == prop_type) & (melted['LTV'] == ltv)]
            line_color = get_line_color(prop_type)
            fillcolor = fill_colors.get(prop_type, {}).get(ltv, 'rgba(200,200,200,0.2)')

            fig.add_trace(go.Scatter(
                x=sub_df['Quarter'],
                y=sub_df['Interest Rate'],
                mode='lines',
                fill='tonexty',
                name=f"{prop_type} - {ltv}",
                line=dict(color=line_color),
                fillcolor=fillcolor,
                hovertemplate='%{y:.2%} %{fullData.name}<extra></extra>'
            ), secondary_y=False)

        # Add Structural Differences if selected
    if 'structural_diff' in additional_lines:
        fig.add_trace(go.Scatter(
            x=rf_df['Quarter'],
            y=rf_df['Structural Differences'],
            mode='lines',
            name="Structural Differences",
            line=dict(color='purple', dash='dash'),
            hovertemplate='%{y:.2%} Structural Differences<extra></extra>'
        ), secondary_y=False)

        # Add Loan Volume if selected
    if 'loan' in additional_lines:
        loan_df = df[df['Property Type'].isin(selected_properties)]
        for prop_type in selected_properties:
            loan_sub_df = loan_df[loan_df['Property Type'] == prop_type]
            loan_color = get_loan_color(prop_type)
            fig.add_trace(go.Scatter(
                x=loan_sub_df['Quarter'],
                y=[val / 1e9 for val in loan_sub_df['Loan Committed']],
                mode='lines',
                name=f'{prop_type} Loan Volume',
                line=dict(color=loan_color, width=2),
                hovertemplate='$%{y:.2f}B<br>%{fullData.name}<extra></extra>'
            ), secondary_y=True)

    # Add Risk-Free Rate if selected (once)
    if 'rf' in additional_lines:
        fig.add_trace(go.Scatter(
            x=rf_df['Quarter'],
            y=rf_df['Rf'],
            mode='lines',
            name='Risk-Free Rate (Rf)',
            line=dict(color='black', dash='dot'),
            hovertemplate='%{y:.2%} %{fullData.name}<extra></extra>'
        ), secondary_y=False)

    # Add thick vertical lines for each recession quarter
    recession_quarters = recession_df[recession_df['USREC'] == 1]['observation_date']
    for rec_qtr in recession_quarters:
        fig.add_shape(
            type="line",
            x0=rec_qtr, x1=rec_qtr,
            y0=0, y1=1,
            xref='x',
            yref='paper',
            line=dict(
                color='rgba(128,128,128,0.6)',
                width=6,
                dash='solid'
            ),
            layer='below'
        )

    fig.update_layout(
        title="Quarterly Estimates of Annual Interest Rates at Various Leverage Ratios for the Years 1996 through 1Q 2025",
        yaxis_title='Estimated Annual Interest Rate Expense',
        legend_title='Legend',
        template='plotly_white',
        hovermode='x unified',
        height=600,
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=False),
        yaxis2=dict(showgrid=False),
    )

    fig.update_yaxes(
        title_text='Estimated Annual Interest Rate Expense',
        tickformat='.0%',
        secondary_y=False
    )

    fig.update_yaxes(
        title_text='Quarterly Loan Volume (Commitments) in USD Billions',
        secondary_y=True
    )

    return fig

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 8050))  # Get port from environment variable, fallback 8050
    app.run(host='0.0.0.0', port=port, debug=False)
