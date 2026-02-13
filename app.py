from flask import Flask, request, send_file, render_template_string, redirect
import io
import barcode
from barcode.writer import ImageWriter
import datetime
import random
import string
from PIL import Image, ImageDraw, ImageFont
import requests

app = Flask(__name__)

# Speicher (ohne Datenbank)
details = {}

# Discord Webhook
WEBHOOK = "https://discord.com/api/webhooks/1466869469543530528/p38DSMKoMNJAG5m9YjMS1WZFvZfe5x6oFSjlI-rAKUUgZw6k8Z9f-jiDcOn4I0n_0JGx"


def generate_serial_number():
    # kurze Codes wie A7F2K91
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=7))


def send_to_discord(image_bytes):
    try:
        files = {
            "file": ("barcode.png", image_bytes, "image/png")
        }
        requests.post(WEBHOOK, files=files)
    except Exception as e:
        print("Discord Fehler:", e)


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

                details[sn] = {
                    'product': product,
                    'price': price_float,
                    'nicotine': nicotine_int,
                    'date': datetime.date.today().strftime('%d.%m.%Y')
                }

                # kurzer Link im Barcode
                base_url = request.host_url.rstrip('/')
                barcode_data = f"{base_url}/s/{sn}"

                code128 = barcode.get('code128', barcode_data, writer=ImageWriter())

                options = {
                    'write_text': False,
                    'module_width': 0.45,
                    'module_height': 8,
                    'quiet_zone': 4,
                    'dpi': 300,
                }

                buf = io.BytesIO()
                code128.write(buf, options=options)
                buf.seek(0)

                barcode_img = Image.open(buf).convert('RGB')

                total_height = barcode_img.height + 70
                new_img = Image.new('RGB', (barcode_img.width, total_height), (255, 255, 255))
                draw = ImageDraw.Draw(new_img)
                new_img.paste(barcode_img, (0, 10))

                try:
                    font = ImageFont.truetype("arial.ttf", 30)
                except:
                    font = ImageFont.load_default()

                bbox = draw.textbbox((0, 0), sn, font=font)
                w = bbox[2] - bbox[0]

                draw.text(
                    ((new_img.width - w) // 2, barcode_img.height + 15),
                    sn,
                    fill=(0, 0, 0),
                    font=font
                )

                final_buf = io.BytesIO()
                new_img.save(final_buf, format='PNG')
                final_buf.seek(0)

                # Discord senden
                send_to_discord(final_buf.getvalue())
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
<title>LuxeFinds Barcode</title>

<style>
body { font-family:system-ui,sans-serif; background:#f8fafc; padding:20px; max-width:480px; margin:auto; }
h1 { color:#6366f1; text-align:center; margin-bottom:20px; }
label { display:block; margin:16px 0 6px; font-weight:600; }
input { width:100%; padding:14px; border:1px solid #cbd5e1; border-radius:12px; font-size:1.05rem; }
button { width:100%; background:#6366f1; color:white; border:none; padding:16px; font-size:1.15rem; border-radius:12px; margin-top:24px; cursor:pointer; }
button:hover { background:#4f46e5; }
</style>
</head>

<body>
<h1>LuxeFinds Barcode Generator</h1>

<form method="post">
<label>Produktname</label>
<input name="product" required>

<label>Preis (CHF)</label>
<input name="price" type="number" step="0.01" required>

<label>Nikotin (mg/ml)</label>
<input name="nicotine" type="number" required>

<button type="submit">Barcode generieren</button>
</form>

</body>
</html>
    """


@app.route('/s/<sn>')
def scan_redirect(sn):
    return redirect(f"/detail?sn={sn}")


@app.route('/detail')
def detail():
    sn = request.args.get('sn')

    if not sn or sn not in details:
        return "<h2>Code nicht gefunden.</h2>", 404

    info = details[sn]

    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
body { font-family:system-ui,sans-serif; background:#f8fafc; padding:30px; text-align:center; }
.card { background:white; max-width:500px; margin:auto; padding:30px; border-radius:16px; box-shadow:0 10px 30px rgba(0,0,0,0.1); }
.value { font-size:1.4rem; margin:12px 0; }
</style>
</head>

<body>
<div class="card">
<h2>{{ product }}</h2>
<div class="value">Preis: CHF {{ price }}</div>
<div class="value">Nikotin: {{ nicotine }} mg/ml</div>
<div class="value">Datum: {{ date }}</div>
<div class="value">SN: {{ sn }}</div>
</div>
</body>
</html>
    """, product=info['product'], price=info['price'],
       nicotine=info['nicotine'], date=info['date'], sn=sn)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
