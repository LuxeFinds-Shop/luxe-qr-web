from flask import Flask, request, send_file
import io
import qrcode
from qrcode.constants import ERROR_CORRECT_H
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
                data = f"""LuxeFinds Vape
Produkt: {product}
Preis: €{price_float:.2f}
Nikotin: {nicotine} mg/ml
Generiert: {datetime.date.today().strftime('%d.%m.%Y')}"""

                qr = qrcode.QRCode(
                    version=None,
                    error_correction=ERROR_CORRECT_H,
                    box_size=10,
                    border=4,
                )
                qr.add_data(data)
                qr.make(fit=True)

                img = qr.make_image(
                    fill_color=(15, 23, 42),  # Dunkelblau
                    back_color="white"
                ).convert("RGB")

                buf = io.BytesIO()
                img.save(buf, format="PNG")
                buf.seek(0)

                return send_file(
                    buf,
                    mimetype='image/png',
                    as_attachment=True,
                    download_name=f'luxe_{product.replace(" ", "_")[:30]}_{nicotine}mg.png'
                )
            except Exception as e:
                return f"Fehler: {str(e)} – bitte versuche es nochmal.", 500

    # Formular anzeigen
    return """
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LuxeFinds QR-Generator</title>
    <style>
        body { font-family: system-ui, sans-serif; background:#f8fafc; padding:20px; max-width:500px; margin:auto; }
        h1 { color:#6366f1; text-align:center; }
        label { display:block; margin:12px 0 4px; font-weight:bold; }
        input { width:100%; padding:10px; border:1px solid #ccc; border-radius:8px; }
        button { width:100%; background:#6366f1; color:white; border:none; padding:14px; font-size:1.1rem; border-radius:8px; margin-top:16px; cursor:pointer; }
        button:hover { background:#4f46e5; }
    </style>
</head>
<body>
    <h1>LuxeFinds Vape QR-Generator</h1>
    <form method="post">
        <label>Produktname</label>
        <input name="product" required placeholder="z.B. Mango Ice Blast">

        <label>Preis (€)</label>
        <input name="price" type="number" step="0.01" required placeholder="19.90">

        <label>Nikotin (mg/ml)</label>
        <input name="nicotine" type="number" required placeholder="20">

        <button type="submit">QR-Code generieren & herunterladen</button>
    </form>
</body>
</html>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
