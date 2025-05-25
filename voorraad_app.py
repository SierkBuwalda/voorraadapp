
import dash
from dash import dcc, html, Input, Output, State, dash_table
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import dash_bootstrap_components as dbc
import re

SCOPES = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
CREDS_FILE = 'credentials/credentials.json'
SHEET_ID = '1t5GqCNNbiBVNbfxkrKA8jgu98ZSO-aQNy8NegHcrFGA'

def clean_column_names(df):
    df.columns = [str(col).replace('\xa0', ' ').replace('\u200b', '').strip() for col in df.columns]
    return df

def list_stock_tabs():
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_FILE, SCOPES)
    gc = gspread.authorize(creds)
    sheet = gc.open_by_key(SHEET_ID)
    tabs = [ws.title for ws in sheet.worksheets()]
    stock_tabs = [t for t in tabs if re.match(r"Stock\s+\w+\s+\d{2}", t)]
    print("📄 Gevonden tabbladen:", stock_tabs)
    return stock_tabs

def load_data(sheet_name):
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_FILE, SCOPES)
    gc = gspread.authorize(creds)
    sheet = gc.open_by_key(SHEET_ID).worksheet(sheet_name)
    records = sheet.get_all_records()
    df = pd.DataFrame(records)
    print(f"🔍 Geselecteerd tabblad: {sheet_name}")
    print(f"📊 Kolommen: {df.columns.tolist()}")

    df = clean_column_names(df)
    for col in ['Aantal', 'Prijs']:
        if col in df.columns:
            df[col] = (
                df[col].astype(str)
                .str.replace('€', '', regex=False)
                .str.replace(',', '.', regex=False)
                .str.strip()
                .replace('', '0')
            )
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    if 'Aantal' in df.columns and 'Prijs' in df.columns:
        df['Totaal (€)'] = (df['Aantal'] * df['Prijs']).round(2)
    else:
        df['Totaal (€)'] = 0
    return df

def save_data(sheet_name, df):
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_FILE, SCOPES)
    gc = gspread.authorize(creds)
    worksheet = gc.open_by_key(SHEET_ID).worksheet(sheet_name)

    for col in ['Aantal', 'Prijs', 'Totaal (€)']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    if 'Aantal' in df.columns and 'Prijs' in df.columns:
        df['Totaal (€)'] = (df['Aantal'] * df['Prijs']).round(2)

    worksheet.clear()
    worksheet.update([df.columns.values.tolist()] + df.values.tolist())

# Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

stock_tabs = list_stock_tabs()

app.layout = dbc.Container([
    dcc.Location(id='url', refresh=False),
    html.H2("Voorraadbeheer Kromme Dissel", style={'textAlign': 'center'}),
    dcc.Store(id='data-store'),

    dbc.Row([
        dbc.Col([
            html.Label("Selecteer maand:"),
            dcc.Dropdown(
                id='sheet-select',
                options=[{'label': s, 'value': s} for s in stock_tabs],
                value=stock_tabs[0] if stock_tabs else None
            )
        ])
    ], className='mb-3'),

    dbc.Row([
        dbc.Col([
            html.Label("Afdeling:"),
            dcc.Dropdown(id='afdeling-select')
        ], md=6),
        dbc.Col([
            html.Label("Categorie:"),
            dcc.Dropdown(id='categorie-select')
        ], md=6),
    ]),

    dash_table.DataTable(
        id='voorraad-tabel',
        columns=[],
        data=[],
        editable=True,
        style_table={'overflowX': 'auto'},
        style_cell={'fontFamily': 'Arial', 'textAlign': 'left'},
        style_header={'backgroundColor': '#2e7d32', 'color': 'white', 'fontWeight': 'bold'}
    ),

    html.Div(id='totaal-afdeling', style={'fontWeight': 'bold', 'marginTop': '20px'}),
    html.Div(id='totaal-alle', style={'fontWeight': 'bold'}),
    html.Button("💾 Opslaan naar Google Sheets", id='save-button', n_clicks=0, style={'marginTop': '30px'})
])

@app.callback(
    Output('data-store', 'data'),
    Input('sheet-select', 'value')
)
def update_data_store(selected_sheet):
    if not selected_sheet:
        return []
    df = load_data(selected_sheet)
    return df.to_dict('records')

@app.callback(
    Output('afdeling-select', 'options'),
    Output('afdeling-select', 'value'),
    Input('data-store', 'data'),
    State('afdeling-select', 'value')
)
def update_afdeling_dropdown(data, huidige_afdeling):
    df = pd.DataFrame(data)
    df = clean_column_names(df)
    afdelingen = sorted(df['Afdeling'].dropna().unique()) if 'Afdeling' in df.columns else []
    options = [{'label': a, 'value': a} for a in afdelingen]
    value = huidige_afdeling if huidige_afdeling in afdelingen else (afdelingen[0] if afdelingen else None)
    return options, value

@app.callback(
    Output('categorie-select', 'options'),
    Output('categorie-select', 'value'),
    Input('afdeling-select', 'value'),
    State('data-store', 'data'),
    State('categorie-select', 'value')
)
def update_categorien(afdeling, data, huidige_cat):
    df = pd.DataFrame(data)
    df = clean_column_names(df)
    if 'Afdeling' not in df.columns or 'Categorie' not in df.columns:
        return [], None
    df = df[df['Afdeling'] == afdeling]
    categorien = sorted(df['Categorie'].dropna().unique())
    value = huidige_cat if huidige_cat in categorien else (categorien[0] if categorien else None)
    return [{'label': c, 'value': c} for c in categorien], value

@app.callback(
    Output('voorraad-tabel', 'data'),
    Output('voorraad-tabel', 'columns'),
    Output('totaal-afdeling', 'children'),
    Output('totaal-alle', 'children'),
    Input('data-store', 'data'),
    Input('afdeling-select', 'value'),
    Input('categorie-select', 'value')
)
def update_tabel(data, afdeling, categorie):
    if not data:
        return [], [], "", ""
    df_all = pd.DataFrame(data)
    df_all = clean_column_names(df_all)

    for col in ['Aantal', 'Prijs']:
        if col in df_all.columns:
            df_all[col] = pd.to_numeric(
                df_all[col].astype(str).str.replace('€', '').str.replace(',', '.').str.strip(),
                errors='coerce'
            ).fillna(0)
    df_all['Totaal (€)'] = (df_all['Aantal'] * df_all['Prijs']).round(2)

    df_filter = df_all.copy()
    if afdeling:
        df_filter = df_filter[df_filter['Afdeling'] == afdeling]
    if categorie:
        df_filter = df_filter[df_filter['Categorie'] == categorie]

    columns = [{'name': col, 'id': col, 'editable': col in ['Aantal', 'Prijs']} for col in df_filter.columns]
    return df_filter.to_dict('records'), columns,         f"Totaalwaarde selectie: € {df_filter['Totaal (€)'].sum():,.2f}",         f"Totaalwaarde alle afdelingen: € {df_all['Totaal (€)'].sum():,.2f}"

@app.callback(
    Output('data-store', 'data', allow_duplicate=True),
    Input('voorraad-tabel', 'data'),
    State('data-store', 'data'),
    prevent_initial_call=True
)
def update_data_store_live(rows, old_data):
    df_new = pd.DataFrame(rows)
    df_old = pd.DataFrame(old_data)
    for idx, row in df_new.iterrows():
        index_in_old = df_old[(df_old['Product'] == row['Product']) & (df_old['Afdeling'] == row['Afdeling'])].index
        if not index_in_old.empty:
            for col in ['Aantal', 'Prijs']:
                df_old.at[index_in_old[0], col] = row[col]
    return df_old.to_dict('records')

@app.callback(
    Output('save-button', 'children'),
    Input('save-button', 'n_clicks'),
    State('sheet-select', 'value'),
    State('data-store', 'data'),
    prevent_initial_call=True
)
def save_to_sheets(n_clicks, sheet_name, data):
    df = pd.DataFrame(data)
    save_data(sheet_name, df)
    return "✅ Opgeslagen naar Google Sheets"

if __name__ == '__main__':
    app.run(debug=True)
