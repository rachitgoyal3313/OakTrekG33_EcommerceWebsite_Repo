import os
from functools import wraps
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # Change this!
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'
login_manager.login_message = 'Please log in to access this page.'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Database Models
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    subscribed = db.Column(db.Boolean, default=False)
    password_changed_at = db.Column(db.DateTime, nullable=True, default=datetime.utcnow)
    addresses = db.relationship('Address', backref='user', lazy=True)
    orders = db.relationship('Order', backref='user', lazy=True)  # Add relationship for orders

    def __repr__(self):
        return f"User('{self.name}', '{self.email}')"

class Address(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    street = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(50), nullable=False)
    state = db.Column(db.String(2), nullable=False)
    zipcode = db.Column(db.String(10), nullable=False)
    is_default = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f"Address('{self.name}', '{self.city}', '{self.is_default}')"

class Order(db.Model):  # Basic Order model
    id = db.Column(db.Integer, primary_key=True)
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    total_amount = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f"Order(id={self.id}, date={self.order_date}, total={self.total_amount})"


# Authentication Routes
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('profile'))

    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')

        # Input validation
        if not all([name, email, password]):
            return jsonify({'message': 'All fields are required'}), 400

        # Check if email already exists
        user = User.query.filter_by(email=email).first()
        if user:
            return jsonify({'message': 'Email already registered'}), 400

        # Create new user
        try:
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            new_user = User(name=name, email=email, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return jsonify({'redirect': url_for('profile'), 'message': 'Account created successfully!'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'message': f'Error creating account: {str(e)}'}), 400

    return render_template('auth.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('profile'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        # Input validation
        if not all([email, password]):
            return jsonify({'message': 'Email and password are required'}), 400

        user = User.query.filter_by(email=email).first()

        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user, remember=remember)
            return jsonify({'redirect': url_for('profile'), 'message': 'Logged in successfully!'})
        else:
            return jsonify({'message': 'Invalid email or password'}), 401

    return render_template('auth.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Profile Routes
@app.route('/profile')
@login_required
def profile():
    orders = Order.query.filter_by(user_id=current_user.id).all() # Fetch orders for the current user
    return render_template('profile.html', user=current_user, orders=orders)

@app.route('/change_password', methods=['POST'])
@login_required
def change_password():
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')

    # Input validation
    if not all([current_password, new_password]):
        return jsonify({'message': 'Both current and new passwords are required'}), 400

    if not bcrypt.check_password_hash(current_user.password, current_password):
        return jsonify({'message': 'Current password is incorrect'}), 400

    try:
        hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        current_user.password = hashed_password
        current_user.password_changed_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'message': 'Password changed successfully!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error changing password: {str(e)}'}), 400

@app.route('/add_address', methods=['POST'])
@login_required
def add_address():
    name = request.form.get('name')
    street = request.form.get('street')
    city = request.form.get('city')
    state = request.form.get('state')
    zipcode = request.form.get('zipcode')
    is_default = request.form.get('is_default') == 'on'

    # Input validation
    if not all([name, street, city, state, zipcode]):
        return jsonify({'message': 'All address fields are required'}), 400

    try:
        if is_default:
            # Clear existing default address
            Address.query.filter_by(user_id=current_user.id, is_default=True).update({Address.is_default: False})
            db.session.commit()  # Commit after updating existing default address

        new_address = Address(
            name=name,
            street=street,
            city=city,
            state=state,
            zipcode=zipcode,
            is_default=is_default,
            user_id=current_user.id
        )

        db.session.add(new_address)
        db.session.commit()
        return jsonify({'message': 'Address added successfully!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error adding address: {str(e)}'}), 400

@app.route('/delete_address/<int:address_id>', methods=['POST'])
@login_required
def delete_address(address_id):
    address = Address.query.get_or_404(address_id)
    if address.user_id != current_user.id:
        return jsonify({'message': 'You do not have permission to delete this address.'}), 403

    try:
        db.session.delete(address)
        db.session.commit()
        return jsonify({'message': 'Address deleted successfully!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error deleting address: {str(e)}'}), 400

@app.route('/add_phone', methods=['POST'])
@login_required
def add_phone():
    phone = request.form.get('phone')
    if not phone:
        return jsonify({'message': 'Phone number is required'}), 400

    try:
        current_user.phone = phone
        db.session.commit()
        return jsonify({'message': 'Phone number added successfully!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error adding phone number: {str(e)}'}), 400

@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    name = request.form.get('name')
    email = request.form.get('email')

    if not all([name, email]):
        return jsonify({'message': 'Name and email are required'}), 400

    # Check if the new email already exists for another user
    existing_user = User.query.filter(User.email == email, User.id != current_user.id).first()
    if existing_user:
        return jsonify({'message': 'Email already exists for another user.'}), 400

    try:
        current_user.name = name
        current_user.email = email
        db.session.commit()
        return jsonify({'message': 'Profile updated successfully!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error updating profile: {str(e)}'}), 400

# Additional Routes
@app.route('/stores')
def stores():
    return render_template('stores.html')
 
@app.route('/about_us')
def about_us():
    return render_template('about_us.html')
 
@app.route('/faq')
def faq():
    return render_template('faq.html') 
 
@app.route('/cart')
def cart():
    return render_template('cart.html') 
 
@app.route('/coming_soon')
def coming_soon():
    return render_template('coming_soon.html') 
 
@app.route('/our_story')
def our_story():
    return render_template('our_story.html') 
 
@app.route('/oaktree_help')
def oaktree_help():
    return render_template('oaktree_help.html') 
 
@app.route('/our_materials')
def our_materials():
    return render_template('our_materials.html') 
 
@app.route('/returns')
def returns():
    return render_template('returns.html')

# Create Database
with app.app_context():
    db.create_all()


if __name__ == '__main__':
    app.run(debug=True) 