from flask import Flask, request, send_file, render_template_string
import io
import barcode
from barcode.writer import ImageWriter
import datetime
import random
import string
from PIL import Image, ImageDraw, ImageFont

app = Flask(__name__)

# Temporärer Speicher für SN → Infos (später echte DB)
details = {}

def generate_serial_number():
    return ''.join(random.choices(string.digits, k=20))  # 20-stellige reine Zahl

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        product = request.form.get('product', '').strip()
        price   = request.form.get('price', '').strip()
        nicotine = request.form.get('nicotine', '').strip()

        if product and price and nicotine:
            try:
                price_float = float(price)
                nicotine_int = int(float(nicotine))

                sn = generate_serial_number()

                # Barcode-Inhalt = Link zur Detail-Seite
                base_url = request.host_url.rstrip('/')
                barcode_data = f"{base_url}/detail?sn={sn}"

                # Infos speichern
                details[sn] = {
                    'product': product,
                    'price': price_float,
                    'nicotine': nicotine_int,
                    'date': datetime.date.today().strftime('%d.%m.%Y')
                }

                # Code128 erzeugen – dick & breit
                code128 = barcode.get('code128', barcode_data, writer=ImageWriter())

                options = {
                    'write_text': False,           # Kein autom. Text unter Bars
                    'module_width': 0.65,          # Dickere Balken → Barcode wird breiter & kürzer
                    'module_height': 12.0,         # Höhe nicht übertrieben
                    'dpi': 400,
                    'quiet_zone': 10,
                }

                buf = io.BytesIO()
                code128.write(buf, options=options)
                buf.seek(0)

                # PIL Bild laden & erweitern für Text unten
                barcode_img = Image.open(buf).convert('RGB')
                total_height = barcode_img.height + 180
                new_img = Image.new('RGB', (barcode_img.width, total_height), (255, 255, 255))
                draw = ImageDraw.Draw(new_img)
                new_img.paste(barcode_img, ((new_img.width - barcode_img.width) // 2, 30))

                # Schrift laden (Fallback)
                try:
                    font = ImageFont.truetype("arial.ttf", 32)  # Größer für bessere Lesbarkeit
                except:
                    font = ImageFont.load_default()

                # Textzeilen zentriert darunter
                lines = [
                    f"LuxeFinds | {product}",
                    f"CHF {price_float:.2f} | {nicotine_int} mg/ml",
                    f"Datum: {details[sn]['date']}",
                    f"SN: {sn}"
                ]

                y = barcode_img.height + 50
                for line in lines:
                    bbox = draw.textbbox((0, 0), line, font=font)
                    w = bbox[2] - bbox[0]
                    draw.text(((new_img.width - w) // 2, y), line, fill=(0, 0, 0), font=font)
                    y += 45

                # Finales Bild in Buffer
                final_buf = io.BytesIO()
                new_img.save(final_buf, format='PNG')
                final_buf.seek(0)

                return send_file(
                    final_buf,
                    mimetype='image/png',
                    as_attachment=True,
                    download_name=f'luxe_barcode_{product.replace(" ", "_")[:25]}_{nicotine}mg.png'
                )

            except Exception as e:
                return f"Fehler: {str(e)} – Daten prüfen.", 500

    # Startseite – Formular
    return """
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LuxeFinds Barcode Generator</title>
    <style>
        body { font-family:system-ui,sans-serif; background:#f8fafc; padding:20px; max-width:500px; margin:auto; }
        h1 { color:#6366f1; text-align:center; }
        label { display:block; margin:14px 0 6px; font-weight:bold; }
        input { width:100%; padding:12px; border:1px solid #cbd5e1; border-radius:10px; font-size:1rem; }
        button { width:100%; background:#6366f1; color:white; border:none; padding:16px; font-size:1.1rem; border-radius:10px; margin-top:20px; cursor:pointer; }
        button:hover { background:#4f46e5; }
        .hint { color:#64748b; font-size:0.95rem; text-align:center; margin-top:20px; }
    </style>
</head>
<body>
    <h1>LuxeFinds Barcode Generator</h1>
    <p class="hint">Erzeugt dicken Code128-Barcode mit Seriennummer.<br>Scannen → öffnet Detail-Seite mit Produkt-Infos.</p>
    
    <form method="post">
        <label>Produktname</label>
        <input name="product" required placeholder="z.B. Mango Ice Blast">

        <label>Preis (CHF)</label>
        <input name="price" type="number" step="0.01" required placeholder="19.90">

        <label>Nikotin (mg/ml)</label>
        <input name="nicotine" type="number" required placeholder="20">

        <button type="submit">Barcode generieren & herunterladen</button>
    </form>
</body>
</html>
    """

@app.route('/detail')
def detail():
    sn = request.args.get('sn')
    if not sn or sn not in details:
        return "<h2>Seriennummer nicht gefunden.</h2>", 404

    info = details[sn]
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="de">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>LuxeFinds – Produktdetail</title>
        <style>
            body { font-family:system-ui,sans-serif; background:#f8fafc; padding:30px; text-align:center; }
            h1 { color:#6366f1; }
            .card { background:white; max-width:500px; margin:30px auto; padding:25px; border-radius:16px; box-shadow:0 8px 25px rgba(0,0,0,0.12); }
            .label { font-weight:bold; color:#1e293b; margin:12px 0 4px; font-size:1.1rem; }
            .value { font-size:1.4rem; color:#6366f1; margin-bottom:16px; }
            .buttons { margin-top:30px; display:flex; gap:16px; justify-content:center; flex-wrap:wrap; }
            .btn { padding:14px 28px; font-size:1.1rem; border-radius:10px; cursor:pointer; text-decoration:none; color:white; }
            .add { background:#10b981; }
            .sell { background:#ef4444; }
            .btn:hover { opacity:0.9; }
        </style>
    </head>
    <body>
        <h1>LuxeFinds Vape Detail</h1>
        <div class="card">
            <div class="label">Produkt</div>
            <div class="value">{{ product }}</div>

            <div class="label">Preis</div>
            <div class="value">CHF {{ "%.2f"|format(price) }}</div>

            <div class="label">Nikotin</div>
            <div class="value">{{ nicotine }} mg/ml</div>

            <div class="label">Generiert am</div>
            <div class="value">{{ date }}</div>

            <div class="label">Seriennummer</div>
            <div class="value">{{ sn }}</div>

            <div class="buttons">
                <a href="#" class="btn add">Zum Lager hinzufügen</a>
                <a href="#" class="btn sell">Als verkauft markieren</a>
            </div>
        </div>
        <p style="color:#64748b; margin-top:40px;">(Buttons werden später mit deinem Lager-System verbunden)</p>
    </body>
    </html>
    """, product=info['product'], price=info['price'], nicotine=info['nicotine'], date=info['date'], sn=sn)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
