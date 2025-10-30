from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator

# -------------------------------
# ✅ State Choices
# -------------------------------
STATE_CHOICES = (
    ('Punjab', 'Punjab'),
    ('Sindh', 'Sindh'),
    ('Khyber Pakhtunkhwa', 'Khyber Pakhtunkhwa'),
    ('Balochistan', 'Balochistan'),
    ('Islamabad Capital Territory', 'Islamabad Capital Territory'),
    ('Gilgit-Baltistan', 'Gilgit-Baltistan'),
    ('Azad Jammu and Kashmir', 'Azad Jammu and Kashmir'),
)

# -------------------------------
# ✅ Customer Model
# -------------------------------
class Customer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    locality = models.CharField(max_length=200)
    city = models.CharField(max_length=50)
    zipcode = models.IntegerField()
    state = models.CharField(choices=STATE_CHOICES, max_length=50)

    def __str__(self):
        return str(self.id)


# -------------------------------
# ✅ Product Model
# -------------------------------
CATEGORY_CHOICES = (
    ('M', 'Mobile'),
    ('L', 'Laptop'),
    ('TW', 'Top Wear'),
    ('BW', 'Bottom Wear'),
    ('S', 'Shoes'),
)

class Product(models.Model):
    title = models.CharField(max_length=100)
    selling_price = models.FloatField()
    discounted_price = models.FloatField()
    description = models.TextField()
    brand = models.CharField(max_length=100)
    category = models.CharField(choices=CATEGORY_CHOICES, max_length=2)
    product_image = models.ImageField(upload_to='productimg')

    def __str__(self):
        return str(self.id)


# -------------------------------
# ✅ Cart Model
# -------------------------------
class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return str(self.id)


# -------------------------------
# ✅ OrderPlaced Model (Updated)
# -------------------------------
STATUS_CHOICES = (
    ('Pending', 'Pending'),
    ('Accepted', 'Accepted'),
    ('Packed', 'Packed'),
    ('On The Way', 'On The Way'),
    ('Delivered', 'Delivered'),
    ('Cancel', 'Cancel'),
)

# ✅ Added new PAYMENT_CHOICES here
PAYMENT_CHOICES = (
    ('COD', 'Cash on Delivery'),
    ('DEBIT', 'Debit / Credit Card'),
    ('JAZZCASH', 'JazzCash'),
    ('EASYPAISA', 'EasyPaisa'),
    ('SADAPAY', 'SadaPay'),
)

class OrderPlaced(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    ordered_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Pending')
    # ✅ New field for payment method
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default='COD')
    # Tracking id for order tracking (UUID string)
    tracking_id = models.CharField(max_length=36, unique=True, null=True, blank=True)

    def __str__(self):
        return str(self.id)
