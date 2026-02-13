from flask import Flask, request, send_file, render_template_string, redirect
import io
import barcode
from barcode.writer import ImageWriter
import datetime
import random
import string
from PIL import Image, ImageDraw, ImageFont

app = Flask(__name__)

# Temporärer Speicher
details = {}

def generate_serial_number():
    # kürzere Seriennummer → kürzerer Barcode
    return ''.join(random.choices(string.digits, k=12))


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        product = request.form.get('product', '').strip()
        price = request.form.get('price', '').strip()
        nicotine = request.form.get('nicotine', '').strip()

        if product and price and nicotine:
            try:
                price_float = float(price)
                nicotine_int = int(float(nicotine))

                sn = generate_serial_number()

                # kurzer Scan-Link
                base_url = request.host_url.rstrip('/')
                barcode_data = f"{base_url}/s/{sn}"

                # Infos speichern
                details[sn] = {
                    'product': product,
                    'price': price_float,
                    'nicotine': nicotine_int,
                    'date': datetime.date.today().strftime('%d.%m.%Y')
                }

                # Barcode erzeugen
                code128 = barcode.get('code128', barcode_data, writer=ImageWriter())

                options = {
                    'write_text': False,
                    'module_width': 1.2,
                    'module_height': 6.0,
                    'dpi': 500,
                    'quiet_zone': 10,
                }

                buf = io.BytesIO()
                code128.write(buf, options=options)
                buf.seek(0)

                barcode_img = Image.open(buf).convert('RGB')

                # Platz für Seriennummer unten
                total_height = barcode_img.height + 80
                new_img = Image.new('RGB', (barcode_img.width, total_height), (255, 255, 255))
                draw = ImageDraw.Draw(new_img)
                new_img.paste(barcode_img, (0, 0))

                # Schrift
                try:
                    font = ImageFont.truetype("arial.ttf", 36)
                except:
                    font = ImageFont.load_default()

                bbox = draw.textbbox((0, 0), sn, font=font)
                text_width = bbox[2] - bbox[0]

                draw.text(
                    ((new_img.width - text_width) // 2, barcode_img.height + 10),
                    sn,
                    fill=(0, 0, 0),
                    font=font
                )

                final_buf = io.BytesIO()
                new_img.save(final_buf, format='PNG')
                final_buf.seek(0)

                return send_file(
                    final_buf,
                    mimetype='image/png',
                    as_attachment=True,
                    download_name=f'barcode_{sn}.png'
                )

            except Exception as e:
                return f"Fehler: {str(e)}", 500

    return """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>LuxeFinds Barcode</title>
<style>
body { font-family:system-ui; background:#f8fafc; padding:20px; max-width:480px; margin:auto; }
input,button { width:100%; padding:14px; margin-top:10px; border-radius:10px; border:1px solid #ccc; }
button { background:#6366f1; color:white; border:none; font-size:1.1rem; }
</style>
</head>
<body>

<h2>Barcode Generator</h2>

<form method="post">
<input name="product" placeholder="Produktname" required>
<input name="price" type="number" step="0.01" placeholder="Preis" required>
<input name="nicotine" type="number" placeholder="Nikotin mg" required>
<button type="submit">Barcode generieren</button>
</form>

</body>
</html>
"""


# kurzer Scan-Link → Redirect zur Detailseite
@app.route('/s/<sn>')
def scan(sn):
    return redirect(f"/detail?sn={sn}")


@app.route('/detail')
def detail():
    sn = request.args.get('sn')

    if not sn or sn not in details:
        return "<h2>Code nicht gefunden</h2>"

    info = details[sn]

    return render_template_string("""
    <html>
    <head>
    <meta charset="UTF-8">
    <style>
    body { font-family:system-ui; background:#f8fafc; padding:30px; text-align:center; }
    .card { background:white; padding:30px; border-radius:16px; max-width:400px; margin:auto; }
    .value { font-size:1.5rem; color:#6366f1; margin-bottom:20px; }
    </style>
    </head>
    <body>

    <div class="card">
        <h2>{{ product }}</h2>
        <div class="value">CHF {{ price }}</div>
        <div class="value">{{ nicotine }} mg/ml</div>
        <div class="value">{{ date }}</div>
        <div class="value">{{ sn }}</div>
    </div>

    </body>
    </html>
    """, product=info['product'], price=info['price'],
       nicotine=info['nicotine'], date=info['date'], sn=sn)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
