from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import os

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))

app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///" + os.path.join(basedir, "default.db")  # Default DB
app.config['SQLALCHEMY_BINDS'] = {
    'users': "sqlite:///" + os.path.join(basedir, "users.db"),
    'cart': "sqlite:///" + os.path.join(basedir, "cart.db"),
    'products': "sqlite:///" + os.path.join(basedir, "products.db")
}

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class User(db.Model, UserMixin):
    __bind_key__ = 'users'  # Uses users.db
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)  # Unique email
    password_hash = db.Column(db.String(256), nullable=False)
    contact = db.Column(db.String(15), unique=True, nullable=False)  # Unique contact
    address = db.Column(db.String(255), nullable=True)
    birthday = db.Column(db.Date)

class Cart(db.Model):
    __bind_key__ = 'cart'  # Uses cart.db
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), nullable=False)
    product_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    price = db.Column(db.Float, nullable=False)

class Product(db.Model):
    __bind_key__ = 'products'  # Uses products.db
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    gender = db.Column(db.String(10), nullable=False)  # Example: 'Male', 'Female', 'Unisex'
    price = db.Column(db.Float, nullable=False)
    image_name = db.Column(db.String(100), nullable=False)  # Stores only the image filename


with app.app_context():
    db.create_all()



@app.route("/stores")
def stores():
    return render_template("stores.html")

@app.route("/collections/<string:collection_name>")
def products(collection_name):
    # Query products based on collection name (which could be a category or gender)
    # Using the Product model from your database
    if collection_name.lower() in ['men', 'mens', "men's"]:
        products = Product.query.filter_by(gender='Male').all()
    elif collection_name.lower() in ['women', 'womens', "women's"]:
        products = Product.query.filter_by(gender='Female').all()
    else:
        # If collection_name is a category (like 'everyday-sneakers')
        # Convert URL-friendly format to database format (e.g., 'everyday-sneakers' to 'Everyday Sneakers')
        category = collection_name.replace('-', ' ').title()
        products = Product.query.filter_by(category=category).all()
    
    # Get unique categories for sidebar navigation
    categories = db.session.query(Product.category).distinct().all()
    categories = [cat[0] for cat in categories]  # Convert from tuples to list
    
    return render_template(
        "products.html",
        products=products,
        collection_name=collection_name,
        categories=categories
    )
@app.route('/product/<int:product_id>')
def product_page(product_id):
    return f"Product Page for ID {product_id}"

if __name__ == '__main__':
    app.run(debug=True)