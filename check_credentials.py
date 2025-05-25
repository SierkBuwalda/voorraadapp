import os

pad = 'credentials/credentials.json'
if os.path.isfile(pad):
    print(f"✅ Bestand '{pad}' is gevonden.")
else:
    print(f"❌ Bestand '{pad}' is NIET gevonden.")
