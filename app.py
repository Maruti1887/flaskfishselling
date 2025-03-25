from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
from werkzeug.utils import secure_filename
import os
# Create a file called test.py with these contents:
import sqlite3
print("SQLite3 imported successfully!")
conn = sqlite3.connect('test.db')
print("Database connected successfully!")

app = Flask(__name__, static_folder='static')
app.secret_key = 'your_secret_key'
UPLOAD_FOLDER = './static/fish_images/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Database setup
DATABASE = 'database.db'


def init_db():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        # Create users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT,
                district TEXT,
                place TEXT
            )
        """)
        # Create sellers table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sellers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                phone TEXT,
                district TEXT,
                place TEXT,
                username TEXT UNIQUE,
                password TEXT
            )
        """)
        # Create fish details table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fish (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                seller_id INTEGER,
                fish_name TEXT,
                rate REAL,
                image_path TEXT,
                FOREIGN KEY (seller_id) REFERENCES sellers (id)
            )
        """)
        conn.commit()

init_db()


@app.route('/aboutus')
def aboutus():
    return render_template('aboutus.html')


@app.route('/img/<path:filename>')
def serve_img(filename):
    # Make sure to adjust this path to your project root directory
    img_dir = os.path.join(os.getcwd(), 'img')  # Path to 'img' folder in the project root
    return send_from_directory(img_dir, filename)

    
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        district = request.form['district']
        place = request.form['place']

        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            if role == 'user':
                try:
                    cursor.execute("""
                        INSERT INTO users (username, password, district, place)
                        VALUES (?, ?, ?, ?)
                    """, (username, password, district, place))
                    conn.commit()
                    flash('User registration successful! Please log in.')
                    return redirect(url_for('login'))
                except sqlite3.IntegrityError:
                    flash('Username already exists. Please choose another.')
            elif role == 'seller':
                phone = request.form['phone']
                try:
                    cursor.execute("""
                        INSERT INTO sellers (name, phone, district, place, username, password)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (request.form['name'], phone, district, place, username, password))
                    conn.commit()
                    flash('Seller registration successful! Please log in.')
                    return redirect(url_for('login'))
                except sqlite3.IntegrityError:
                    flash('Username already exists. Please choose another.')

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        # Check for admin login
        if username == 'admin' and password == 'admin123':
            with sqlite3.connect(DATABASE) as conn:
                cursor = conn.cursor()
                # Fetch all users
                cursor.execute("SELECT id, username, district, place FROM users")
                users = cursor.fetchall()

                # Fetch all sellers
                cursor.execute("SELECT id, name, phone, district, place FROM sellers")
                sellers = cursor.fetchall()

            return render_template('admin_dashboard.html', users=users, sellers=sellers)

        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            if role == 'user':
                cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
            else:  # Seller
                cursor.execute("SELECT * FROM sellers WHERE username = ? AND password = ?", (username, password))

            account = cursor.fetchone()

        if account:
            session['username'] = username
            session['role'] = role
            if role == 'user':
                return redirect(url_for('user_dashboard'))
            else:
                return redirect(url_for('seller_dashboard'))
        else:
            flash('Invalid credentials!')

    return render_template('login.html')



@app.route('/user_dashboard')
def user_dashboard():
    if 'username' not in session or session['role'] != 'user':
        return redirect(url_for('login'))

    username = session['username']
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT district, place FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        district, place = user

        cursor.execute("SELECT * FROM sellers WHERE district = ? AND place = ?", (district, place))
        sellers = cursor.fetchall()

    return render_template('user_dashboard.html', sellers=sellers)

@app.route('/seller/<int:seller_id>')
def seller_profile(seller_id):
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM fish WHERE seller_id = ?", (seller_id,))
        fish_details = cursor.fetchall()

    return render_template('seller_profile.html', fish_details=fish_details)

@app.route('/fix_image_paths')
def fix_image_paths():
    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            # Update the image paths to replace backslashes with forward slashes
            cursor.execute("UPDATE fish SET image_path = REPLACE(image_path, '\\\\', '/');")
            conn.commit()
        return "Image paths updated successfully!"
    except Exception as e:
        return f"An error occurred: {e}"


@app.route('/seller_dashboard', methods=['GET', 'POST'])
def seller_dashboard():
    if 'username' not in session or session['role'] != 'seller':
        return redirect(url_for('login'))

    if request.method == 'POST':
        fish_name = request.form['fish_name']
        rate = request.form['rate']
        image = request.files['image']

        if image:
            filename = secure_filename(f"{session['username']}_{image.filename}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(filepath)

            # Ensure forward slashes in the relative path
            relative_path = f'fish_images/{filename}'
            print(f"Saved image path: {relative_path}")  # Debugging line

            with sqlite3.connect(DATABASE) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM sellers WHERE username = ?", (session['username'],))
                seller_id = cursor.fetchone()[0]
                cursor.execute("""
                    INSERT INTO fish (seller_id, fish_name, rate, image_path)
                    VALUES (?, ?, ?, ?)
                """, (seller_id, fish_name, rate, relative_path))
                conn.commit()
            flash('Fish details uploaded successfully!')

    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM sellers WHERE username = ?", (session['username'],))
        seller_id = cursor.fetchone()[0]
        cursor.execute("SELECT * FROM fish WHERE seller_id = ?", (seller_id,))
        fish_details = cursor.fetchall()

        # Debugging: print all fish details
        for fish in fish_details:
            print(f"Fish entry: {fish}")

    return render_template('seller_dashboard.html', fish_details=fish_details)

@app.route('/delete_fish/<int:fish_id>', methods=['POST'])
def delete_fish(fish_id):
    if 'username' not in session or session['role'] != 'seller':
        flash("Unauthorized access!")
        return redirect(url_for('login'))

    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            # Fetch the fish image path before deleting
            cursor.execute("SELECT image_path FROM fish WHERE id = ?", (fish_id,))
            result = cursor.fetchone()
            if result:
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], result[0])
                # Remove the fish entry from the database
                cursor.execute("DELETE FROM fish WHERE id = ?", (fish_id,))
                conn.commit()

                # Delete the image file from the file system if it exists
                if os.path.exists(image_path):
                    os.remove(image_path)
                    print(f"Deleted image file: {image_path}")

                flash("Fish details deleted successfully!")
            else:
                flash("Fish not found!")
    except Exception as e:
        print(f"Error deleting fish: {e}")
        flash("An error occurred while deleting the fish details.")

    return redirect(url_for('seller_dashboard'))


@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('role', None)
    flash('Logged out successfully!')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)