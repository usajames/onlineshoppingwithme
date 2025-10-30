# from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from app import views

urlpatterns = [
    # path('', views.home),
    path('', views.ProductView.as_view(), name='home'),
    path('product-detail/<int:pk>', views.ProductDetailView.as_view(), name='product-detail'),
    path('cart/', views.add_to_cart, name='add-to-cart'),
    path('buy/', views.buy_now, name='buy-now'),
    path('profile/', views.profile, name='profile'),
    path('address/', views.address, name='address'),
    path('orders/', views.orders, name='orders'),
    path('changepassword/', views.change_password, name='changepassword'),
    path('mobile/', views.mobile, name='mobile'),
    path('mobile/<slug:data>', views.mobile, name='mobiledata'),
    path('topwear/', views.topwear, name='topwear'),
    path('topwear/<slug:data>/', views.topwear, name='topweardata'),
    path('bottomwear/', views.bottomwear, name='bottomwear'),
    path('bottomwear/<slug:data>/', views.bottomwear, name='bottomweardata'),
    path('shoes/', views.shoes, name='shoes'),
    path('shoes/<slug:data>/', views.shoes, name='shoesdata'),
    path('laptops/', views.laptop, name='laptop'),
    path('laptops/<slug:data>/', views.laptop, name='laptopdata'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('registration/', views.CustomerRegistrationView.as_view(), name='customerregistration'),  # ✅ comma added
    path('checkout/', views.checkout, name='checkout'),
    path('paymentdone/', views.payment_done, name='payment-done'),
    path('search/', views.search, name='search'),
    path('api/cart/update/', views.cart_update_api, name='cart-update-api'),
    path('cart/remove/<int:cart_id>/', views.remove_from_cart, name='remove-from-cart'),
    path('cart/update/<int:cart_id>/<str:action>/', views.update_cart_quantity, name='update-cart-quantity'),
    path('trackorder/', views.track_order, name='track-order'),
    path('csrf-debug/', views.csrf_debug, name='csrf-debug'),
    path('order/cancel/<int:order_id>/', views.cancel_order, name='cancel-order'),
    path('order/return/<int:order_id>/', views.return_order, name='return-order'),
    path('forgot-password/', views.forgot_password, name='forgot-password'),
        path('profiles/clear/', views.clear_profiles, name='clear-profiles'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
