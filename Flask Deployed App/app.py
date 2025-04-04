import os
import sqlite3
from flask import Flask, redirect, render_template, request, url_for, session, flash
from PIL import Image
import torchvision.transforms.functional as TF
import CNN
import numpy as np
import torch
import pandas as pd

# Load Data
disease_info = pd.read_csv('disease_info.csv', encoding='cp1252')
supplement_info = pd.read_csv('supplement_info.csv', encoding='cp1252')

# Load Model
model = CNN.CNN(39)
model.load_state_dict(torch.load("plant_disease_model_1_latest.pt"))
model.eval()

# Function to Predict Disease
def prediction(image_path):
    image = Image.open(image_path)
    image = image.resize((224, 224))
    input_data = TF.to_tensor(image)
    input_data = input_data.view((-1, 3, 224, 224))
    output = model(input_data)
    output = output.detach().numpy()
    index = np.argmax(output)
    return index

# Flask App Configuration
app = Flask(__name__)
app.secret_key = "your_secret_key"  # Required for session handling

# SQLite Database Setup
DATABASE = "users.db"

def create_users_table():
    """Creates the users table if it doesn't exist"""
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        conn.commit()

# Ensure the table is created when the app starts
create_users_table()

def get_user(email):
    """Fetches a user by email"""
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        return cursor.fetchone()

def add_user(email, password):
    """Inserts a new user into the database"""
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, password))
        conn.commit()

# ===================== Signup Route =====================
import sqlite3  # Add at the top

@app.route('/', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email', '')
        password = request.form.get('password1', '')

        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()

        # Check if user already exists
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            flash("Email already exists!", "danger")
            conn.close()
            return redirect(url_for('signup'))

        # Insert user into database
        cursor.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, password))
        conn.commit()
        conn.close()

        session['user'] = email  # Store user session
        flash("Signup successful!", "success")
        return redirect(url_for('home_page'))

    return render_template('signup.html')


# ===================== Login Route =====================
@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        print(f"📢 Login Attempt: Email = {email}, Password = {password}")  # Debugging

        user = get_user(email)
        if user and user[2] == password:  # user[2] is the password column
            session['user'] = email  # Store user session
            flash("✅ Login successful!", "success")
            print("✅ Redirecting to home page...")  # Debugging
            return redirect(url_for('home_page'))

        flash("❌ Invalid credentials!", "danger")
        print("❌ Login failed!")  # Debugging
        return render_template('login.html')

    return render_template('login.html')

# ===================== Logout Route =====================
@app.route('/logout')
def logout():
    session.pop('user', None)
    flash("Logged out successfully!", "info")
    return redirect(url_for('login_page'))

# ===================== Home Page =====================
@app.route('/home')
def home_page():
    if 'user' not in session:
        flash("⚠️ Please log in first!", "warning")
        print("⚠️ Redirecting to login page...")
        return redirect(url_for('login_page'))

    print(f"🏠 Home page accessed by: {session['user']}")  # Debugging
    return render_template('home.html')

# ===================== Contact Page =====================
@app.route('/contact')
def contact():
    return render_template('contact-us.html')

# ===================== AI Engine Page =====================
@app.route('/index')
def ai_engine_page():
    return render_template('index.html')

# ===================== Image Submission & Prediction =====================
@app.route('/submit', methods=['GET', 'POST'])
def submit():
    if request.method == 'POST':
        image = request.files['image']
        filename = image.filename
        file_path = os.path.join('static/uploads', filename)
        image.save(file_path)

        pred = prediction(file_path)
        title = disease_info['disease_name'][pred]
        description = disease_info['description'][pred]
        prevent = disease_info['Possible Steps'][pred]
        image_url = disease_info['image_url'][pred]
        supplement_name = supplement_info['supplement name'][pred]
        supplement_image_url = supplement_info['supplement image'][pred]
        supplement_buy_link = supplement_info['buy link'][pred]

        return render_template('submit.html',
                               title=title, desc=description, prevent=prevent,
                               image_url=image_url, pred=pred, sname=supplement_name,
                               simage=supplement_image_url, buy_link=supplement_buy_link)

# ===================== Marketplace Page =====================
@app.route('/market', methods=['GET', 'POST'])
def market():
    return render_template('market.html',
                           supplement_image=list(supplement_info['supplement image']),
                           supplement_name=list(supplement_info['supplement name']),
                           disease=list(disease_info['disease_name']),
                           buy=list(supplement_info['buy link']))

# Run the Flask App
if __name__ == '__main__':
    app.run(debug=True)
