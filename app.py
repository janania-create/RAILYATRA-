from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import mysql.connector
from mysql.connector import Error
from datetime import datetime
import hashlib
import random
import string

app = Flask(__name__)
app.secret_key = 'raiyatra_secret_key_2026'

# ─────────────────────────────────────────────
#  DATABASE CONNECTION
# ─────────────────────────────────────────────
def get_db():
    try:
        conn = mysql.connector.connect(
            host='localhost',
            database='railway_management',
            user='root',
            password='Janani4906!',          # ← PUT YOUR MYSQL PASSWORD HERE
            autocommit=True
        )
        return conn
    except Error as e:
        print(f"DB Error: {e}")
        return None

def query(sql, params=(), one=False, write=False):
    conn = get_db()
    if not conn:
        return None
    cur = conn.cursor(dictionary=True)
    cur.execute(sql, params)
    if write:
        conn.commit()
        conn.close()
        return cur.lastrowid
    result = cur.fetchone() if one else cur.fetchall()
    conn.close()
    return result

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def generate_pnr():
    return 'PNR' + ''.join(random.choices(string.digits, k=7))

# ─────────────────────────────────────────────
#  HOME
# ─────────────────────────────────────────────
@app.route('/')
def home():
    trains = query("SELECT train_number, train_name, train_type FROM trains WHERE status='Active' LIMIT 5")
    return render_template('home.html', trains=trains)

# ─────────────────────────────────────────────
#  AUTH — LOGIN
# ─────────────────────────────────────────────
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email    = request.form['email']
        password = hash_password(request.form['password'])
        user = query(
            "SELECT * FROM passengers WHERE email=%s AND password_hash=%s",
            (email, password), one=True
        )
        if user:
            session['user_id']   = user['passenger_id']
            session['user_name'] = user['first_name']
            session['user_email']= user['email']
            flash('Welcome back, ' + user['first_name'] + '!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid email or password.', 'error')
    return render_template('login.html')

# ─────────────────────────────────────────────
#  AUTH — REGISTER
# ─────────────────────────────────────────────
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first_name      = request.form['first_name']
        last_name       = request.form['last_name']
        email           = request.form['email']
        phone           = request.form['phone']
        dob             = request.form['dob']
        gender          = request.form['gender']
        id_proof_type   = request.form['id_proof_type']
        id_proof_number = request.form['id_proof_number']
        password_hash   = hash_password(request.form['password'])

        existing = query("SELECT passenger_id FROM passengers WHERE email=%s", (email,), one=True)
        if existing:
            flash('Email already registered. Please login.', 'error')
            return redirect(url_for('register'))

        query(
            """INSERT INTO passengers
               (first_name, last_name, email, phone, dob, gender,
                id_proof_type, id_proof_number, password_hash)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (first_name, last_name, email, phone, dob, gender,
             id_proof_type, id_proof_number, password_hash),
            write=True
        )
        flash('Account created! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

# ─────────────────────────────────────────────
#  LOGOUT
# ─────────────────────────────────────────────
@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('home'))

# ─────────────────────────────────────────────
#  SEARCH TRAINS
# ─────────────────────────────────────────────
@app.route('/search', methods=['GET', 'POST'])
def search():
    stations = query("SELECT * FROM stations ORDER BY station_name")
    results  = []
    from_st = to_st = date = None

    if request.method == 'POST':
        from_code = request.form['from_station']
        to_code   = request.form['to_station']
        date      = request.form['journey_date']
        from_st   = query("SELECT * FROM stations WHERE station_code=%s", (from_code,), one=True)
        to_st     = query("SELECT * FROM stations WHERE station_code=%s", (to_code,), one=True)

        results = query("""
            SELECT DISTINCT t.train_id, t.train_number, t.train_name, t.train_type,
                   r_from.departure_time, r_to.arrival_time,
                   (r_to.distance_from_origin - r_from.distance_from_origin) AS distance_km
            FROM routes r_from
            JOIN routes   r_to ON r_from.train_id = r_to.train_id
                               AND r_from.stop_number < r_to.stop_number
            JOIN trains   t    ON r_from.train_id   = t.train_id
            JOIN stations sf   ON r_from.station_id = sf.station_id
            JOIN stations st   ON r_to.station_id   = st.station_id
            WHERE sf.station_code = %s AND st.station_code = %s AND t.status='Active'
        """, (from_code, to_code))

    return render_template('search.html',
                           stations=stations, results=results,
                           from_st=from_st, to_st=to_st, date=date)

# ─────────────────────────────────────────────
#  BOOK TICKET
# ─────────────────────────────────────────────
@app.route('/book/<int:train_id>', methods=['GET', 'POST'])
def book(train_id):
    if 'user_id' not in session:
        flash('Please login to book a ticket.', 'error')
        return redirect(url_for('login'))

    train    = query("SELECT * FROM trains WHERE train_id=%s", (train_id,), one=True)
    coaches  = query("SELECT * FROM coaches WHERE train_id=%s", (train_id,))
    stations = query("SELECT * FROM stations ORDER BY station_name")
    fares    = query("SELECT * FROM fares WHERE train_id=%s", (train_id,))

    if request.method == 'POST':
        coach_id     = request.form['coach_id']
        from_station = request.form['from_station']
        to_station   = request.form['to_station']
        journey_date = request.form['journey_date']
        seat_number  = request.form['seat_number']
        pnr          = generate_pnr()

        booking_id = query(
            """INSERT INTO bookings
               (passenger_id, train_id, coach_id, journey_date,
                from_station, to_station, seat_number, booking_status, pnr_number)
               VALUES (%s,%s,%s,%s,%s,%s,%s,'Confirmed',%s)""",
            (session['user_id'], train_id, coach_id, journey_date,
             from_station, to_station, seat_number, pnr),
            write=True
        )

        amount = request.form.get('fare_amount', 500)
        query(
            """INSERT INTO payments (booking_id, amount, payment_method, payment_status, transaction_id)
               VALUES (%s,%s,%s,'Success',%s)""",
            (booking_id, amount, request.form.get('payment_method','UPI'),
             'TXN' + ''.join(random.choices(string.digits, k=10))),
            write=True
        )

        flash(f'Booking Confirmed! Your PNR is {pnr}', 'success')
        return redirect(url_for('pnr_status', pnr=pnr))

    return render_template('book.html',
                           train=train, coaches=coaches,
                           stations=stations, fares=fares)

# ─────────────────────────────────────────────
#  PNR STATUS
# ─────────────────────────────────────────────
@app.route('/pnr', methods=['GET', 'POST'])
def pnr():
    return render_template('pnr.html', booking=None)

@app.route('/pnr/<pnr>', methods=['GET'])
def pnr_status(pnr):
    booking = query("""
        SELECT b.*, p.first_name, p.last_name, p.phone,
               t.train_number, t.train_name,
               c.coach_number, c.coach_type,
               sf.station_name AS from_name, sf.station_code AS from_code,
               st.station_name AS to_name,   st.station_code AS to_code,
               py.amount, py.payment_method, py.payment_status
        FROM bookings b
        JOIN passengers p  ON b.passenger_id = p.passenger_id
        JOIN trains     t  ON b.train_id      = t.train_id
        JOIN coaches    c  ON b.coach_id      = c.coach_id
        JOIN stations   sf ON b.from_station  = sf.station_id
        JOIN stations   st ON b.to_station    = st.station_id
        LEFT JOIN payments py ON b.booking_id = py.booking_id
        WHERE b.pnr_number = %s
    """, (pnr,), one=True)
    return render_template('pnr.html', booking=booking, pnr=pnr)

# ─────────────────────────────────────────────
#  CANCEL BOOKING
# ─────────────────────────────────────────────
@app.route('/cancel/<pnr>')
def cancel(pnr):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    query("UPDATE bookings SET booking_status='Cancelled' WHERE pnr_number=%s", (pnr,), write=True)
    query("UPDATE payments SET payment_status='Refunded' WHERE booking_id=(SELECT booking_id FROM bookings WHERE pnr_number=%s)", (pnr,), write=True)
    flash('Booking cancelled and refund initiated.', 'success')
    return redirect(url_for('my_bookings'))

# ─────────────────────────────────────────────
#  MY BOOKINGS
# ─────────────────────────────────────────────
@app.route('/my-bookings')
def my_bookings():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    bookings = query("""
        SELECT b.*, t.train_number, t.train_name,
               c.coach_number, c.coach_type,
               sf.station_name AS from_name, st.station_name AS to_name,
               py.amount
        FROM bookings b
        JOIN trains   t  ON b.train_id     = t.train_id
        JOIN coaches  c  ON b.coach_id     = c.coach_id
        JOIN stations sf ON b.from_station = sf.station_id
        JOIN stations st ON b.to_station   = st.station_id
        LEFT JOIN payments py ON b.booking_id = py.booking_id
        WHERE b.passenger_id = %s ORDER BY b.booking_date DESC
    """, (session['user_id'],))
    return render_template('my_bookings.html', bookings=bookings)

# ─────────────────────────────────────────────
#  ADMIN DASHBOARD
# ─────────────────────────────────────────────
@app.route('/admin')
def admin():
    stats = {
        'total_bookings'  : query("SELECT COUNT(*) AS c FROM bookings", one=True)['c'],
        'total_revenue'   : query("SELECT COALESCE(SUM(amount),0) AS s FROM payments WHERE payment_status='Success'", one=True)['s'],
        'active_trains'   : query("SELECT COUNT(*) AS c FROM trains WHERE status='Active'", one=True)['c'],
        'total_passengers': query("SELECT COUNT(*) AS c FROM passengers", one=True)['c'],
    }
    recent_bookings = query("""
        SELECT b.pnr_number, CONCAT(p.first_name,' ',p.last_name) AS passenger,
               t.train_number, t.train_name,
               sf.station_code AS from_code, st.station_code AS to_code,
               b.journey_date, c.coach_type, b.seat_number, b.booking_status
        FROM bookings b
        JOIN passengers p  ON b.passenger_id = p.passenger_id
        JOIN trains     t  ON b.train_id      = t.train_id
        JOIN coaches    c  ON b.coach_id      = c.coach_id
        JOIN stations   sf ON b.from_station  = sf.station_id
        JOIN stations   st ON b.to_station    = st.station_id
        ORDER BY b.booking_date DESC LIMIT 10
    """)
    trains      = query("SELECT * FROM trains ORDER BY train_id")
    employees   = query("""
        SELECT e.*, s.station_name, t.train_name
        FROM employees e
        LEFT JOIN stations s ON e.station_id = s.station_id
        LEFT JOIN trains   t ON e.train_id   = t.train_id
    """)
    return render_template('admin.html',
                           stats=stats, recent_bookings=recent_bookings,
                           trains=trains, employees=employees)

# ─────────────────────────────────────────────
#  RUN
# ─────────────────────────────────────────────
if __name__ == '__main__':
    app.run(debug=True)