from django.shortcuts import render
from django.views import View
from .models import Customer, Product, Cart, OrderPlaced
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
    return render(request, 'app/addtocart.html')


def buy_now(request):
    return render(request, 'app/buynow.html')


def profile(request):
    return render(request, 'app/profile.html')


def address(request):
    return render(request, 'app/address.html')


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


def login(request):
    return render(request, 'app/login.html')


# ✅ Customer Registration View (CSRF + Validation Fixed)
class CustomerRegistrationView(View):
    def get(self, request):
        form = CustomerRegistrationForm()
        return render(request, 'app/customerregistration.html', {'form': form})

    def post(self, request):
        form = CustomerRegistrationForm(request.POST)
        msg = ""
        if form.is_valid():
            form.save()
            msg = "Account created successfully!"
            form = CustomerRegistrationForm()  # Clear form after save
        return render(request, 'app/customerregistration.html', {'form': form, 'msg': msg})


def checkout(request):
    return render(request, 'app/checkout.html')
