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

                # Der Text, der im Barcode kodiert wird (Scanner liest das aus)
                data = f"LuxeFinds|{product}|€{price_float:.2f}|{nicotine_int}mg/ml|{datetime.date.today().strftime('%d.%m.%Y')}"

                # Code128 Barcode generieren (alphanumerisch, perfekt für unseren Text)
                code128 = barcode.get('code128', data, writer=ImageWriter())

                # Optionen: Text unter Barcode anzeigen, Größe anpassen
                options = {
                    'write_text': True,          # Menschlich lesbarer Text unten
                    'text_distance': 5,          # Abstand Text zu Bars
                    'module_width': 0.4,         # Dicke der Bars (für Scanner gut)
                    'dpi': 300                   # Hohe Auflösung für Druck/Scan
                }

                # In Memory speichern (keine Datei auf Server)
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

    # HTML-Formular (angepasst, Hinweis auf Barcode)
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
    </style>
</head>
<body>
    <h1>LuxeFinds Barcode Generator</h1>
    <p class="hint">Erzeugt einen scannbaren Code128-Barcode (wie im Supermarkt). Scanner zeigt den gesamten Text an.</p>
    
    <form method="post">
        <label>Produktname</label>
        <input name="product" required placeholder="z.B. Mango Ice Blast">

        <label>Preis (€)</label>
        <input name="price" type="number" step="0.01" required placeholder="19.90">

        <label>Nikotin (mg/ml)</label>
        <input name="nicotine" type="number" required placeholder="20">

        <button type="submit">Barcode generieren & herunterladen</button>
    </form>
</body>
</html>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
