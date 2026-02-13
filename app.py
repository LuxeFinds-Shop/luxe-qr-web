from flask import Flask, request, send_file, render_template_string
import io
import barcode
from barcode.writer import ImageWriter
import datetime
import random
import string
from PIL import Image, ImageDraw, ImageFont

app = Flask(__name__)

# Temporärer Speicher (später echte DB)
details = {}

def generate_serial_number():
    return ''.join(random.choices(string.digits, k=20))

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

                # Code128 – extrem kurz & dick
                code128 = barcode.get('code128', barcode_data, writer=ImageWriter())

                options = {
                    'write_text': False,           # Kein Text unter den Balken
                    'module_width': 0.8,           # Sehr dicke Balken → Barcode wird extrem breit/kurz
                    'module_height': 10.0,         # Nicht zu hoch
                    'dpi': 450,
                    'quiet_zone': 15,              # Mehr Rand links/rechts
                }

                buf = io.BytesIO()
                code128.write(buf, options=options)
                buf.seek(0)

                # PIL Bild laden & erweitern für SN unten
                barcode_img = Image.open(buf).convert('RGB')
                total_height = barcode_img.height + 120  # Nur Platz für SN
                new_img = Image.new('RGB', (barcode_img.width, total_height), (255, 255, 255))
                draw = ImageDraw.Draw(new_img)
                new_img.paste(barcode_img, ((new_img.width - barcode_img.width) // 2, 20))

                # Große, klare Schrift für SN
                try:
                    font = ImageFont.truetype("arial.ttf", 36)  # Groß & lesbar
                except:
                    font = ImageFont.load_default()

                # Nur Seriennummer zentriert unten
                sn_text = f"SN: {sn}"
                bbox = draw.textbbox((0, 0), sn_text, font=font)
                w = bbox[2] - bbox[0]
                draw.text(((new_img.width - w) // 2, barcode_img.height + 40), sn_text, fill=(0, 0, 0), font=font)

                # Finales Bild
                final_buf = io.BytesIO()
                new_img.save(final_buf, format='PNG')
                final_buf.seek(0)

                return send_file(
                    final_buf,
                    mimetype='image/png',
                    as_attachment=True,
                    download_name=f'luxe_barcode_{product.replace(" ", "_")[:20]}_{nicotine}mg.png'
                )

            except Exception as e:
                return f"Fehler: {str(e)}", 500

    # Startseite – Formular
    return """
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LuxeFinds Barcode</title>
    <style>
        body { font-family:system-ui,sans-serif; background:#f8fafc; padding:20px; max-width:480px; margin:auto; }
        h1 { color:#6366f1; text-align:center; margin-bottom:20px; }
        label { display:block; margin:16px 0 6px; font-weight:600; }
        input { width:100%; padding:14px; border:1px solid #cbd5e1; border-radius:12px; font-size:1.05rem; }
        button { width:100%; background:#6366f1; color:white; border:none; padding:16px; font-size:1.15rem; border-radius:12px; margin-top:24px; cursor:pointer; }
        button:hover { background:#4f46e5; }
        .hint { color:#64748b; text-align:center; margin-top:24px; font-size:0.95rem; }
    </style>
</head>
<body>
    <h1>LuxeFinds Barcode Generator</h1>
    <p class="hint">Kurzer, dicker Barcode mit Seriennummer unten.<br>Scannen → zeigt Infos + Lager-Optionen.</p>
    
    <form method="post">
        <label>Produktname</label>
        <input name="product" required placeholder="z.B. Mango Ice">

        <label>Preis (CHF)</label>
        <input name="price" type="number" step="0.01" required placeholder="19.90">

        <label>Nikotin (mg/ml)</label>
        <input name="nicotine" type="number" required placeholder="20">

        <button type="submit">Barcode generieren</button>
    </form>
</body>
</html>
    """

@app.route('/detail')
def detail():
    sn = request.args.get('sn')
    if not sn or sn not in details:
        return "<h2>Code nicht gefunden.</h2>", 404

    info = details[sn]
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="de">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>LuxeFinds Detail</title>
        <style>
            body { font-family:system-ui,sans-serif; background:#f8fafc; padding:30px; text-align:center; }
            h1 { color:#6366f1; margin-bottom:30px; }
            .card { background:white; max-width:500px; margin:auto; padding:30px; border-radius:16px; box-shadow:0 10px 30px rgba(0,0,0,0.1); }
            .label { font-weight:600; color:#1e293b; margin:16px 0 6px; font-size:1.2rem; }
            .value { font-size:1.5rem; color:#6366f1; margin-bottom:20px; }
            .buttons { margin-top:40px; display:flex; gap:20px; justify-content:center; flex-wrap:wrap; }
            .btn { padding:16px 32px; font-size:1.2rem; border-radius:12px; color:white; text-decoration:none; cursor:pointer; }
            .add { background:#10b981; }
            .sell { background:#ef4444; }
            .btn:hover { opacity:0.9; }
        </style>
    </head>
    <body>
        <h1>LuxeFinds Vape</h1>
        <div class="card">
            <div class="label">Produkt</div>
            <div class="value">{{ product }}</div>

            <div class="label">Preis</div>
            <div class="value">CHF {{ "%.2f"|format(price) }}</div>

            <div class="label">Nikotin</div>
            <div class="value">{{ nicotine }} mg/ml</div>

            <div class="label">Generiert</div>
            <div class="value">{{ date }}</div>

            <div class="label">Seriennummer</div>
            <div class="value">{{ sn }}</div>

            <div class="buttons">
                <a href="#" class="btn add">Zum Lager hinzufügen</a>
                <a href="#" class="btn sell">Als verkauft markieren</a>
            </div>
        </div>
    </body>
    </html>
    """, product=info['product'], price=info['price'], nicotine=info['nicotine'], date=info['date'], sn=sn)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
