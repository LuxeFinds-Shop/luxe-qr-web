from flask import Flask, request, send_file, render_template_string
import io
import barcode
from barcode.writer import ImageWriter
import datetime
import random
import string
from PIL import Image, ImageDraw, ImageFont
import requests

app = Flask(__name__)

details = {}

WEBHOOK = "https://discord.com/api/webhooks/1466869469543530528/p38DSMKoMNJAG5m9YjMS1WZFvZfe5x6oFSjlI-rAKUUgZw6k8Z9f-jiDcOn4I0n_0JGx"

def generate_serial_number():
    return ''.join(random.choices(string.digits, k=10))


def send_to_discord(image_bytes, sn, product, price, nicotine):
    try:
        files = {
            "file": ("barcode.png", image_bytes, "image/png")
        }

        data = {
            "content": f"📦 Neuer Barcode erstellt\n"
                       f"Produkt: {product}\n"
                       f"Preis: CHF {price}\n"
                       f"Nikotin: {nicotine} mg\n"
                       f"SN: {sn}"
        }

        requests.post(WEBHOOK, data=data, files=files)

    except Exception as e:
        print("Discord Fehler:", e)


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

                barcode_data = sn

                details[sn] = {
                    'product': product,
                    'price': price_float,
                    'nicotine': nicotine_int,
                    'date': datetime.date.today().strftime('%d.%m.%Y')
                }

                code128 = barcode.get('code128', barcode_data, writer=ImageWriter())

                options = {
                    'write_text': False,
                    'module_width': 0.5,
                    'module_height': 8,
                    'quiet_zone': 4,
                    'dpi': 300,
                }

                buf = io.BytesIO()
                code128.write(buf, options=options)
                buf.seek(0)

                barcode_img = Image.open(buf).convert('RGB')

                total_height = barcode_img.height + 80
                new_img = Image.new('RGB', (barcode_img.width, total_height), (255, 255, 255))
                draw = ImageDraw.Draw(new_img)
                new_img.paste(barcode_img, (0, 10))

                try:
                    font = ImageFont.truetype("arial.ttf", 36)
                except:
                    font = ImageFont.load_default()

                bbox = draw.textbbox((0, 0), sn, font=font)
                w = bbox[2] - bbox[0]

                draw.text(
                    ((new_img.width - w) // 2, barcode_img.height + 20),
                    sn,
                    fill=(0, 0, 0),
                    font=font
                )

                final_buf = io.BytesIO()
                new_img.save(final_buf, format='PNG')
                final_buf.seek(0)

                # Discord senden
                send_to_discord(final_buf.getvalue(), sn, product, price_float, nicotine_int)
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
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>LuxeFinds System</title>

<style>
body { font-family:system-ui; background:#f1f5f9; padding:20px; }
.container { max-width:500px; margin:auto; }
.header { font-size:28px; font-weight:700; color:#4f46e5; text-align:center; margin-bottom:25px; }
.card { background:white; padding:25px; border-radius:14px; box-shadow:0 8px 25px rgba(0,0,0,0.08); }
label { font-weight:600; display:block; margin-top:15px; }
input { width:100%; padding:14px; margin-top:6px; border-radius:10px; border:1px solid #cbd5e1; font-size:1rem; }
button { width:100%; margin-top:20px; padding:15px; background:#6366f1; border:none; border-radius:12px; color:white; font-size:1.1rem; cursor:pointer; }
button:hover { background:#4f46e5; }
.footer { text-align:center; color:#64748b; margin-top:20px; font-size:0.9rem; }
</style>
</head>

<body>
<div class="container">
<div class="header">LuxeFinds Barcode System</div>
<div class="card">
<form method="post">

<label>Produktname</label>
<input name="product" required>

<label>Preis (CHF)</label>
<input name="price" type="number" step="0.01" required>

<label>Nikotin (mg/ml)</label>
<input name="nicotine" type="number" required>

<button type="submit">Barcode generieren</button>

</form>
</div>

<div class="footer">
Scan → Detailseite anzeigen
</div>

</div>
</body>
</html>
    """


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
