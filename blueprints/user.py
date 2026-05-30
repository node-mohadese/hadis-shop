from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, login_required, current_user, logout_user
from passlib.hash import sha256_crypt
from extentions import db
from models.cart import Cart
from models.cart_item import CartItem
from models.payment import Payment
from models.product import Product
from models.user import User
import re
import uuid

app = Blueprint("user", __name__)


# ================= LOGIN / REGISTER =================
@app.route('/user/login', methods=['GET', 'POST'])
def login():

    if request.method == 'GET':
        if current_user.is_authenticated:
            return redirect(url_for('user.dashboard'))
        return render_template('user/login.html')

    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    register = request.form.get('register', None)
    phone = request.form.get('phone', None)
    address = request.form.get('address', None)

    # جلوگیری از خالی بودن
    if not username or not password:
        flash("نام کاربری و رمز عبور الزامی است")
        return redirect(url_for('user.login'))

    # ================= REGISTER =================
    if register:

        if phone and not re.fullmatch(r'09\d{9}', phone):
            flash("شماره تلفن نامعتبر است")
            return redirect(url_for('user.login'))

        if address and len(address) < 10:
            flash("آدرس خیلی کوتاه است")
            return redirect(url_for('user.login'))

        if User.query.filter_by(username=username).first():
            flash("نام کاربری قبلاً استفاده شده")
            return redirect(url_for('user.login'))

        user = User(
            username=username,
            password=sha256_crypt.encrypt(password),
            phone=phone,
            address=address
        )

        db.session.add(user)
        db.session.commit()

        login_user(user)

        _merge_guest_cart_to_user(user)

        return redirect(url_for('user.dashboard'))

    # ================= LOGIN =================
    user = User.query.filter_by(username=username).first()

    if not user:
        flash("کاربر پیدا نشد")
        return redirect(url_for('user.login'))

    if not sha256_crypt.verify(password, user.password):
        flash("رمز اشتباه است")
        return redirect(url_for('user.login'))

    login_user(user)

    _merge_guest_cart_to_user(user)

    next_page = request.args.get('next')
    return redirect(next_page or url_for('user.dashboard'))


# ================= MERGE GUEST CART =================
def _merge_guest_cart_to_user(user):

    if 'cart_items' not in session:
        return

    cart = user.carts.filter(Cart.status == 'pending').first()

    if not cart:
        cart = Cart()
        user.carts.append(cart)
        db.session.add(cart)
        db.session.commit()

    for pid, qty in session['cart_items'].items():

        product = Product.query.get(int(pid))
        if not product:
            continue

        item = CartItem.query.filter_by(
            cart_id=cart.id,
            product_id=product.id
        ).first()

        if item:
            item.quantity += qty
        else:
            db.session.add(CartItem(
                quantity=qty,
                price=product.price,
                product=product,
                cart=cart
            ))

    db.session.commit()
    session.pop('cart_items', None)


# ================= ADD TO CART =================
@app.route('/add-to-cart')
def add_to_cart():

    product_id = request.args.get('id')
    product = Product.query.filter_by(id=product_id).first_or_404()

    if current_user.is_authenticated:

        cart = current_user.carts.filter(Cart.status == 'pending').first()

        if not cart:
            cart = Cart()
            current_user.carts.append(cart)
            db.session.add(cart)
            db.session.commit()

        item = CartItem.query.filter_by(
            cart_id=cart.id,
            product_id=product.id
        ).first()

        if item:
            item.quantity += 1
        else:
            db.session.add(CartItem(
                quantity=1,
                price=product.price,
                product=product,
                cart=cart
            ))

        db.session.commit()
        flash("محصول اضافه شد")
        return redirect(url_for('user.cart'))

    # guest cart
    if 'cart_items' not in session:
        session['cart_items'] = {}

    pid = str(product.id)
    session['cart_items'][pid] = session['cart_items'].get(pid, 0) + 1
    session.modified = True

    return redirect(url_for('user.login', next=url_for('user.cart')))


# ================= CART =================
@app.route('/cart')
@login_required
def cart():
    cart = current_user.carts.filter(Cart.status == "pending").first()
    return render_template('user/cart.html', cart=cart)


# ================= REMOVE FROM CART =================
@app.route('/remove-from-cart')
@login_required
def remove_from_cart():

    item_id = request.args.get('id')
    item = CartItem.query.filter_by(id=item_id).first_or_404()

    if item.quantity > 1:
        item.quantity -= 1
    else:
        db.session.delete(item)

    db.session.commit()
    return redirect(url_for('user.cart'))


# ================= PAYMENT =================
@app.route('/payment')
@login_required
def payment():

    cart = current_user.carts.filter(Cart.status == 'pending').first()

    if not cart or not cart.cart_items:
        flash("سبد خرید خالی است")
        return redirect(url_for('user.cart'))

    token = str(uuid.uuid4())

    pay = Payment(
        price=cart.total_price(),
        token=token
    )

    pay.cart = cart
    db.session.add(pay)
    db.session.commit()

    return render_template("user/mock_payment.html", token=token)


# ================= VERIFY =================
@app.route('/verify')
def verify():

    token = request.args.get('token')
    status = request.args.get('status')

    pay = Payment.query.filter_by(token=token).first_or_404()
    user = pay.cart.user

    login_user(user)

    if status == "success":
        pay.status = "success"
        pay.cart.status = "paid"
        flash("پرداخت موفق بود")
    else:
        pay.status = "failed"
        pay.cart.status = "rejected"
        flash("پرداخت ناموفق بود")

    new_cart = Cart(status="pending")
    user.carts.append(new_cart)

    db.session.add(new_cart)
    db.session.commit()

    return redirect(url_for('user.dashboard'))


# ================= DASHBOARD =================
@app.route('/user/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():

    if request.method == "GET":
        return render_template('user/dashboard.html')

    username = request.form.get('username')
    password = request.form.get('password')
    phone = request.form.get('phone')
    address = request.form.get('address')

    if phone and not re.fullmatch(r'09\d{9}', phone):
        flash("شماره نامعتبر است")
        return redirect(url_for('user.dashboard'))

    if address and len(address) < 10:
        flash("آدرس خیلی کوتاه است")
        return redirect(url_for('user.dashboard'))

    current_user.phone = phone
    current_user.address = address

    if username and username != current_user.username:
        if User.query.filter_by(username=username).first():
            flash("نام کاربری تکراری است")
            return redirect(url_for('user.dashboard'))
        current_user.username = username

    if password:
        current_user.password = sha256_crypt.encrypt(password)

    db.session.commit()

    flash("تغییرات ذخیره شد")
    return redirect(url_for('user.dashboard'))


# ================= LOGOUT =================
@app.route('/user/logout')
@login_required
def logout():
    logout_user()
    flash("خارج شدید")
    return redirect('/')