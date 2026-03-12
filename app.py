from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import json, os, random, string

app = Flask(__name__)
app.secret_key = 'study_tracker_ultra_secure_9911'

DATA_FILE = 'data.json'
login_manager = LoginManager(app)
login_manager.login_view = "login"

# --- DATA PERSISTENCE ---
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            if "users" not in data: data = {"users": {}}
            return data
    return {"users": {}}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

data_store = load_data()

def init_user_data():
    return {
        "app_settings": {"boss_title": "KNOWLEDGE ARCHITECT"},
        "library": []
    }

# --- AUTHENTICATION ---
class User(UserMixin):
    def __init__(self, username):
        self.id = str(username)
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    if "users" in data_store and user_id in data_store["users"]:
        return User(user_id)
    return None

# --- PROGRESS LOGIC ---
def calculate_all_progress(username):
    user_lib = data_store["users"][username]["data"]["library"]
    gt_pages, gc_pages = 0, 0
    if not user_lib: return 0
    for book in user_lib:
        b_total, b_current = 0, 0
        for chap in book.get("chapters", []):
            c_total = sum(int(l.get("total_pages", 0)) for l in chap.get("lessons", []))
            c_current = sum(int(l.get("current_page", 0)) for l in chap.get("lessons", []))
            chap["total_pages"], chap["current_page"] = c_total, c_current
            chap["percent"] = int((c_current / c_total * 100)) if c_total > 0 else 0
            b_total += c_total; b_current += c_current
        book["percent"] = int((b_current / b_total * 100)) if b_total > 0 else 0
        gt_pages += b_total; gc_pages += b_current
    save_data(data_store)
    return int((gc_pages / gt_pages * 100)) if gt_pages > 0 else 0

# --- NAVIGATION ROUTES ---
@app.route("/")
def home():
    if not current_user.is_authenticated:
        return redirect(url_for("guest_login"))
    uname = current_user.username
    if uname not in data_store["users"]: return redirect(url_for("logout"))
    score = calculate_all_progress(uname)
    user_data = data_store["users"][uname]["data"]
    return render_template("index.html", library=user_data["library"], master_score=score, boss_title=user_data["app_settings"]["boss_title"], username=uname)

@app.route("/library")
@login_required
def library_view():
    uname = current_user.username
    calculate_all_progress(uname)
    return render_template("library_view.html", library=data_store["users"][uname]["data"]["library"], username=uname)

@app.route("/book/<int:book_id>")
@login_required
def book_detail(book_id):
    uname = current_user.username
    calculate_all_progress(uname)
    user_lib = data_store["users"][uname]["data"]["library"]
    book = next((b for b in user_lib if b["id"] == book_id), None)
    return render_template("book_detail.html", book=book, username=uname)

# --- CREATION ROUTES (FIXED) ---
@app.route("/add_book", methods=["POST"])
@login_required
def add_book():
    uname = current_user.username
    t = request.form.get("title")
    if t:
        user_lib = data_store["users"][uname]["data"]["library"]
        new_id = max([b["id"] for b in user_lib] + [-1]) + 1
        user_lib.append({"id": new_id, "title": t, "chapters": [], "percent": 0})
        save_data(data_store)
    return redirect(url_for("home"))

@app.route("/add_chapter/<int:book_id>", methods=["POST"])
@login_required
def add_chapter(book_id):
    uname = current_user.username
    name = request.form.get("name")
    user_lib = data_store["users"][uname]["data"]["library"]
    book = next((b for b in user_lib if b["id"] == book_id), None)
    if book and name:
        new_id = max([c["id"] for c in book["chapters"]] + [-1]) + 1
        book["chapters"].append({"id": new_id, "name": name, "lessons": []})
        save_data(data_store)
    return redirect(url_for("book_detail", book_id=book_id))

@app.route("/add_lesson/<int:book_id>/<int:chap_id>", methods=["POST"])
@login_required
def add_lesson(book_id, chap_id):
    uname = current_user.username
    name, pgs = request.form.get("name"), request.form.get("total_pages")
    user_lib = data_store["users"][uname]["data"]["library"]
    book = next((b for b in user_lib if b["id"] == book_id), None)
    if book and name and pgs:
        chap = next((c for c in book["chapters"] if c["id"] == chap_id), None)
        if chap:
            new_id = max([l["id"] for l in chap["lessons"]] + [-1]) + 1
            chap["lessons"].append({"id": new_id, "name": name, "current_page": 0, "total_pages": int(pgs), "is_completed": False})
            save_data(data_store)
    return redirect(url_for("book_detail", book_id=book_id))

# --- EDITING & TOGGLING (FIXED) ---
@app.route("/update_book/<int:book_id>", methods=["POST"])
@login_required
def update_book(book_id):
    uname = current_user.username
    user_lib = data_store["users"][uname]["data"]["library"]
    book = next((b for b in user_lib if b["id"] == book_id), None)
    if book:
        book["title"] = request.form.get("new_title")
        save_data(data_store)
    return redirect(url_for("home"))

@app.route("/update_chapter/<int:book_id>/<int:chap_id>", methods=["POST"])
@login_required
def update_chapter(book_id, chap_id):
    uname = current_user.username
    user_lib = data_store["users"][uname]["data"]["library"]
    book = next((b for b in user_lib if b["id"] == book_id), None)
    if book:
        chap = next((c for c in book["chapters"] if c["id"] == chap_id), None)
        if chap:
            chap["name"] = request.form.get("name")
            save_data(data_store)
    return redirect(url_for("book_detail", book_id=book_id))

@app.route("/update_lesson_full/<int:book_id>/<int:chap_id>/<int:les_id>", methods=["POST"])
@login_required
def update_lesson_full(book_id, chap_id, les_id):
    uname = current_user.username
    user_lib = data_store["users"][uname]["data"]["library"]
    book = next((b for b in user_lib if b["id"] == book_id), None)
    if book:
        chap = next((c for c in book["chapters"] if c["id"] == chap_id), None)
        if chap:
            les = next((l for l in chap["lessons"] if l["id"] == les_id), None)
            if les:
                les["name"] = request.form.get("name")
                les["total_pages"] = int(request.form.get("total_pages"))
                save_data(data_store)
    return redirect(url_for("book_detail", book_id=book_id))

@app.route("/update_lesson_page/<int:book_id>/<int:chap_id>/<int:les_id>", methods=["POST"])
@login_required
def update_lesson_page(book_id, chap_id, les_id):
    uname = current_user.username
    user_lib = data_store["users"][uname]["data"]["library"]
    book = next((b for b in user_lib if b["id"] == book_id), None)
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

@app.route("/toggle_lesson/<int:book_id>/<int:chap_id>/<int:les_id>")
@login_required
def toggle_lesson(book_id, chap_id, les_id):
    uname = current_user.username
    user_lib = data_store["users"][uname]["data"]["library"]
    book = next((b for b in user_lib if b["id"] == book_id), None)
    if book:
        chap = next((c for c in book["chapters"] if c["id"] == chap_id), None)
        if chap:
            les = next((l for l in chap["lessons"] if l["id"] == les_id), None)
            if les:
                les["is_completed"] = not les["is_completed"]
                les["current_page"] = les["total_pages"] if les["is_completed"] else 0
                save_data(data_store)
    return redirect(url_for("book_detail", book_id=book_id))

# --- DELETION ---
@app.route("/delete_book/<int:book_id>")
@login_required
def delete_book(book_id):
    uname = current_user.username
    user_lib = data_store["users"][uname]["data"]["library"]
    data_store["users"][uname]["data"]["library"] = [b for b in user_lib if b["id"] != book_id]
    save_data(data_store)
    return redirect(url_for("home"))
@app.route("/delete_chapter/<int:book_id>/<int:chap_id>")
@login_required
def delete_chapter(book_id, chap_id):
    uname = current_user.username
    user_lib = data_store["users"][uname]["data"]["library"]
    book = next((b for b in user_lib if b["id"] == book_id), None)
    if book:
        book["chapters"] = [c for c in book["chapters"] if c["id"] != chap_id]
        save_data(data_store) # <-- Critical line
    return redirect(url_for("book_detail", book_id=book_id))
    # In app.py
@app.route("/delete_lesson/<int:book_id>/<int:chap_id>/<int:les_id>")
@login_required
def delete_lesson(book_id, chap_id, les_id):
    uname = current_user.username
    user_lib = data_store["users"][uname]["data"]["library"]
    
    book = next((b for b in user_lib if b["id"] == book_id), None)
    if book:
        chapter = next((c for c in book["chapters"] if c["id"] == chap_id), None)
        if chapter:
            # Filter the lesson list to remove the target ID
            chapter["lessons"] = [l for l in chapter["lessons"] if l["id"] != les_id]
            save_data(data_store)
            
    return redirect(url_for("book_detail", book_id=book_id))
# --- AUTH & GUEST ---
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username in data_store["users"]:
            flash("Username already exists!")
            return redirect(url_for("register"))
        data_store["users"][username] = {"password": generate_password_hash(password), "data": init_user_data()}
        save_data(data_store)
        login_user(User(username))
        return redirect(url_for("home"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user_entry = data_store["users"].get(username)
        if user_entry and check_password_hash(user_entry["password"], password):
            login_user(User(username))
            return redirect(url_for("home"))
        flash("Invalid credentials")
    return render_template("login.html")

@app.route("/guest_login")
def guest_login():
    random_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    guest_username = f"Guest_{random_id}"
    data_store["users"][guest_username] = {"password": generate_password_hash("guest"), "data": init_user_data()}
    save_data(data_store)
    login_user(User(guest_username), remember=True)
    return redirect(url_for("home"))

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("guest_login"))

if __name__ == "__main__":
    app.run(debug=True)
