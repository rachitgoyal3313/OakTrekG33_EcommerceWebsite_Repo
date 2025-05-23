from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, Blueprint
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
import os

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))

# Configuration
app.config['ADMIN_EMAILS'] = ['admin@example.com']  # List of admin email addresses
app.config['SECRET_KEY'] = 'your_secret_key'  # Change this!
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///" + os.path.join(basedir, "default.db")
app.config['SQLALCHEMY_BINDS'] = {
    'users': "sqlite:///" + os.path.join(basedir, "users.db"),
    'cart': "sqlite:///" + os.path.join(basedir, "cart.db"),
    'products': "sqlite:///" + os.path.join(basedir, "products.db"),
    'address': "sqlite:///" + os.path.join(basedir, "address.db"),
    'orders': "sqlite:///" + os.path.join(basedir, "orders.db")  # Added orders db as well since we have Order model
}


app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'
login_manager.login_message = 'Please log in to access this page.'

admin = Blueprint('admin', __name__)


ADMIN_USERS = {

    'admin@example.com': {

        'password': 'admin123'  # Password stored as plain text
    }   
}

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.email not in app.config.get('ADMIN_EMAILS', []):
            flash('You need administrator privileges to access this page.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'assets/products')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Database Models
class User(db.Model, UserMixin):
    __bind_key__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    subscribed = db.Column(db.Boolean, default=False)
    password_changed_at = db.Column(db.DateTime, nullable=True, default=datetime.utcnow)
    addresses = db.relationship('Address', backref='user', lazy=True)
    orders = db.relationship('Order', backref='user', lazy=True)

class Address(db.Model):
    __bind_key__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    street = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(50), nullable=False)
    state = db.Column(db.String(2), nullable=False)
    zipcode = db.Column(db.String(10), nullable=False)
    is_default = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Order(db.Model):
    __bind_key__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    total_amount = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Cart(db.Model):
    __bind_key__ = 'cart'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), nullable=False)
    product_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    price = db.Column(db.Float, nullable=False)

class Product(db.Model):
    __bind_key__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    price = db.Column(db.Float, nullable=False)
    image_1 = db.Column(db.String(100))
    image_2 = db.Column(db.String(100))
    image_3 = db.Column(db.String(100))
    image_4 = db.Column(db.String(100))
    image_5 = db.Column(db.String(100))


# Helper Functions
def get_cart_details():
    if not current_user.is_authenticated:
        return None, 0, 0
    
    cart_items = Cart.query.filter_by(email=current_user.email).all()
    cart_with_details = []
    subtotal = 0
    
    for item in cart_items:
        product = Product.query.filter_by(product_name=item.product_name).first()
        if product:
            item_details = {
                'product_name': item.product_name,
                'quantity': item.quantity,
                'price': product.price,
                'total_price': product.price * item.quantity,
                'image': product.image_1
            }
            cart_with_details.append(item_details)
            subtotal += item_details['total_price']
    
    # Calculate tax (assuming 8% tax rate - adjust as needed)
    tax = round(subtotal * 0.08, 2)
    total = subtotal + tax
    
    return cart_with_details, subtotal, tax, total


def save_product_images(form_data, product=None):
    """Handle saving of product images"""
    images = {}
    main_image = request.files.get('image')
    
    if main_image and allowed_file(main_image.filename) and main_image.filename != '':
        filename = secure_filename(main_image.filename)
        img_path = os.path.join(UPLOAD_FOLDER, filename)
        main_image.save(img_path)
        images['image_1'] = filename
    
    # Handle additional images
    for i in range(1, 6):
        img_field = f'image_{i}'
        img_file = request.files.get(img_field)
        if img_file and allowed_file(img_file.filename) and img_file.filename != '':
            filename = secure_filename(img_file.filename)
            img_path = os.path.join(UPLOAD_FOLDER, filename)
            img_file.save(img_path)
            images[img_field] = filename
    
    return images

# Authentication Routes
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('profile'))

    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')

        if not all([name, email, password]):
            return jsonify({'message': 'All fields are required'}), 400

        user = User.query.filter_by(email=email).first()
        if user:
            return jsonify({'message': 'Email already registered'}), 400

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

# Profile Management Routes
# @app.route('/profile')
# @login_required
# def profile():
#     orders = Order.query.filter_by(user_id=current_user.id).all()
#     return render_template('profile.html', user=current_user, orders=orders)


@app.route('/profile')
@login_required
def profile():
    orders = Order.query.filter_by(user_id=current_user.id).all()
    return render_template('profile.html', user=current_user, orders=orders, app=app)

@app.route('/change_password', methods=['POST'])
@login_required
def change_password():
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')

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

    if not all([name, street, city, state, zipcode]):
        return jsonify({'message': 'All address fields are required'}), 400

    try:
        if is_default:
            Address.query.filter_by(user_id=current_user.id, is_default=True).update({Address.is_default: False})
            db.session.commit()

        new_address = Address(
            name=name, street=street, city=city, state=state,
            zipcode=zipcode, is_default=is_default, user_id=current_user.id
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


# Product and Cart Routes
@app.route("/collections/<string:collection_name>")
def products(collection_name):
    if collection_name.lower() in ['men', 'mens', "men's"]:
        products = Product.query.filter_by(gender='Male').all()
    elif collection_name.lower() in ['women', 'womens', "women's"]:
        products = Product.query.filter_by(gender='Female').all()
    else:
        category = collection_name.replace('-', ' ').title()
        products = Product.query.filter_by(category=category).all()
    
    categories = db.session.query(Product.category).distinct().all()
    categories = [cat[0] for cat in categories]
    
    return render_template(
        "products.html",
        products=products,
        collection_name=collection_name,
        categories=categories
    )


@app.route("/collections/<string:collection_name>/<string:product_name>")
def product_page(collection_name, product_name):
    product = Product.query.filter_by(product_name=product_name).first_or_404()
    return render_template("product2.html", **{
        "product_name": product.product_name,
        "category": product.category,
        "gender": product.gender,
        "price": product.price,
        "image_1": product.image_1,
        "image_2": product.image_2,
        "image_3": product.image_3,
        "image_4": product.image_4,
        "image_5": product.image_5
    })

@app.route("/cart", methods=["GET", "POST"])
def cart():
    if request.method == "POST":
        if not current_user.is_authenticated:
            flash("Please log in to add items to your cart.", "warning")
            return redirect(url_for("login"))

        product_name = request.form.get("product_name")
        price = float(request.form.get("price"))
        quantity = int(request.form.get("quantity"))
        prod_item = Product.query.filter_by(product_name=product_name).first()
        
        if not prod_item:
            flash("Product not found!", "danger")
            return redirect(url_for("cart"))

        existing_item = Cart.query.filter_by(email=current_user.email, product_name=product_name).first()
        if existing_item:
            existing_item.quantity += quantity
            existing_item.price += price
        else:
            new_cart_item = Cart(
                email=current_user.email,
                product_name=product_name,
                quantity=quantity,
                price=price
            )
            db.session.add(new_cart_item)

        db.session.commit()
        flash("Item added to cart!", "success")
        return redirect(url_for("cart"))

    cart_items = Cart.query.filter_by(email=current_user.email).all() if current_user.is_authenticated else []

    # Attach product images by querying Product table
    cart_with_images = []
    for item in cart_items:
        product = Product.query.filter_by(product_name=item.product_name).first()
        item.product_image = product.image_1 if product else "default.jpg"  # Avoid undefined errors
        cart_with_images.append(item)

    return render_template("cart.html", cart_items=cart_with_images)

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



@app.route("/update_cart", methods=["POST"])
def update_cart():
    if not current_user.is_authenticated:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    product_name = data.get("product_name")
    action = data.get("action")

    cart_item = Cart.query.filter_by(email=current_user.email, product_name=product_name).first()
    prod_item = Product.query.filter_by(product_name=product_name).first()
    if cart_item:
        if action == "increase":
            cart_item.quantity += 1
            cart_item.price += prod_item.price
        elif action == "decrease" and cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.price -= prod_item.price
        elif(action == "decrease" and cart_item.quantity == 1):
            db.session.delete(cart_item)
        db.session.commit()
    
    return jsonify({"success": True})



# Static Pages Routes
@app.route('/about_us')
def about_us():
    return render_template('about_us.html')

@app.route('/faq')
def faq():
    return render_template('faq.html')

@app.route('/coming_soon')
def coming_soon():
    return render_template('coming_soon.html')

@app.route('/our_story')
def our_story():
    return render_template('our_story.html')

@app.route('/oaktrek_help')
def oaktrek_help():
    return render_template('oaktrek_help.html')

@app.route('/our_materials')
def our_materials():
    return render_template('our_materials.html')

@app.route('/returns')
def returns():
    return render_template('returns.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')


@app.route("/stores")
def stores():
    return render_template("stores.html")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/adidasxoaktrek")
def adidasxoaktrek():
    return render_template("adidasxoaktrek.html")

@app.route("/foorprint")
def footprint():
    return render_template("footprint.html")

@app.route("/carbonoffsets")
def carbonoffsets():
    return render_template("carbonoffsets.html")

@app.route("/bcorp")
def bcorp():
    return render_template("bcorp.html")

@app.route("/moonshot")
def moonshot():
    return render_template("moonshot.html")

@app.route("/mothernature")
def mothernature():
    return render_template("mothernature.html")

@app.route("/regenerative")
def regenerative():
    return render_template("regenerative.html")

@app.route("/renewable")
def renewable():
    return render_template("renewable.html")

@app.route("/responsibleenergy")
def responsibleenergy():
    return render_template("responsibleenergy.html")

@app.route("/sustainability")
def sustainability():
    return render_template("sustainability.html")


@app.route("/checkout")
@login_required  # Add this decorator to ensure only logged-in users can access checkout
def checkout():
    # Get cart details
    cart_items, subtotal, tax, total = get_cart_details()
    
    if not cart_items:
        flash("Your cart is empty!", "warning")
        return redirect(url_for("cart"))
    
    # Get user's addresses
    addresses = Address.query.filter_by(user_id=current_user.id).all()
    
    return render_template(
        "checkout.html",
        cart_items=cart_items,
        subtotal=subtotal,
        tax=tax,
        total=total,
        addresses=addresses,
        user=current_user
    )


@app.route("/confirmation", methods=['GET', 'POST'])
@login_required
def confirmation():
    # Get cart items
    cart_items = Cart.query.filter_by(email=current_user.email).all()
    
    if not cart_items:
        return redirect(url_for('cart'))
    
    # Create order summary
    order_items = []
    subtotal = 0
    
    for cart_item in cart_items:
        product = Product.query.filter_by(product_name=cart_item.product_name).first()
        if product:
            item_total = product.price * cart_item.quantity
            order_items.append({
                'name': product.product_name,
                'quantity': cart_item.quantity,
                'price': product.price,
                'total': item_total,
                'image': product.image_1
            })
            subtotal += item_total
    
    # Calculate totals
    tax = round(subtotal * 0.08, 2)  # 8% tax
    total = subtotal + tax
    
    # Generate dummy order number
    import random
    order_number = f"OT{random.randint(100000, 999999)}"
    
    # Get shipping address
    shipping_address = Address.query.filter_by(
        user_id=current_user.id,
        is_default=True
    ).first()

    # Create a new order record - ADD THIS CODE HERE
    new_order = Order(
        total_amount=total,
        user_id=current_user.id
    )
    db.session.add(new_order)
    db.session.commit()
    
    # Clear the cart after confirmation
    for item in cart_items:
        db.session.delete(item)
    db.session.commit()
    
    return render_template(
        "confirmation.html",
        order_number=order_number,
        order_items=order_items,
        subtotal=subtotal,
        tax=tax,
        total=total,
        user=current_user,
        shipping_address=shipping_address
    )

@admin.route('/dashboard')
@login_required
@admin_required
def dashboard():
    return render_template('dashboard.html')

@admin.route('/products')
@login_required
@admin_required
def products():
    products = Product.query.all()
    return render_template('adminProducts.html', products=products)

@admin.route('/products/new', methods=['GET', 'POST'])
@login_required
@admin_required
def add_product():
    if request.method == 'POST':
        # Extract form data
        product_name = request.form.get('product_name')
        category = request.form.get('category')
        gender = request.form.get('gender')
        price = float(request.form.get('price'))
        
        # Validate required fields
        if not all([product_name, category, gender, price]):
            flash('All required fields must be filled', 'danger')
            return redirect(request.url)
        
        # Handle image uploads
        main_image = request.files.get('image')
        if not main_image or main_image.filename == '':
            flash('Main product image is required', 'danger')
            return redirect(request.url)
        
        # Save images and get paths
        images = save_product_images(request.form)
        
        # Create product object
        new_product = Product(
            product_name=product_name,
            category=category,
            gender=gender,
            price=price,
            image_1=images.get('image_1'),
            image_2=images.get('image_2'),
            image_3=images.get('image_3'),
            image_4=images.get('image_4'),
            image_5=images.get('image_5')
        )
        
        # Save to database
        db.session.add(new_product)
        db.session.commit()
        
        flash('Product added successfully!', 'success')
        return redirect(url_for('admin.products'))
    
    return render_template('add_product.html')

@admin.route('/products/<int:product_id>')
@login_required
@admin_required
def view_product(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('view_product.html', product=product)

# Edit product
@admin.route('/products/<int:product_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    
    if request.method == 'POST':
        # Update product with form data
        product.product_name = request.form.get('product_name')
        product.category = request.form.get('category')
        product.gender = request.form.get('gender')
        product.price = float(request.form.get('price'))
        
        # Handle image uploads - only update if new images provided
        try:
            # Handle main image
            main_image = request.files.get('image')
            if main_image and allowed_file(main_image.filename) and main_image.filename != '':
                # Delete old image if it exists
                if product.image_1:
                    old_image_path = os.path.join(UPLOAD_FOLDER, product.image_1)
                    if os.path.exists(old_image_path):
                        os.remove(old_image_path)
                    
                # Save new image
                filename = secure_filename(main_image.filename)
                main_image.save(os.path.join(UPLOAD_FOLDER, filename))
                product.image_1 = filename
            
            # Handle additional images
            for i in range(2, 6):
                img_field = f'image_{i}'
                img_file = request.files.get(img_field)
                if img_file and allowed_file(img_file.filename) and img_file.filename != '':
                    # Delete old image if it exists
                    old_img = getattr(product, img_field)
                    if old_img:
                        old_img_path = os.path.join(UPLOAD_FOLDER, old_img)
                        if os.path.exists(old_img_path):
                            os.remove(old_img_path)
                    
                    # Save new image
                    filename = secure_filename(img_file.filename)
                    img_file.save(os.path.join(UPLOAD_FOLDER, filename))
                    setattr(product, img_field, filename)
        
        except FileNotFoundError as e:
            # Log the error but continue with product update
            app.logger.error(f"File not found: {e}")
            flash('Product updated, but had trouble managing some image files', 'warning')
        except Exception as e:
            app.logger.error(f"Error handling images: {e}")
            flash('Product updated, but there was an issue with image processing', 'warning')
        
        # Commit database changes
        db.session.commit()
        flash('Product updated successfully!', 'success')
        return redirect(url_for('admin.products'))
    
    return render_template('edit_product.html', product=product)

@admin.route('/products/<int:product_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    
    # Optionally remove image files from filesystem
    try:
        if product.image_1:
            os.remove(os.path.join(UPLOAD_FOLDER, product.image_1))
        for i in range(1, 6):
            img_field = f'image_{i}'
            img_path = getattr(product, img_field)
            if img_path:
                os.remove(os.path.join(UPLOAD_FOLDER, img_path))
    except Exception as e:
        # Log the error but continue with deletion
        app.logger.error(f"Error removing image files: {e}")
    
    # Delete from database
    db.session.delete(product)
    db.session.commit()
    
    flash('Product deleted successfully!', 'success')
    return redirect(url_for('admin.products'))

# Bulk operations
@admin.route('/products/bulk-delete', methods=['POST'])
@login_required
@admin_required
def bulk_delete_products():
    product_ids = request.form.getlist('product_ids')
    
    if not product_ids:
        flash('No products selected', 'warning')
        return redirect(url_for('admin.products'))
    
    # Delete selected products
    for product_id in product_ids:
        product = Product.query.get(product_id)
        if product:
            db.session.delete(product)
    
    db.session.commit()
    flash(f'{len(product_ids)} products deleted successfully!', 'success')
    return redirect(url_for('admin.products'))

@app.route('/admin-signin', methods=['POST'])
def admin_signin():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    if email in ADMIN_USERS:
        stored_password = ADMIN_USERS[email]['password']
        if password == stored_password:
            # Authentication successful
            app.config['ADMIN_EMAILS'].append(current_user.email)
            return jsonify({'success': True})   
            return(redirect(url_for('dashboard')))
    
    # Authentication failed
    return jsonify({'success': False}), 401

# Initialize Database
with app.app_context():
    db.create_all()

app.register_blueprint(admin)

if __name__ == '__main__':
    app.run(debug=True)