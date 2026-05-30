from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, login_required, current_user, logout_user
from passlib.hash import sha256_crypt
from extentions import db
from models.cart import Cart
from models.cart_item import CartItem
from models.payment import Payment
from models.product import Product
from models.user import User
import requests
import config
from flask import session
app = Blueprint("user", __name__)


@app.route('/user/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        if current_user.is_authenticated:
            return redirect(url_for('user.dashboard'))
        return render_template('user/login.html')
    else:
        register = request.form.get('register', None)
        username = request.form.get('username', None)
        password = request.form.get('password', None)
        phone = request.form.get('phone', None)
        address = request.form.get('address', None)

    if register != None:
        # 1️⃣ ثبت‌نام کاربر
        user = User.query.filter(User.username == username).first()
        if user:
            flash('نام کاربری دیگری انتخاب کنید.')
            return redirect(url_for('user.login'))

        user = User(username=username, password=sha256_crypt.encrypt(password), phone=phone, address=address)
        db.session.add(user)
        db.session.commit()

        # 2️⃣ ورود کاربر
        login_user(user)

        # خیلی مهم: تازه کردن شیء کاربر بعد از لاگین
        db.session.refresh(user)

        # 3️⃣ گرفتن یا ایجاد cart
        cart = user.carts.filter(Cart.status == 'pending').first()
        if not cart:
            cart = Cart()
            user.carts.append(cart)
            db.session.add(cart)
            db.session.commit()

        # 4️⃣ انتقال محصولات session به cart
        if 'cart_items' in session:
            for pid in session.get('cart_items', []):
                product = Product.query.get(pid)
                if product:
                    cart_item = CartItem.query.filter_by(
                        cart_id=cart.id,
                        product_id=product.id
                    ).first()
                    if cart_item:
                        cart_item.quantity += 1
                    else:
                        new_item = CartItem(
                            quantity=1,
                            price=product.price,
                            product=product,
                            cart=cart
                        )
                        db.session.add(new_item)
            db.session.commit()
            session.pop('cart_items', None)

        # هدایت به صفحه بعدی
        next_page = request.args.get('next')
        return redirect(next_page or url_for('user.dashboard'))

    else:
        user = User.query.filter(User.username == username).first()
        if user is None:
            flash('نام کاربری یا رمز اشتباه است.')
            return redirect(url_for('user.login'))
        if sha256_crypt.verify(password, user.password):
            # ورود موفق
            login_user(user)

            # تازه کردن شیء کاربر بعد از لاگین (همانند ثبت‌نام)
            db.session.refresh(user)

            # گرفتن یا ایجاد cart
            cart = user.carts.filter(Cart.status == 'pending').first()
            if not cart:
                cart = Cart()
                user.carts.append(cart)
                db.session.add(cart)
                db.session.commit()

            # انتقال محصولات session به cart (تکرار کد برای ورود معمولی)
            if 'cart_items' in session:
                for pid in session.get('cart_items', []):
                    product = Product.query.get(pid)
                    if product:
                        cart_item = CartItem.query.filter_by(
                            cart_id=cart.id,
                            product_id=product.id
                        ).first()
                        if cart_item:
                            cart_item.quantity += 1
                        else:
                            new_item = CartItem(
                                quantity=1,
                                price=product.price,
                                product=product,
                                cart=cart
                            )
                            db.session.add(new_item)
                db.session.commit()
                session.pop('cart_items', None)

            next_page = request.args.get('next')
            return redirect(next_page or url_for('user.dashboard'))
        else:
            flash('نام کاربری یا رمز اشتباه است')
            return redirect(url_for('user.login'))



@app.route('/add-to-cart', methods=['GET'])
def add_to_cart():
    product_id = request.args.get('id')
    product = Product.query.filter(Product.id == product_id).first_or_404()

    if current_user.is_authenticated:
        # کاربر لاگین کرده
        cart = current_user.carts.filter(Cart.status == 'pending').first()
        if not cart:
            cart = Cart()
            current_user.carts.append(cart)
            db.session.add(cart)
            db.session.commit()

        # چک کردن اینکه قبلاً این محصول هست یا نه
        cart_item = CartItem.query.filter_by(cart_id=cart.id, product_id=product.id).first()

        if cart_item:
            cart_item.quantity += 1
        else:
            new_item = CartItem(
                quantity=1,
                price=product.price,
                product=product,
                cart=cart
            )
            db.session.add(new_item)

        db.session.commit()
        flash('محصول با موفقیت به سبد خرید اضافه شد.')
        return redirect(url_for('user.cart'))

    else:
        # کاربر مهمان → ذخیره در session
        if 'cart_items' not in session:
            session['cart_items'] = {}

        pid = str(product.id)
        if pid in session['cart_items']:
            session['cart_items'][pid] += 1
        else:
            session['cart_items'][pid] = 1

        session.modified = True

        flash("برای افزودن محصول به سبد خرید، ابتدا وارد حساب کاربری شوید.")
        # مهم: مستقیم به سبد خرید برود، نه دوباره add-to-cart
        return redirect(url_for('user.login', next=url_for('user.cart')))

@app.route('/remove-from-cart', methods=['GET'])
@login_required
def remove_from_cart():
    id = request.args.get('id')
    cart_item = CartItem.query.filter(CartItem.id == id).first_or_404()
    if cart_item.quantity > 1:
        cart_item.quantity -= 1
    else:
        db.session.delete(cart_item)

    db.session.commit()

    return redirect(url_for('user.cart'))


@app.route('/cart', methods=['GET'])
@login_required
def cart():
    cart = current_user.carts.filter(Cart.status == "pending").first()
    return render_template('user/cart.html', cart=cart)


@app.route('/payment', methods=['GET'])
@login_required
def payment():
    cart = current_user.carts.filter(Cart.status == 'pending').first()

    import uuid
    token = str(uuid.uuid4())
    url = url_for('user.dashboard')

    pay = Payment(price=cart.total_price(), token=token)
    pay.cart = cart
    db.session.add(pay)
    db.session.commit()

    flash("پرداخت تستی موفق بود (Mock Mode)")
    return redirect(url)

@app.route('/verify', methods=['GET'])
def verify():
    token = request.args.get('token')
    pay = Payment.query.filter(Payment.token == token).first_or_404()

    user = pay.cart.user
    login_user(user)

    # 🔥 MOCK VERIFY
    pay.status = 'success'
    pay.cart.status = 'paid'
    db.session.commit()

    flash("پرداخت تستی موفق بود (Mock Verify)")
    return redirect(url_for('user.dashboard'))
@app.route('/user/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    if request.method == "GET":
        return render_template('user/dashboard.html')
    else:
        username = request.form.get('username', None)
        password = request.form.get('password', None)
        phone = request.form.get('phone', None)
        address = request.form.get('address', None)

        if current_user.username != username:
            user = User.query.filter(User.username == username).first()
            if user != None:
                flash('نام کاربری از قبل انتخاب شده است.')
                return redirect(url_for('user.dashboard'))
            else:
                current_user.username = username

        if password != None:
            current_user.password =sha256_crypt.encrypt(password)

        current_user.address =address
        current_user.phone =phone
        db.session.commit()

        flash('تغییرات با موفقیت ثبت شد')
        return redirect(url_for('user.dashboard'))

@app.route('/user/logout', methods=['GET'])
@login_required
def logout():
    logout_user()
    flash('با موفقیت خارج شدید.')
    return redirect('/')

@app.route('/user/dashbard/order/<id>', methods=['GET'])
@login_required
def order(id):
    cart = current_user.carts.filter(Cart.id == id).first_or_404()

    return render_template('user/order.html', cart=cart)