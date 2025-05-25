
def write_total_sheet(sheet_name, df):
    if not {'Afdeling', 'Aantal', 'Prijs'}.issubset(df.columns):
        print("❌ Vereiste kolommen ontbreken, totalen niet gegenereerd.")
        return

    df['Totaal (€)'] = pd.to_numeric(df['Aantal'], errors='coerce').fillna(0) * pd.to_numeric(df['Prijs'], errors='coerce').fillna(0)
    totals = df.groupby('Afdeling')['Totaal (€)'].sum().reset_index()
    totaal_algemeen = totals['Totaal (€)'].sum()
    totals.loc[len(totals.index)] = ['Totaal', totaal_algemeen]
    totals['Totaal (€)'] = totals['Totaal (€)'].round(2)

    # Maak nieuwe tabbladnaam
    totaal_tab = sheet_name.replace("Stock", "Totaal")

    # Verbind met Google Sheets
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_FILE, SCOPES)
    gc = gspread.authorize(creds)
    sheet = gc.open_by_key(SHEET_ID)

    try:
        worksheet = sheet.worksheet(totaal_tab)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = sheet.add_worksheet(title=totaal_tab, rows="100", cols="2")

    worksheet.clear()
    worksheet.update([totals.columns.tolist()] + totals.values.tolist())
    print(f"✅ Totaal-tabblad '{totaal_tab}' aangemaakt of bijgewerkt.")
