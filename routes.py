from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from models import User, Product, Category, CartItem, Order, OrderItem
from werkzeug.security import generate_password_hash

main = Blueprint('main', __name__)
auth = Blueprint('auth', __name__)
products = Blueprint('products', __name__)
cart = Blueprint('cart', __name__)
checkout = Blueprint('checkout', __name__)

@main.route('/')
def home():
    categories = Category.query.all()
    featured_products = Product.query.limit(4).all()
    return render_template('home.html', categories=categories, featured_products=featured_products)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('main.home'))
        flash('Invalid email or password')
    return render_template('auth/login.html')

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect(url_for('auth.register'))
            
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
        return redirect(url_for('main.home'))
    return render_template('auth/register.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.home'))

@products.route('/catalog')
def catalog():
    category_id = request.args.get('category', type=int)
    search = request.args.get('search', '')
    sort = request.args.get('sort', 'name')

    if not Product.query.first():
        sample_categories = [
            Category(name='Electronics', description='Latest gadgets and electronics', 
                    banner_url='https://images.unsplash.com/photo-1498049794561-7780e7231661?w=500'),
            Category(name='Books', description='Books across all genres', 
                    banner_url='https://images.unsplash.com/photo-1495446815901-a7297e633e8d?w=500'),
            Category(name='Fashion', description='Trendy clothing and accessories', 
                    banner_url='https://images.unsplash.com/photo-1445205170230-053b83016050?w=500')
        ]

        for category in sample_categories:
            db.session.add(category)
        db.session.commit()

        sample_products = [
            {'name': 'Wireless Headphones', 'price': 99.99, 'category_id': 1, 
             'image_url': 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=500',
             'description': 'High-quality wireless headphones with noise cancellation'},
            {'name': 'Smart Watch', 'price': 199.99, 'category_id': 1, 
             'image_url': 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=500',
             'description': 'Feature-rich smartwatch with fitness tracking'},
            {'name': 'Best Seller Book', 'price': 19.99, 'category_id': 2, 
             'image_url': 'https://images.unsplash.com/photo-1544947950-fa07a98d237f?w=500',
             'description': 'International bestseller, must read'},
            {'name': 'Designer T-Shirt', 'price': 29.99, 'category_id': 3, 
             'image_url': 'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=500',
             'description': 'Comfortable cotton t-shirt with modern design'},
            {'name': 'Laptop Pro', 'price': 1299.99, 'category_id': 1, 
             'image_url': 'https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=500',
             'description': 'Powerful laptop for professionals'},
            {'name': 'Classic Novel', 'price': 15.99, 'category_id': 2, 
             'image_url': 'https://images.unsplash.com/photo-1543002588-bfa74002ed7e?w=500',
             'description': 'Timeless classic literature'}
        ]

        for product_data in sample_products:
            product = Product(**product_data, stock=100)
            db.session.add(product)
        db.session.commit()

    query = Product.query
    if category_id:
        query = query.filter_by(category_id=category_id)
    if search:
        query = query.filter(Product.name.ilike(f'%{search}%'))

    if sort == 'price_low':
        query = query.order_by(Product.price.asc())
    elif sort == 'price_high':
        query = query.order_by(Product.price.desc())
    else:
        query = query.order_by(Product.name.asc())

    products = query.all()
    categories = Category.query.all()
    return render_template('products/catalog.html', products=products, categories=categories)

@products.route('/product/<int:id>')
def product_detail(id):
    product = Product.query.get_or_404(id)
    return render_template('products/product_details.html', product=product)

@cart.route('/cart')
def view_cart():
    if current_user.is_authenticated:
        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    else:
        cart_items = []
        if 'cart' in session:
            for item in session['cart']:
                product = Product.query.get(item['product_id'])
                if product:
                    cart_items.append({'product': product, 'quantity': item['quantity']})
    return render_template('cart/cart.html', cart_items=cart_items)

@cart.route('/cart/add/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    quantity = int(request.form.get('quantity', 1))
    if current_user.is_authenticated:
        cart_item = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
        if cart_item:
            cart_item.quantity += quantity
        else:
            cart_item = CartItem(user_id=current_user.id, product_id=product_id, quantity=quantity)
            db.session.add(cart_item)
        db.session.commit()
    else:
        if 'cart' not in session:
            session['cart'] = []
        cart = session['cart']
        item_found = False
        for item in cart:
            if item['product_id'] == product_id:
                item['quantity'] += quantity
                item_found = True
                break
        if not item_found:
            cart.append({'product_id': product_id, 'quantity': quantity})
        session.modified = True
    return redirect(url_for('cart.view_cart'))

@cart.route('/cart/remove/<int:item_id>', methods=['POST'])
def remove_from_cart(item_id):
    if current_user.is_authenticated:
        cart_item = CartItem.query.filter_by(id=item_id, user_id=current_user.id).first()
        if cart_item:
            db.session.delete(cart_item)
            db.session.commit()
    else:
        if 'cart' in session:
            session['cart'] = [item for item in session['cart'] if item['product_id'] != item_id]
            session.modified = True
    return redirect(url_for('cart.view_cart'))

@checkout.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout_process():
    if request.method == 'POST':
        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        if not cart_items:
            flash('Your cart is empty')
            return redirect(url_for('cart.view_cart'))
            
        total_amount = sum(item.product.price * item.quantity for item in cart_items)
        order = Order(user_id=current_user.id, total_amount=total_amount)
        db.session.add(order)
        
        for cart_item in cart_items:
            order_item = OrderItem(
                order=order,
                product_id=cart_item.product_id,
                quantity=cart_item.quantity,
                price=cart_item.product.price
            )
            db.session.add(order_item)
            db.session.delete(cart_item)
            
        db.session.commit()
        flash('Order placed successfully!')
        return redirect(url_for('main.home'))
        
    return render_template('checkout/checkout.html')

def register_blueprints(app):
    app.register_blueprint(main)
    app.register_blueprint(auth, url_prefix='/auth')
    app.register_blueprint(products, url_prefix='/products')
    app.register_blueprint(cart, url_prefix='/cart')
    app.register_blueprint(checkout, url_prefix='/checkout')