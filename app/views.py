from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from .models import Customer, Product, Cart, OrderPlaced
from django.db.models import Q
from django.http import JsonResponse
import uuid
from .forms import CustomerRegistrationForm
from django.middleware.csrf import get_token
from django.contrib.auth.models import User
from django.utils.crypto import get_random_string


# ✅ Home Page View (Class-Based)
class ProductView(View):
    def get(self, request):
        topwears = Product.objects.filter(category='TW')
        bottomwears = Product.objects.filter(category='BW')
        mobiles = Product.objects.filter(category='M')
        laptops = Product.objects.filter(category='L')
        shoes = Product.objects.filter(category='S')

        return render(
            request,
            'app/home.html',
            {
                'topwears': topwears,
                'bottomwears': bottomwears,
                'mobiles': mobiles,
                'laptops': laptops,
                'shoes': shoes,
            }
        )


# ✅ Product Detail View
class ProductDetailView(View):
    def get(self, request, pk):
        product = Product.objects.get(pk=pk)
        return render(request, 'app/productdetail.html', {'product': product})


# ✅ Other Views
def add_to_cart(request):
    """Add a product to the logged-in user's cart (via ?product_id=) or
    render the cart page showing current cart items.
    """
    if not request.user.is_authenticated:
        # Redirect anonymous users to login page
        return redirect('login')

    # If product_id provided, add/update cart and redirect to cart page
    product_id = request.GET.get('product_id')
    if product_id:
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return redirect('home')

        cart_item, created = Cart.objects.get_or_create(user=request.user, product=product)
        if not created:
            cart_item.quantity = cart_item.quantity + 1
            cart_item.save()

        return redirect('add-to-cart')

    # No product_id -> render the cart page
    cart_items = Cart.objects.filter(user=request.user).select_related('product')

    # Compute totals
    amount = 0
    shipping = 0
    for item in cart_items:
        line = item.quantity * item.product.discounted_price
        # attach a convenience attribute for template rendering
        item.line_total = line
        amount += line

    # simple shipping rule: free over 5000, else fixed 70
    shipping = 0 if amount > 5000 else 70
    total = amount + shipping

    return render(request, 'app/addtocart.html', {
        'cart_items': cart_items,
        'amount': amount,
        'shipping': shipping,
        'total': total,
    })


@login_required
def remove_from_cart(request, cart_id):
    """Remove a cart item and redirect back to the cart page."""
    cart_item = get_object_or_404(Cart, id=cart_id, user=request.user)
    cart_item.delete()
    return redirect('add-to-cart')


@login_required
def update_cart_quantity(request, cart_id, action):
    """Increase or decrease the quantity of a cart item.
    action should be 'inc' or 'dec'. If quantity reaches 0, remove the item.
    """
    cart_item = get_object_or_404(Cart, id=cart_id, user=request.user)
    if action == 'inc':
        cart_item.quantity += 1
        cart_item.save()
    elif action == 'dec':
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
        else:
            cart_item.delete()

    return redirect('add-to-cart')


@login_required
def cart_update_api(request):
    """AJAX-friendly endpoint to update cart item quantity and return updated totals as JSON."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)

    cart_id = request.POST.get('cart_id')
    action = request.POST.get('action')
    if not cart_id or not action:
        return JsonResponse({'error': 'cart_id and action required'}, status=400)

    try:
        cart_item = Cart.objects.get(id=cart_id, user=request.user)
    except Cart.DoesNotExist:
        return JsonResponse({'error': 'Cart item not found'}, status=404)

    # perform action
    if action == 'inc':
        cart_item.quantity += 1
        cart_item.save()
    elif action == 'dec':
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
        else:
            # if reducing below 1, remove the item
            cart_item.delete()
            # indicate the item was removed
            removed = True
    else:
        return JsonResponse({'error': 'invalid action'}, status=400)

    # recompute totals
    cart_items = Cart.objects.filter(user=request.user).select_related('product')
    amount = 0
    for it in cart_items:
        amount += it.quantity * it.product.discounted_price

    shipping = 0 if amount > 5000 else 70
    total = amount + shipping

    # line total for this item (if still exists)
    try:
        new_item = Cart.objects.get(id=cart_id, user=request.user)
        line_total = new_item.quantity * new_item.product.discounted_price
        new_quantity = new_item.quantity
    except Cart.DoesNotExist:
        line_total = 0
        new_quantity = 0

    return JsonResponse({
        'success': True,
        'cart_id': int(cart_id),
        'quantity': new_quantity,
        'line_total': float(line_total),
        'amount': float(amount),
        'shipping': float(shipping),
        'total': float(total),
    })


def buy_now(request):
    # Buy a single product (product_id) or show the buy form
    if not request.user.is_authenticated:
        return redirect('login')

    product_id = request.GET.get('product_id') or request.POST.get('product_id')

    if request.method == 'POST':
        # handle form submission: either create address and/or use selected custid
        custid = request.POST.get('custid')
        # create new address if provided
        if not custid and request.POST.get('name'):
            name = request.POST.get('name')
            locality = request.POST.get('locality')
            city = request.POST.get('city')
            zipcode = request.POST.get('zipcode')
            state = request.POST.get('state')
            customer = Customer.objects.create(
                user=request.user,
                name=name,
                locality=locality,
                city=city,
                zipcode=zipcode,
                state=state,
            )
            custid = customer.id

        payment_method = request.POST.get('payment_method') or 'COD'

        # If product_id is provided, create an OrderPlaced for that product
        if product_id:
            try:
                product = Product.objects.get(id=product_id)
            except Product.DoesNotExist:
                return redirect('home')

            quantity = int(request.POST.get('quantity') or 1)
            tracking = str(uuid.uuid4())
            OrderPlaced.objects.create(
                user=request.user,
                customer=Customer.objects.get(id=custid),
                product=product,
                quantity=quantity,
                status='Accepted',
                payment_method=payment_method,
                tracking_id=tracking,
            )

            return render(request, 'app/order_success.html', {
                'payment_method': payment_method,
                'tracking_id': tracking,
            })

        # If no product_id, behave similar to checkout/payment_done for cart
        # reuse payment_done behaviour
        return payment_done(request)

    # GET: render buy now form with user's addresses and product info
    addresses = Customer.objects.filter(user=request.user)
    product = None
    if product_id:
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            product = None

    return render(request, 'app/buynow.html', {
        'addresses': addresses,
        'product': product,
    })


def profile(request):
    # Show only the logged-in user's saved addresses/profiles
    if not request.user.is_authenticated:
        return redirect('login')

    customers = Customer.objects.filter(user=request.user)
    return render(request, 'app/profile.html', {'customers': customers})


def address(request):
    if not request.user.is_authenticated:
        return redirect('login')

    if request.method == 'POST':
        name = request.POST.get('name')
        locality = request.POST.get('locality')
        city = request.POST.get('city')
        zipcode = request.POST.get('zipcode')
        state = request.POST.get('state')
        if name and locality and city and zipcode and state:
            Customer.objects.create(
                user=request.user,
                name=name,
                locality=locality,
                city=city,
                zipcode=int(zipcode),
                state=state,
            )
            messages.success(request, 'Address added')
            return redirect('address')

    customers = Customer.objects.filter(user=request.user)
    return render(request, 'app/address.html', {'customers': customers})


@login_required
def clear_profiles(request):
    # Admin-only: delete all Customer profiles
    if not request.user.is_superuser:
        messages.error(request, 'Unauthorized')
        return redirect('home')

    Customer.objects.all().delete()
    messages.success(request, 'All profiles deleted')
    return redirect('home')


def orders(request):
    # Show all orders placed by the logged-in user
    if not request.user.is_authenticated:
        return redirect('login')

    user_orders = OrderPlaced.objects.filter(user=request.user).select_related('product', 'customer')
    return render(request, 'app/orders.html', {'orders': user_orders})


def change_password(request):
    return render(request, 'app/changepassword.html')


# ✅ Mobile View
def mobile(request, data=None):
    if data is None:
        mobiles = Product.objects.filter(category='M')
    elif data.upper() in ['REDMI', 'SAMSUNG']:
        mobiles = Product.objects.filter(category='M', brand=data)
    elif data == 'below':
        mobiles = Product.objects.filter(category='M', discounted_price__lt=15000)
    elif data == 'above':
        mobiles = Product.objects.filter(category='M', discounted_price__gt=15000)
    else:
        mobiles = Product.objects.filter(category='M')

    return render(request, 'app/mobile.html', {'mobiles': mobiles})


# Top Wear view
def topwear(request, data=None):
    if data is None:
        topwears = Product.objects.filter(category='TW')
    elif data == 'below':
        topwears = Product.objects.filter(category='TW', discounted_price__lt=1000)
    elif data == 'above':
        topwears = Product.objects.filter(category='TW', discounted_price__gt=1000)
    else:
        topwears = Product.objects.filter(category='TW')

    return render(request, 'app/topware.html', {'topwears': topwears})


# Bottom Wear view
def bottomwear(request, data=None):
    if data is None:
        bottomwears = Product.objects.filter(category='BW')
    elif data == 'below':
        bottomwears = Product.objects.filter(category='BW', discounted_price__lt=1000)
    elif data == 'above':
        bottomwears = Product.objects.filter(category='BW', discounted_price__gt=1000)
    else:
        bottomwears = Product.objects.filter(category='BW')

    return render(request, 'app/bottomware.html', {'bottomwears': bottomwears})


# Search view
def search(request):
    q = request.GET.get('q', '')
    results = []
    if q:
        results = Product.objects.filter(
            Q(title__icontains=q) |
            Q(brand__icontains=q) |
            Q(description__icontains=q)
        )
    return render(request, 'app/search_results.html', {'query': q, 'results': results})


# ✅ Shoes View
def shoes(request, data=None):
    if data is None:
        shoes = Product.objects.filter(category='S')  # All shoes
    elif data.upper() in ['KNCHDE', 'MYNOT']:  # Match your brands here
        shoes = Product.objects.filter(category='S', brand=data)
    elif data == 'below':
        shoes = Product.objects.filter(category='S', discounted_price__lt=2500)
    elif data == 'above':
        shoes = Product.objects.filter(category='S', discounted_price__gt=3000)
    else:
        shoes = Product.objects.filter(category='S')

    return render(request, 'app/shoes.html', {'shoes': shoes})


# ✅ Laptop View
def laptop(request, data=None):
    if data is None:
        laptops = Product.objects.filter(category='L')  # All laptops
    elif data.upper() in ['HP', 'DELL']:  # Brand filters
        laptops = Product.objects.filter(category='L', brand=data)
    elif data == 'below':
        laptops = Product.objects.filter(category='L', discounted_price__lt=20000)
    elif data == 'above':
        laptops = Product.objects.filter(category='L', discounted_price__gt=25000)
    else:
        laptops = Product.objects.filter(category='L')

    return render(request, 'app/laptop.html', {'laptops': laptops})


def login(request):
    # Handle GET (render) and POST (authenticate)
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            # detect if this is the user's first login by checking last_login
            first_login = user.last_login is None
            auth_login(request, user)
            if first_login:
                messages.success(request, 'Welcome — your profile is created. Please review your details.')
                return redirect('profile')

            messages.success(request, 'Login successfully')
            return redirect('home')
        else:
            messages.error(request, 'Invalid username or password')
            return render(request, 'app/login.html')

    return render(request, 'app/login.html')


# ✅ Customer Registration View
class CustomerRegistrationView(View):
    def get(self, request):
        form = CustomerRegistrationForm()
        return render(request, 'app/customerregistration.html', {'form': form})

    def post(self, request):
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Registration successfully')
            return redirect('login')

        # If form invalid, render with errors
        return render(request, 'app/customerregistration.html', {'form': form})


# ✅ Checkout Page View
def checkout(request):
    return render(request, 'app/checkout.html')


# ✅ Payment Done View
@login_required
def payment_done(request):
    user = request.user
    custid = request.GET.get('custid') or request.POST.get('custid')
    payment_method = request.POST.get('payment_method')  # 👈 Selected payment method

    if not custid:
        return render(request, 'app/checkout.html', {'error': 'Customer not selected'})

    customer = Customer.objects.get(id=custid)
    cart_items = Cart.objects.filter(user=user)

    for item in cart_items:
        OrderPlaced(
            user=user,
            customer=customer,
            product=item.product,
            quantity=item.quantity,
            status='Accepted',  # Default status
            payment_method=payment_method,
            tracking_id=str(uuid.uuid4()),
        ).save()

    cart_items.delete()

    return render(request, 'app/order_success.html', {
        'payment_method': payment_method,
    })


def logout_view(request):
    """Log out the user and show a message."""
    # Per request: delete ALL Customer profiles when a user logs out so that
    # subsequent logins/registrations only show the current user's profile.
    # WARNING: This is destructive and removes all saved addresses/profiles.
    try:
        Customer.objects.all().delete()
    except Exception:
        # don't block logout on deletion errors
        pass

    auth_logout(request)
    messages.info(request, 'You are logged out. All previous profiles were removed.')
    return redirect('login')


def track_order(request):
    """Allow users to enter a tracking id and view associated order(s)."""
    orders = None
    tracking = ''
    # support GET (e.g., /trackorder/?tracking_id=...) and POST from the form
    if request.method == 'POST':
        tracking = request.POST.get('tracking_id', '').strip()
    else:
        tracking = request.GET.get('tracking_id', '').strip()

    if tracking:
        orders = OrderPlaced.objects.filter(tracking_id=tracking)
        if not orders.exists():
            messages.error(request, 'No orders found for that tracking id')

    return render(request, 'app/track_order.html', {'orders': orders, 'tracking': tracking})


@login_required
def cancel_order(request, order_id):
    # only accept POST for cancel to avoid accidental GET cancels
    if request.method != 'POST':
        messages.error(request, 'Invalid request method')
        return redirect('track-order')

    order = get_object_or_404(OrderPlaced, id=order_id)
    # only allow owner to cancel
    if order.user != request.user:
        messages.error(request, 'Unauthorized')
        return redirect('track-order')

    if order.status in ['Cancelled', 'Returned']:
        messages.info(request, 'Order already cancelled or returned')
    else:
        order.status = 'Cancelled'
        order.save()
        messages.success(request, 'Order cancelled')

    return redirect('track-order')


@login_required
def return_order(request, order_id):
    if request.method != 'POST':
        messages.error(request, 'Invalid request method')
        return redirect('track-order')

    order = get_object_or_404(OrderPlaced, id=order_id)
    if order.user != request.user:
        messages.error(request, 'Unauthorized')
        return redirect('track-order')

    if order.status == 'Returned':
        messages.info(request, 'Order already returned')
    else:
        order.status = 'Returned'
        order.save()
        messages.success(request, 'Order marked as returned')

    return redirect('track-order')


def forgot_password(request):
    """Simple dev-only password reset: regenerate a password and show it to the user.

    NOTE: This is not secure for production. For production use Django's
    password reset via email tokens.
    """
    new_password = None
    if request.method == 'POST':
        identifier = request.POST.get('identifier', '').strip()
        user = None
        if identifier:
            # try by username then by email
            try:
                user = User.objects.get(username=identifier)
            except User.DoesNotExist:
                try:
                    user = User.objects.get(email=identifier)
                except User.DoesNotExist:
                    user = None

        if not user:
            messages.error(request, 'No user found with that username or email')
        else:
            new_password = get_random_string(8)
            user.set_password(new_password)
            user.save()
            messages.success(request, 'Password regenerated; please note it carefully')

    return render(request, 'app/forgot_password.html', {'new_password': new_password})


def csrf_debug(request):
    """Development-only view to help debug CSRF token mismatches.

    Shows the CSRF token that Django generated for this request and the
    csrftoken cookie value sent by the browser. Use this to compare and
    diagnose token rotation / cookie issues.
    """
    # generate/get the token for this request
    token = get_token(request)
    cookie_val = request.COOKIES.get('csrftoken')
    return render(request, 'app/csrf_debug.html', {
        'token': token,
        'cookie_val': cookie_val,
    })
