from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    # Shop URLs
    path('', views.home, name='home'),
    path('shop/', views.shop_view, name='shop'),
    path('search/', views.search_view, name='search'),
    path('product/<slug:slug>/', views.product_detail_view, name='product_detail'),
    path('category/<slug:slug>/', views.category_view, name='category'),
    
    # Cart URLs
    path('cart/', views.cart_view, name='cart'),
    path('update-cart/', views.update_cart, name='update_cart'),
    path('add-to-cart/', views.add_to_cart, name='add_to_cart'),
    path('remove-from-cart/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    
    # Checkout URLs
    path('checkout/', views.checkout_view, name='checkout'),
    path('payment/', views.payment_view, name='payment'),
    path('order-confirmation/<str:order_oid>/', views.order_confirmation_view, name='order_confirmation'),
    
    # User Dashboard URLs
    path('dashboard/', views.dashboard, name='user_dashboard'),
    path('orders/', views.user_orders_view, name='user_orders'),
    path('order/<str:order_oid>/', views.user_order_detail_view, name='order_detail'),
    path('wishlist/', views.user_wishlist_view, name='wishlist'),
    path('add-to-wishlist/<int:product_id>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('remove-from-wishlist/<int:product_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),
    path('reviews/', views.user_reviews_view, name='user_reviews'),
    path('notifications/', views.user_notifications_view, name='notifications'),
    
    # FAQ URL
    path('product-faq/<int:product_id>/', views.product_faq_view, name='product_faq'),
    
    # Coupon URL
    path('apply-coupon/', views.apply_coupon, name='apply_coupon'),
    path('newsletter-subscribe/', views.newsletter_subscribe, name='newsletter_subscribe'),
]