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

WEBHOOK = "DEIN_WEBHOOK_HIER"

DB = "database.db"


# Datenbank erstellen
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS products (
        sn TEXT PRIMARY KEY,
        product TEXT,
        price REAL,
        nicotine INTEGER,
        date TEXT
    )
    """)
    conn.commit()
    conn.close()


init_db()


def generate_serial_number():
    return str(random.randint(100000, 999999))  # 6-stellig → sehr kurzer Barcode


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
        price = float(request.form.get("price"))
        nicotine = int(request.form.get("nicotine"))

        sn = generate_serial_number()

        save_product(sn, product, price, nicotine)

        # Barcode enthält nur SN
        barcode_data = sn

        code128 = barcode.get("code128", barcode_data, writer=ImageWriter())

        options = {
            "write_text": False,
            "module_width": 0.4,
            "module_height": 8,
            "quiet_zone": 3,
            "dpi": 300,
        }

        buf = io.BytesIO()
        code128.write(buf, options=options)
        buf.seek(0)

        barcode_img = Image.open(buf).convert("RGB")

        total_height = barcode_img.height + 60
        new_img = Image.new("RGB", (barcode_img.width, total_height), (255, 255, 255))
        draw = ImageDraw.Draw(new_img)
        new_img.paste(barcode_img, (0, 0))

        try:
            font = ImageFont.truetype("arial.ttf", 28)
        except:
            font = ImageFont.load_default()

        draw.text((10, barcode_img.height + 10), sn, fill=(0, 0, 0), font=font)

        final_buf = io.BytesIO()
        new_img.save(final_buf, format="PNG")
        final_buf.seek(0)

        send_to_discord(final_buf.getvalue())
        final_buf.seek(0)

        return send_file(final_buf, mimetype="image/png")

    return """
    <h2>Barcode erstellen</h2>
    <form method="post">
    Produkt:<br><input name="product"><br>
    Preis:<br><input name="price"><br>
    Nikotin:<br><input name="nicotine"><br><br>
    <button type="submit">Generieren</button>
    </form>
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
    <h1>{{product}}</h1>
    Preis: CHF {{price}}<br>
    Nikotin: {{nicotine}} mg<br>
    SN: {{sn}}
    """, product=product[1], price=product[2],
       nicotine=product[3], sn=product[0])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
