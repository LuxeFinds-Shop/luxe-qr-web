from flask import Flask, request, send_file, render_template_string
import io
import barcode
from barcode.writer import ImageWriter
import datetime
import random
import string

app = Flask(__name__)

# Dummy-Speicher für die Detail-Seite (in Produktion wäre das eine Datenbank)
details = {}

def generate_serial_number():
    """Erzeugt eine 20-stellige numerische Seriennummer"""
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

                # Seriennummer generieren
                sn = generate_serial_number()

                # Daten, die im Barcode kodiert werden → URL + SN
                base_url = request.host_url.rstrip('/')
                barcode_data = f"{base_url}/detail?sn={sn}"

                # Zusätzliche Infos speichern (für die Detail-Seite)
                details[sn] = {
                    'product': product,
                    'price': price_float,
                    'nicotine': nicotine_int,
                    'date': datetime.date.today().strftime('%d.%m.%Y')
                }

                # Code128 Barcode erstellen
                code128 = barcode.get('code128', barcode_data, writer=ImageWriter())

                # Optionen → größerer, breiterer Barcode (nicht so lang)
                options = {
                    'write_text': False,           # Kein Text direkt unter den Bars (wir machen es selbst)
                    'module_width': 0.6,           # Dickere Balken → Barcode wird breiter & kürzer
                    'dpi': 350,
                    'quiet_zone': 12,
                    'font_size': 0,                # Kein Font (wir setzen Text manuell)
                }

                # Barcode als Bild generieren
                barcode_img_buf = io.BytesIO()
                code128.write(barcode_img_buf, options=options)
                barcode_img_buf.seek(0)

                # Neues Bild erstellen: Barcode + Seriennummer + generierter Text unten
                from PIL import Image, ImageDraw, ImageFont
                barcode_img = Image.open(barcode_img_buf).convert('RGB')

                # Größe des neuen Bildes (Barcode + Platz für Text unten)
                total_height = barcode_img.height + 140  # Mehr Platz unten
                new_img = Image.new('RGB', (barcode_img.width, total_height), (255, 255, 255))
                draw = ImageDraw.Draw(new_img)

                # Barcode einfügen (zentriert)
                new_img.paste(barcode_img, ((new_img.width - barcode_img.width) // 2, 20))

                # Seriennummer + Text darunter schreiben
                try:
                    font = ImageFont.truetype("arial.ttf", 28)
                except:
                    font = ImageFont.load_default()

                # Haupttext unter Barcode
                text_lines = [
                    f"LuxeFinds | {product}",
                    f"CHF {price_float:.2f} | {nicotine_int} mg/ml",
                    f"Datum: {datetime.date.today().strftime('%d.%m.%Y')}",
                    f"SN: {sn}"
                ]

                y_pos = barcode_img.height + 30
                for line in text_lines:
                    bbox = draw.textbbox((0, 0), line, font=font)
                    text_width = bbox[2] - bbox[0]
                    draw.text(((new_img.width - text_width) // 2, y_pos), line, fill=(0, 0, 0), font=font)
                    y_pos += 36  # Zeilenabstand

                # In Memory speichern und zurückgeben
                final_buf = io.BytesIO()
                new_img.save(final_buf, format='PNG')
                final_buf.seek(0)

                return send_file(
                    final_buf,
                    mimetype='image/png',
                    as_attachment=True,
                    download_name=f'luxe_barcode_{product.replace(" ", "_")[:30]}_{nicotine}mg.png'
                )

            except Exception as e:
                return f"Fehler beim Generieren: {str(e)}", 500

    # HTML-Formular
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
    <p class="hint">Erzeugt einen dicken Code128-Barcode mit Seriennummer.<br>Scan → öffnet Detail-Seite mit allen Infos.</p>
    
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
        return "Seriennummer nicht gefunden oder abgelaufen.", 404

    info = details[sn]
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="de">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Produktdetail - LuxeFinds</title>
        <style>
            body { font-family: system-ui, sans-serif; background:#f8fafc; padding:30px; max-width:600px; margin:auto; text-align:center; }
            h1 { color:#6366f1; }
            .card { background:white; padding:24px; border-radius:12px; box-shadow:0 4px 15px rgba(0,0,0,0.1); margin-top:20px; }
            .label { font-weight:bold; color:#1e293b; margin-top:12px; }
            .value { font-size:1.3rem; color:#6366f1; }
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
        </div>
    </body>
    </html>
    """, product=info['product'], price=info['price'], nicotine=info['nicotine'], date=info['date'], sn=sn)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
