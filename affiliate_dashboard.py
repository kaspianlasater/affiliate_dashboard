from flask import Flask, request, redirect, render_template_string, session, url_for
import pandas as pd
from datetime import datetime
import requests, os

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "supersecretkey")

ADMIN_KEY = os.environ.get("ADMIN_KEY", "letmein")
DATA_FILE = "clicks.csv"

def log_click(slug, ip, location):
    df = pd.DataFrame([{
        "timestamp": datetime.now().isoformat(),
        "slug": slug,
        "ip": ip,
        "country": location.get("country", ""),
        "region": location.get("regionName", ""),
        "city": location.get("city", "")
    }])
    df.to_csv(DATA_FILE, mode="a", index=False, header=not os.path.exists(DATA_FILE))

@app.route("/go/<slug>")
def go(slug):
    # read or create links file
    if not os.path.exists("links.csv"):
        pd.DataFrame(columns=["slug", "url"]).to_csv("links.csv", index=False)
        return "No links configured yet."
    links = pd.read_csv("links.csv").set_index("slug").to_dict()["url"]
    url = links.get(slug)
    if not url:
        return "Link not found", 404

    # get IP and location
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    try:
        r = requests.get(f"http://ip-api.com/json/{ip}").json()
    except:
        r = {}
    log_click(slug, ip, r)
    return redirect(url)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("key") == ADMIN_KEY:
            session["admin"] = True
            return redirect(url_for("stats"))
        else:
            return "Invalid key", 403
    return render_template_string("""
        <form method="post">
            <input type="password" name="key" placeholder="Admin key"/>
            <button type="submit">Login</button>
        </form>
    """)

@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("login"))

@app.route("/add", methods=["GET", "POST"])
def add_link():
    if not session.get("admin"):
        return redirect(url_for("login"))
    if request.method == "POST":
        slug = request.form["slug"]
        url = request.form["url"]
        df = pd.DataFrame([[slug, url]], columns=["slug", "url"])
        header = not os.path.exists("links.csv")
        df.to_csv("links.csv", mode="a", index=False, header=header)
        return "Link added! Go back to /stats."
    return render_template_string("""
        <form method="post">
            Slug: <input name="slug"><br>
            URL: <input name="url"><br>
            <button type="submit">Add</button>
        </form>
    """)

@app.route("/stats")
def stats():
    if not session.get("admin"):
        return redirect(url_for("login"))
    if not os.path.exists(DATA_FILE):
        return "No data yet."
    df = pd.read_csv(DATA_FILE)
    table_html = df.tail(20).to_html(index=False)
    return f"<h1>Recent Clicks</h1>{table_html}<br><a href='/add'>Add Link</a> | <a href='/logout'>Logout</a>"

import os
port = int(os.environ.get("PORT", 8080))
app.run(host="0.0.0.0", port=port)

