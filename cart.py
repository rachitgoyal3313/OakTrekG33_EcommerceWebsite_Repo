from flask import Flask, request, redirect, url_for, render_template, g
import sqlite3

app = Flask(__name__)
app.config['DATABASE'] = 'cart.db'

# Database setup
def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:  # Use schema.sql to initialize
            db.cursor().executescript(f.read())
        db.commit()

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(app.config['DATABASE'])
        db.row_factory = sqlite3.Row  #  Access columns by name
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# Add product to cart
@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    product_name = request.form.get('product_name')
    price = float(request.form.get('price'))
    quantity = int(request.form.get('quantity'))

    db = get_db()
    db.execute("INSERT INTO cart (product_name, price, quantity) VALUES (?, ?, ?)",
              (product_name, price, quantity))
    db.commit()

    return redirect(url_for('cart'))

@app.route('/stores')
def stores():
    cart_count = get_cart_count()
    return render_template('stores.html', cart_count=cart_count)

# View cart
@app.route('/cart')
def cart():
    db = get_db()
    cur = db.execute("SELECT * FROM cart")
    cart_items = cur.fetchall()
    cart_count = get_cart_count()

    total = sum(item['price'] * item['quantity'] for item in cart_items)  # Calculate total

    return render_template('cart.html', cart_items=cart_items, cart_count=cart_count, total=total)

@app.route('/checkout')
def checkout():
    cart_count = get_cart_count()
    return render_template('checkout.html', cart_count=cart_count)

@app.route('/stores')
def stores():
    return render_template("stores.html")

@app.route('/confirmation')
def confirmation():
    # Clear the cart (optional, depending on your flow)
    clear_cart()
    cart_count = 0  # Reset cart count
    return render_template('confirmation.html', cart_count=cart_count)  # Pass updated cart_count

def get_cart_count():
    db = get_db()
    cur = db.execute("SELECT SUM(quantity) FROM cart")
    result = cur.fetchone()
    count = result[0] if result[0] else 0
    return count

def clear_cart():
    db = get_db()
    db.execute("DELETE FROM cart")
    db.commit()

@app.context_processor
def inject_cart_count():
    return {'cart_count': get_cart_count()}

if __name__ == '__main__':
    init_db()
    app.run(debug=True)