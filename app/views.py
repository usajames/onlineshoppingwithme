from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from .models import Customer, Product, Cart, OrderPlaced
from django.db.models import Q
import uuid
from .forms import CustomerRegistrationForm


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
    return render(request, 'app/orders.html')


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
            auth_login(request, user)
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
    auth_logout(request)
    messages.info(request, 'You are logged out')
    return redirect('login')
