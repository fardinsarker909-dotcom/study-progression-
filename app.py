from flask import Flask, render_template, request, redirect, url_for
import json, os

app = Flask(__name__)
DATA_FILE = 'data.json'

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f: return json.load(f)
    return {"app_settings": {"boss_title": "Exam Preparation"}, "library": []}

def save_data(data):
    with open(DATA_FILE, 'w') as f: json.dump(data, f, indent=4)

data_store = load_data()

def calculate_all_progress():
    gt_pages, gc_pages = 0, 0
    if not data_store["library"]: return 0
    for book in data_store["library"]:
        b_total, b_current = 0, 0
        for chap in book["chapters"]:
            c_total = sum(l["total_pages"] for l in chap["lessons"])
            c_current = sum(l["current_page"] for l in chap["lessons"])
            chap["total_pages"], chap["current_page"] = c_total, c_current
            chap["percent"] = int((c_current / c_total * 100)) if c_total > 0 else 0
            b_total += c_total; b_current += c_current
        book["percent"] = int((b_current / b_total * 100)) if b_total > 0 else 0
        gt_pages += b_total; gc_pages += b_current
    save_data(data_store)
    return int((gc_pages / gt_pages * 100)) if gt_pages > 0 else 0

@app.route("/")
def home():
    score = calculate_all_progress()
    return render_template("index.html", library=data_store["library"], master_score=score, boss_title=data_store["app_settings"]["boss_title"])

@app.route("/library")
def library_view():
    calculate_all_progress()
    return render_template("library_view.html", library=data_store["library"])

@app.route("/rename_boss", methods=["POST"])
def rename_boss():
    data_store["app_settings"]["boss_title"] = request.form.get("new_title", "Exam Preparation")
    save_data(data_store); return redirect(url_for("home"))

@app.route("/book/<int:book_id>")
def book_detail(book_id):
    calculate_all_progress()
    book = next((b for b in data_store["library"] if b["id"] == book_id), None)
    return render_template("book_detail.html", book=book)

@app.route("/add_book", methods=["POST"])
def add_book():
    t = request.form.get("title")
    if t:
        new_id = max([b["id"] for b in data_store["library"]] + [-1]) + 1
        data_store["library"].append({"id": new_id, "title": t, "chapters": []})
        save_data(data_store)
    return redirect(url_for("home"))

@app.route("/update_book/<int:book_id>", methods=["POST"])
def update_book(book_id):
    book = next((b for b in data_store["library"] if b["id"] == book_id), None)
    if book: book["title"] = request.form.get("new_title"); save_data(data_store)
    return redirect(url_for("home"))

@app.route("/delete_book/<int:book_id>")
def delete_book(book_id):
    data_store["library"] = [b for b in data_store["library"] if b["id"] != book_id]
    save_data(data_store); return redirect(url_for("home"))

@app.route("/add_chapter/<int:book_id>", methods=["POST"])
def add_chapter(book_id):
    name = request.form.get("name")
    book = next((b for b in data_store["library"] if b["id"] == book_id), None)
    if book and name:
        new_id = max([c["id"] for c in book["chapters"]] + [-1]) + 1
        book["chapters"].append({"id": new_id, "name": name, "lessons": []})
        save_data(data_store)
    return redirect(url_for("book_detail", book_id=book_id))

@app.route("/update_chapter/<int:book_id>/<int:chap_id>", methods=["POST"])
def update_chapter(book_id, chap_id):
    book = next((b for b in data_store["library"] if b["id"] == book_id), None)
    if book:
        chap = next((c for c in book["chapters"] if c["id"] == chap_id), None)
        if chap: chap["name"] = request.form.get("name"); save_data(data_store)
    return redirect(url_for("book_detail", book_id=book_id))

@app.route("/delete_chapter/<int:book_id>/<int:chap_id>")
def delete_chapter(book_id, chap_id):
    book = next((b for b in data_store["library"] if b["id"] == book_id), None)
    if book: book["chapters"] = [c for c in book["chapters"] if c["id"] != chap_id]; save_data(data_store)
    return redirect(url_for("book_detail", book_id=book_id))

@app.route("/add_lesson/<int:book_id>/<int:chap_id>", methods=["POST"])
def add_lesson(book_id, chap_id):
    name, pgs = request.form.get("name"), request.form.get("total_pages")
    book = next((b for b in data_store["library"] if b["id"] == book_id), None)
    if book and name and pgs:
        chap = next((c for c in book["chapters"] if c["id"] == chap_id), None)
        if chap:
            new_id = max([l["id"] for l in chap["lessons"]] + [-1]) + 1
            chap["lessons"].append({"id": new_id, "name": name, "current_page": 0, "total_pages": int(pgs), "is_completed": False})
            save_data(data_store)
    return redirect(url_for("book_detail", book_id=book_id))

@app.route("/update_lesson_page/<int:book_id>/<int:chap_id>/<int:les_id>", methods=["POST"])
def update_lesson_page(book_id, chap_id, les_id):
    book = next((b for b in data_store["library"] if b["id"] == book_id), None)
    if book:
        chap = next((c for c in book["chapters"] if c["id"] == chap_id), None)
        if chap:
            les = next((l for l in chap["lessons"] if l["id"] == les_id), None)
            if les:
                val = int(request.form.get("current_page", 0))
                les["current_page"] = min(val, les["total_pages"])
                les["is_completed"] = (les["current_page"] >= les["total_pages"])
                save_data(data_store)
    return redirect(url_for("book_detail", book_id=book_id))

@app.route("/update_lesson_full/<int:book_id>/<int:chap_id>/<int:les_id>", methods=["POST"])
def update_lesson_full(book_id, chap_id, les_id):
    book = next((b for b in data_store["library"] if b["id"] == book_id), None)
    if book:
        chap = next((c for c in book["chapters"] if c["id"] == chap_id), None)
        if chap:
            les = next((l for l in chap["lessons"] if l["id"] == les_id), None)
            if les:
                les["name"] = request.form.get("name")
                les["total_pages"] = int(request.form.get("total_pages"))
                les["is_completed"] = (les["current_page"] >= les["total_pages"])
                save_data(data_store)
    return redirect(url_for("book_detail", book_id=book_id))

@app.route("/toggle_lesson/<int:book_id>/<int:chap_id>/<int:les_id>")
def toggle_lesson(book_id, chap_id, les_id):
    book = next((b for b in data_store["library"] if b["id"] == book_id), None)
    if book:
        chap = next((c for c in book["chapters"] if c["id"] == chap_id), None)
        if chap:
            les = next((l for l in chap["lessons"] if l["id"] == les_id), None)
            if les:
                les["is_completed"] = not les["is_completed"]
                les["current_page"] = les["total_pages"] if les["is_completed"] else 0
                save_data(data_store)
    return redirect(url_for("book_detail", book_id=book_id))

@app.route("/delete_lesson/<int:book_id>/<int:chap_id>/<int:les_id>")
def delete_lesson(book_id, chap_id, les_id):
    book = next((b for b in data_store["library"] if b["id"] == book_id), None)
    if book:
        chap = next((c for c in book["chapters"] if c["id"] == chap_id), None)
        if chap:
            chap["lessons"] = [l for l in chap["lessons"] if l["id"] != les_id]
            save_data(data_store)
    return redirect(url_for("book_detail", book_id=book_id))

if __name__ == "__main__":
    app.run(debug=True)