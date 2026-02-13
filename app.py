from flask import Flask, request, send_file, render_template_string, redirect
import io
import barcode
from barcode.writer import ImageWriter
import datetime
import random
import sqlite3
from PIL import Image, ImageDraw, ImageFont
import requests

app = Flask(__name__)

WEBHOOK = "https://discord.com/api/webhooks/1466869469543530528/p38DSMKoMNJAG5m9YjMS1WZFvZfe5x6oFSjlI-rAKUUgZw6k8Z9f-jiDcOn4I0n_0JGx"
DB = "database.db"


# Datenbank erstellen
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS products (
            sn TEXT PRIMARY KEY,
            product TEXT,
            price TEXT,
            nicotine TEXT,
            date TEXT
        )
    """)
    conn.commit()
    conn.close()


init_db()


def generate_serial_number():
    return str(random.randint(100000, 999999))


def save_product(sn, product, price, nicotine):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT INTO products VALUES (?, ?, ?, ?, ?)",
              (sn, product, price, nicotine,
               datetime.date.today().strftime("%d.%m.%Y")))
    conn.commit()
    conn.close()


def get_product(sn):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM products WHERE sn=?", (sn,))
    row = c.fetchone()
    conn.close()
    return row


def send_to_discord(image_bytes):
    try:
        files = {"file": ("barcode.png", image_bytes, "image/png")}
        requests.post(WEBHOOK, files=files)
    except:
        pass


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        product = request.form.get("product")
        price = request.form.get("price")
        nicotine = request.form.get("nicotine")

        sn = generate_serial_number()
        save_product(sn, product, price, nicotine)

        # Barcode enthält Link
        base_url = request.host_url.rstrip('/')
        barcode_data = f"{base_url}/s/{sn}"

        code128 = barcode.get("code128", barcode_data, writer=ImageWriter())

        options = {
            "write_text": False,
            "module_width": 0.5,
            "module_height": 35,
            "quiet_zone": 6,
            "dpi": 300,
        }

        buf = io.BytesIO()
        code128.write(buf, options=options)
        buf.seek(0)

        barcode_img = Image.open(buf).convert("RGB")

        total_height = barcode_img.height + 70
        new_img = Image.new("RGB", (barcode_img.width, total_height), (255, 255, 255))
        draw = ImageDraw.Draw(new_img)

        new_img.paste(barcode_img, (0, 0))

        try:
            font = ImageFont.truetype("arial.ttf", 30)
        except:
            font = ImageFont.load_default()

        draw.text((20, barcode_img.height + 10), sn, fill=(0, 0, 0), font=font)

        final_buf = io.BytesIO()
        new_img.save(final_buf, format="PNG")
        final_buf.seek(0)

        send_to_discord(final_buf.getvalue())
        final_buf.seek(0)

        return send_file(final_buf, mimetype="image/png")

    return """
<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>LuxeFinds Barcode System</title>

<style>
body {
    font-family: system-ui, sans-serif;
    background: #f1f5f9;
    padding: 20px;
}

.container {
    max-width: 500px;
    margin: auto;
}

.header {
    font-size: 28px;
    font-weight: 700;
    color: #4f46e5;
    text-align: center;
    margin-bottom: 25px;
}

.card {
    background: white;
    padding: 25px;
    border-radius: 14px;
    box-shadow: 0 8px 25px rgba(0,0,0,0.08);
}

label {
    font-weight: 600;
    display: block;
    margin-top: 15px;
}

input {
    width: 100%;
    padding: 14px;
    margin-top: 6px;
    border-radius: 10px;
    border: 1px solid #cbd5e1;
    font-size: 1rem;
}

button {
    width: 100%;
    margin-top: 20px;
    padding: 15px;
    background: #6366f1;
    border: none;
    border-radius: 12px;
    color: white;
    font-size: 1.1rem;
    cursor: pointer;
}

button:hover {
    background: #4f46e5;
}
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
            <input name="price" required>

            <label>Nikotin (mg/ml)</label>
            <input name="nicotine" required>

            <button type="submit">Barcode generieren</button>
        </form>
    </div>
</div>
</body>
</html>
"""


@app.route("/s/<sn>")
def scan(sn):
    return redirect(f"/detail?sn={sn}")


@app.route("/detail")
def detail():
    sn = request.args.get("sn")
    product = get_product(sn)

    if not product:
        return "Nicht gefunden"

    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
body {
    font-family: system-ui, sans-serif;
    background: #f1f5f9;
    padding: 30px;
}

.card {
    max-width: 500px;
    margin: auto;
    background: white;
    padding: 30px;
    border-radius: 14px;
    box-shadow: 0 8px 25px rgba(0,0,0,0.08);
    text-align: center;
}

.title {
    font-size: 24px;
    font-weight: 700;
    color: #4f46e5;
    margin-bottom: 20px;
}

.value {
    font-size: 20px;
    margin-bottom: 15px;
}
</style>
</head>

<body>
<div class="card">
<div class="title">{{product}}</div>
<div class="value">Preis: CHF {{price}}</div>
<div class="value">Nikotin: {{nicotine}} mg</div>
<div class="value">SN: {{sn}}</div>
</div>
</body>
</html>
""", product=product[1], price=product[2], nicotine=product[3], sn=product[0])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
