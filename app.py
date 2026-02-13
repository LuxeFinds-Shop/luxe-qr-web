from flask import Flask, request, send_file
import io
import barcode
from barcode.writer import ImageWriter
import datetime

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        product = request.form.get('product', '').strip()
        price   = request.form.get('price', '').strip()
        nicotine = request.form.get('nicotine', '').strip()

        if product and price and nicotine:
            try:
                price_float = float(price)
                nicotine_int = int(float(nicotine))  # mg/ml meist ganzzahlig

                # Text für den Barcode – mit "CHF " statt Symbol
                data = f"LuxeFinds|{product}|CHF {price_float:.2f}|{nicotine_int}mg/ml|{datetime.date.today().strftime('%d.%m.%Y')}"

                # Code128 Barcode generieren
                code128 = barcode.get('code128', data, writer=ImageWriter())

                # Barcode-Optionen (für gute Lesbarkeit und Scannbarkeit)
                options = {
                    'write_text': True,          # Menschlich lesbarer Text unten
                    'text_distance': 5,          # Abstand Text zu Bars
                    'module_width': 0.4,         # Dicke der Bars (gut für Scanner)
                    'dpi': 300,                  # Hohe Auflösung
                    'quiet_zone': 10             # Rand links/rechts
                }

                # In Memory speichern
                buf = io.BytesIO()
                code128.write(buf, options=options)
                buf.seek(0)

                return send_file(
                    buf,
                    mimetype='image/png',
                    as_attachment=True,
                    download_name=f'luxe_barcode_{product.replace(" ", "_")[:30]}_{nicotine}mg.png'
                )
            except Exception as e:
                return f"Fehler beim Generieren: {str(e)} – bitte Daten prüfen.", 500

    # HTML-Formular mit Schweiz-Hinweis
    return """
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LuxeFinds Barcode Generator</title>
    <style>
        body { font-family: system-ui, sans-serif; background:#f8fafc; padding:20px; max-width:500px; margin:auto; }
        h1 { color:#6366f1; text-align:center; }
        label { display:block; margin:12px 0 4px; font-weight:bold; }
        input { width:100%; padding:10px; border:1px solid #ccc; border-radius:8px; }
        button { width:100%; background:#6366f1; color:white; border:none; padding:14px; font-size:1.1rem; border-radius:8px; margin-top:16px; cursor:pointer; }
        button:hover { background:#4f46e5; }
        .hint { color:#64748b; font-size:0.9rem; margin-top:16px; text-align:center; }
        .info { background:#e0f2fe; padding:12px; border-radius:8px; margin-top:20px; font-size:0.95rem; }
    </style>
</head>
<body>
    <h1>LuxeFinds Barcode Generator</h1>
    <p class="hint">Erzeugt einen scannbaren Code128-Barcode (ideal für Scanner in CH).</p>
    
    <form method="post">
        <label>Produktname</label>
        <input name="product" required placeholder="z.B. Mango Ice Blast">

        <label>Preis (CHF)</label>
        <input name="price" type="number" step="0.01" required placeholder="19.90">

        <label>Nikotin (mg/ml)</label>
        <input name="nicotine" type="number" required placeholder="20">

        <button type="submit">Barcode generieren & herunterladen</button>
    </form>

    <div class="info">
        Der Barcode enthält: LuxeFinds | Produkt | CHF Preis | Nikotin | Datum<br>
        Scanner zeigt den vollen Text an (z. B. LuxeFinds|Mango Ice Blast|CHF 19.90|20mg/ml|13.02.2026)
    </div>
</body>
</html>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
