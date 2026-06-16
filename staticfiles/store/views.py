import json
from django.db.models.functions import TruncMonth, TruncDate
from django.db import models
from django.db.models import Avg, Count, F
from django.db.models.functions import Cast # Eita add korun
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Avg, Count, Sum, F
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse
from django.db import transaction
from decimal import Decimal
import uuid

from .models import (
    Category, Product, Gallery, Specification, Size, Color, Wshlist,
    Cart, CartOrder, CartOrderItem, ProductFeq, Review, Notification, Coupon, Tax, Banner, Newsletter
)
from vendor.models import Vendor
from userauths.models import User, Profile
from django.utils import timezone
from datetime import timedelta
from django.db import models


def home(request):
    """Complete home page view with all sections"""
    
    # Get active banners
    banners = Banner.objects.filter(active=True).order_by('order', '-created_at')
    
    # Get all active categories
    categories = Category.objects.filter(active=True)[:8]
    
    # Featured Products
    featured_products = Product.objects.filter(
        featured=True, 
        status='published',
        in_stock=True
    ).select_related('vendor', 'category')[:12]
    
    # New Arrivals (Last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    new_arrivals = Product.objects.filter(
        status='published',
        in_stock=True,
        date__gte=thirty_days_ago
    ).order_by('-date')[:8]
    
    # Best Sellers (Top rated products)
    best_sellers = Product.objects.filter(
        status='published',
        in_stock=True
    ).annotate(
        avg_rating=Avg('review__rating')
    ).filter(avg_rating__gte=4.0).order_by('-avg_rating')[:8]
    
    # Special Offers (Discounted products)
    special_offers = Product.objects.filter(
        status='published',
        in_stock=True,
        old_price__gt=0
    ).exclude(old_price=0.00).exclude(old_price__lte=models.F('price'))[:8]
    
    # Flash Sale Products (Products with highest discount)
    # Flash Sale Logic (IMPORTANT: models.F update kora hoyeche)
    flash_sale = Product.objects.filter(
        status='published',
        in_stock=True,
        old_price__gt=0
    ).annotate(
        # Discount percent calculate korchi
        calc_discount=Cast((F('old_price') - F('price')) * 100 / F('old_price'), models.IntegerField())
    ).filter(calc_discount__gte=20).order_by('-calc_discount')[:6]
    
    # Top Rated Products
    top_rated = Product.objects.filter(
        status='published',
        in_stock=True
    ).annotate(
        avg_rating=Avg('review__rating'),
        review_count=Count('review')
    ).filter(review_count__gte=1).order_by('-avg_rating')[:8]
    
    # Get cart count for logged in user
    cart_count = 0
    wishlist_count = 0
    wishlist_products = []
    
    if request.user.is_authenticated:
        cart_id = request.session.get('cart_id')
        if cart_id:
            cart_count = Cart.objects.filter(
                user=request.user, 
                cart_id=cart_id
            ).count()
        
        wishlist_count = Wshlist.objects.filter(user=request.user).count()
        wishlist_products = list(Wshlist.objects.filter(
            user=request.user
        ).values_list('product_id', flat=True))
    
    # Recently viewed products (from session)
    recently_viewed_ids = request.session.get('recently_viewed', [])
    recently_viewed = Product.objects.filter(
        id__in=recently_viewed_ids,
        status='published'
    )[:4] if recently_viewed_ids else []
    
    # Service highlights
    services = [
        {
            'icon': 'fas fa-truck-fast',
            'title': 'Free Delivery',
            'description': 'Free delivery on orders over $50'
        },
        {
            'icon': 'fas fa-rotate-left',
            'title': 'Easy Returns',
            'description': '30 days easy return policy'
        },
        {
            'icon': 'fas fa-lock',
            'title': 'Secure Payment',
            'description': '100% secure payment system'
        },
        {
            'icon': 'fas fa-headset',
            'title': '24/7 Support',
            'description': 'Dedicated customer support'
        }
    ]
    
    context = {
        'banners': banners,
        'categories': categories,
        'featured_products': featured_products,
        'new_arrivals': new_arrivals,
        'best_sellers': best_sellers,
        'special_offers': special_offers,
        'flash_sale': flash_sale,
        'top_rated': top_rated,
        'recently_viewed': recently_viewed,
        'cart_count': cart_count,
        'wishlist_count': wishlist_count,
        'wishlist_products': wishlist_products,
        'services': services,
        'flash_sale_end_time': timezone.now() + timedelta(hours=24),
    }
    
    return render(request, 'store/home.html', context)


def add_to_recently_viewed(request, product_id):
    """Add product to recently viewed session"""
    recently_viewed = request.session.get('recently_viewed', [])
    
    if product_id in recently_viewed:
        recently_viewed.remove(product_id)
    recently_viewed.insert(0, product_id)
    
    request.session['recently_viewed'] = recently_viewed[:10]
    request.session.modified = True
    
    return True


# ==================== SHOP VIEWS ====================

def shop_view(request):
    """Main shop page with filtering and pagination"""
    products = Product.objects.filter(status="published").select_related('category', 'vendor')
    
    # Search functionality
    search_query = request.GET.get('q', '')
    if search_query:
        products = products.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(category__title__icontains=search_query)
        )
    
    # Category filter
    category_slug = request.GET.get('category')
    if category_slug:
        products = products.filter(category__slug=category_slug)
    
    # Price filter
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price:
        try:
            products = products.filter(price__gte=Decimal(min_price))
        except:
            pass
    if max_price:
        try:
            products = products.filter(price__lte=Decimal(max_price))
        except:
            pass
    
    # Sorting
    sort_by = request.GET.get('sort', '-date')
    valid_sort_fields = ['date', '-date', 'price', '-price', 'title', '-title', 'views', '-views']
    if sort_by in valid_sort_fields:
        products = products.order_by(sort_by)
    else:
        products = products.order_by('-date')
    
    # Pagination
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Categories for sidebar
    categories = Category.objects.filter(active=True)
    
    context = {
        'products': page_obj,
        'categories': categories,
        'search_query': search_query,
        'selected_category': category_slug,
        'min_price': min_price,
        'max_price': max_price,
        'sort_by': sort_by,
    }
    return render(request, 'store/shop.html', context)


def product_detail_view(request, slug):
    """Product detail page"""
    product = get_object_or_404(Product, slug=slug, status="published")
    
    # Increment view count
    product.views += 1
    product.save()
    
    # Add to recently viewed
    add_to_recently_viewed(request, product.id)
    
    # Get related products
    related_products = Product.objects.filter(
        category=product.category, 
        status="published"
    ).exclude(id=product.id)[:8]
    
    # Get product gallery, specifications, sizes, colors
    gallery = product.gallery()
    specifications = product.specification()
    sizes = product.size()
    colors = product.color()
    
    # Get reviews
    reviews = Review.objects.filter(product=product, active=True)
    
    # Check if user has purchased this product
    has_purchased = False
    if request.user.is_authenticated:
        has_purchased = CartOrderItem.objects.filter(
            order__buyer=request.user,
            product=product,
            order__payment_status='paid'
        ).exists()
    
    # Handle review submission
    if request.method == 'POST' and request.user.is_authenticated:
        rating = request.POST.get('rating')
        review_text = request.POST.get('review')
        
        if rating and review_text:
            # Check if user already reviewed
            existing_review = Review.objects.filter(user=request.user, product=product).first()
            if existing_review:
                messages.warning(request, 'You have already reviewed this product!')
            else:
                Review.objects.create(
                    user=request.user,
                    product=product,
                    review=review_text,
                    rating=int(rating),
                    active=True
                )
                messages.success(request, 'Thank you for your review!')
        else:
            messages.error(request, 'Please provide both rating and review.')
        
        return redirect('store:product_detail', slug=product.slug)
    
    # Get FAQs
    faqs = ProductFeq.objects.filter(product=product, active=True)
    
    # Check if product is in wishlist
    in_wishlist = False
    if request.user.is_authenticated:
        in_wishlist = Wshlist.objects.filter(user=request.user, product=product).exists()
    
    context = {
        'product': product,
        'gallery': gallery,
        'specifications': specifications,
        'sizes': sizes,
        'colors': colors,
        'reviews': reviews,
        'related_products': related_products,
        'faqs': faqs,
        'has_purchased': has_purchased,
        'in_wishlist': in_wishlist,
    }
    return render(request, 'store/product_detail.html', context)


# ==================== CART VIEWS ====================

def cart_view(request):
    """Shopping cart page"""
    cart_id = request.session.get('cart_id')
    cart_items = Cart.objects.filter(cart_id=cart_id) if cart_id else []
    
    # Calculate cart totals
    subtotal = sum(item.sub_total for item in cart_items)
    shipping = sum(item.shipping_amount for item in cart_items)
    tax = sum(item.tax_fee for item in cart_items)
    service_fee = sum(item.service_fee for item in cart_items)
    total = subtotal + shipping + tax + service_fee
    
    context = {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'shipping': shipping,
        'tax': tax,
        'service_fee': service_fee,
        'total': total,
    }
    return render(request, 'store/cart.html', context)


@login_required
def add_to_cart(request):
    """Add product to cart"""
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        qty = int(request.POST.get('qty', 1))
        size = request.POST.get('size', '')
        color = request.POST.get('color', '')
        
        try:
            product = get_object_or_404(Product, id=product_id)
        except:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': 'Product not found'})
            messages.error(request, 'Product not found')
            return redirect('store:shop')
        
        # Get or create cart session
        cart_id = request.session.get('cart_id')
        if not cart_id:
            cart_id = str(uuid.uuid4())
            request.session['cart_id'] = cart_id
        
        # Calculate prices
        price = product.price
        sub_total = price * qty
        
        # Get tax rate (you can implement dynamic tax based on country)
        tax_rate = Decimal('0.10')  # 10% tax
        tax_fee = sub_total * tax_rate
        
        service_fee = Decimal('5.00')  # Fixed service fee
        shipping_amount = product.shipping_amount
        
        total = sub_total + tax_fee + service_fee + shipping_amount
        
        # Check if item already in cart
        cart_item, created = Cart.objects.get_or_create(
            cart_id=cart_id,
            product=product,
            size=size,
            color=color,
            defaults={
                'user': request.user if request.user.is_authenticated else None,
                'qty': qty,
                'price': price,
                'sub_total': sub_total,
                'shipping_amount': shipping_amount,
                'service_fee': service_fee,
                'tax_fee': tax_fee,
                'total': total,
            }
        )
        
        if not created:
            cart_item.qty += qty
            cart_item.sub_total = cart_item.price * cart_item.qty
            cart_item.total = cart_item.sub_total + cart_item.tax_fee + cart_item.service_fee + cart_item.shipping_amount
            cart_item.save()
        
        messages.success(request, f'{product.title} added to cart!')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'Added to cart'})
        
        return redirect('store:cart')
    
    return redirect('store:shop')


@login_required
def update_cart(request):
    """Update cart item quantity"""
    if request.method == 'POST':
        item_id = request.POST.get('item_id')
        qty = int(request.POST.get('qty'))
        
        try:
            cart_item = get_object_or_404(Cart, id=item_id)
            cart_item.qty = qty
            cart_item.sub_total = cart_item.price * qty
            cart_item.total = cart_item.sub_total + cart_item.tax_fee + cart_item.service_fee + cart_item.shipping_amount
            cart_item.save()
            
            # Recalculate totals
            cart_items = Cart.objects.filter(cart_id=cart_item.cart_id)
            subtotal = sum(item.sub_total for item in cart_items)
            shipping = sum(item.shipping_amount for item in cart_items)
            tax = sum(item.tax_fee for item in cart_items)
            service_fee = sum(item.service_fee for item in cart_items)
            total = subtotal + shipping + tax + service_fee
            
            return JsonResponse({
                'success': True,
                'subtotal': float(subtotal),
                'shipping': float(shipping),
                'tax': float(tax),
                'service_fee': float(service_fee),
                'total': float(total),
                'item_total': float(cart_item.sub_total)
            })
        except:
            return JsonResponse({'success': False, 'message': 'Error updating cart'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})


@login_required
def remove_from_cart(request, item_id):
    """Remove item from cart"""
    cart_item = get_object_or_404(Cart, id=item_id)
    cart_item.delete()
    messages.success(request, 'Item removed from cart')
    return redirect('store:cart')


# ==================== CHECKOUT VIEWS ====================

@login_required
def checkout_view(request):
    """Checkout page"""
    cart_id = request.session.get('cart_id')
    cart_items = Cart.objects.filter(cart_id=cart_id) if cart_id else []
    
    if not cart_items:
        messages.warning(request, 'Your cart is empty')
        return redirect('store:shop')
    
    # Get user profile for pre-filling forms
    try:
        profile = request.user.profile
    except:
        profile = None
    
    if request.method == 'POST':
        # Collect shipping information
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        mobile = request.POST.get('mobile')
        address = request.POST.get('address')
        city = request.POST.get('city')
        state = request.POST.get('state')
        country = request.POST.get('country')
        
        # Calculate totals
        subtotal = sum(item.sub_total for item in cart_items)
        shipping = sum(item.shipping_amount for item in cart_items)
        tax = sum(item.tax_fee for item in cart_items)
        service_fee = sum(item.service_fee for item in cart_items)
        total = subtotal + shipping + tax + service_fee
        
        # Create order
        with transaction.atomic():
            order = CartOrder.objects.create(
                buyer=request.user,
                sub_total=subtotal,
                shipping_amount=shipping,
                tax_fee=tax,
                service_fee=service_fee,
                total=total,
                full_name=full_name,
                email=email,
                mobile=mobile,
                address=address,
                city=city,
                state=state,
                country=country,
                payment_status='pending',
                order_status='Pending'
            )
            
            # Add vendors to order
            vendors = set()
            for item in cart_items:
                vendors.add(item.product.vendor)
            order.vendor.add(*vendors)
            
            # Create order items
            for item in cart_items:
                order_item = CartOrderItem.objects.create(
                    order=order,
                    product=item.product,
                    qty=item.qty,
                    price=item.price,
                    sub_total=item.sub_total,
                    shipping_amount=item.shipping_amount,
                    service_fee=item.service_fee,
                    tax_fee=item.tax_fee,
                    total=item.total,
                    size=item.size,
                    color=item.color,
                    vendor=item.product.vendor
                )
                
                # Update stock
                product = item.product
                product.stock_qty -= item.qty
                if product.stock_qty <= 0:
                    product.in_stock = False
                product.save()
            
            # Clear cart
            cart_items.delete()
            if 'cart_id' in request.session:
                del request.session['cart_id']
            
            # Create notification for vendors
            for vendor in vendors:
                Notification.objects.create(
                    vendor=vendor,
                    order=order,
                )
            
            # Store order ID in session for payment
            request.session['order_id'] = str(order.oid)
            
            messages.success(request, 'Order placed successfully! Proceed to payment.')
            return redirect('store:payment')
    
    # Calculate totals for display
    subtotal = sum(item.sub_total for item in cart_items)
    shipping = sum(item.shipping_amount for item in cart_items)
    tax = sum(item.tax_fee for item in cart_items)
    service_fee = sum(item.service_fee for item in cart_items)
    total = subtotal + shipping + tax + service_fee
    
    context = {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'shipping': shipping,
        'tax': tax,
        'service_fee': service_fee,
        'total': total,
        'profile': profile,
    }
    return render(request, 'store/checkout.html', context)


@login_required
def payment_view(request):
    """Payment page"""
    order_id = request.session.get('order_id')
    if not order_id:
        messages.warning(request, 'No active order found')
        return redirect('store:cart')
    
    order = get_object_or_404(CartOrder, oid=order_id, buyer=request.user)
    
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        
        if payment_method == 'cash_on_delivery':
            order.payment_status = 'pending'
            order.order_status = 'Pending'
            order.save()
            messages.success(request, 'Order placed successfully! You will pay upon delivery.')
            return redirect('store:order_confirmation', order_oid=order.oid)
        
        elif payment_method == 'stripe':
            # Integrate Stripe here
            # For now, simulate success
            order.payment_status = 'paid'
            order.order_status = 'Processing'
            order.save()
            messages.success(request, 'Payment successful! Your order is being processed.')
            return redirect('store:order_confirmation', order_oid=order.oid)
        else:
            messages.error(request, 'Invalid payment method')
    
    context = {
        'order': order,
    }
    return render(request, 'store/payment.html', context)


@login_required
def order_confirmation_view(request, order_oid):
    """Order confirmation page"""
    order = get_object_or_404(CartOrder, oid=order_oid, buyer=request.user)
    order_items = order.orderitem()
    
    context = {
        'order': order,
        'order_items': order_items,
    }
    return render(request, 'store/order_confirmation.html', context)


# ==================== USER DASHBOARD VIEWS ====================

@login_required
def dashboard(request):
    """User dashboard with charts and statistics"""
    
    user = request.user
    
    # Get date range for filtering (last 12 months for chart)
    today = timezone.now().date()
    last_12_months = today - timedelta(days=365)
    last_30_days = today - timedelta(days=30)
    
    # ========== BASIC STATISTICS ==========
    
    # Order Statistics
    total_orders = CartOrder.objects.filter(buyer=user).count()
    completed_orders = CartOrder.objects.filter(
        buyer=user, 
        order_status='Fullfilled'
    ).count()
    pending_orders = CartOrder.objects.filter(
        buyer=user, 
        payment_status='pending'
    ).count()
    cancelled_orders = CartOrder.objects.filter(
        buyer=user, 
        order_status='Cancelled'
    ).count()
    
    # Financial Statistics
    total_spent = CartOrder.objects.filter(
        buyer=user, 
        payment_status='paid'
    ).aggregate(total=Sum('total'))['total'] or Decimal('0.00')
    
    total_saved = CartOrder.objects.filter(
        buyer=user
    ).aggregate(saved=Sum('saved'))['saved'] or Decimal('0.00')
    
    # Product Statistics
    wishlist_count = Wshlist.objects.filter(user=user).count()
    review_count = Review.objects.filter(user=user).count()
    
    # Notification Statistics
    unread_notifications = Notification.objects.filter(
        user=user, 
        seen=False
    ).count()
    total_notifications = Notification.objects.filter(user=user).count()
    
    # ========== MONTHLY ORDER CHART DATA ==========
    monthly_orders = CartOrder.objects.filter(
        buyer=user,
        date__date__gte=last_12_months
    ).annotate(
        month=TruncMonth('date')
    ).values('month').annotate(
        order_count=Count('id'),
        total_amount=Sum('total')
    ).order_by('month')
    
    # Prepare chart data
    months = []
    order_counts = []
    order_amounts = []
    
    # Get last 12 months
    for i in range(11, -1, -1):
        month_date = today.replace(day=1) - timedelta(days=30*i)
        month_name = month_date.strftime('%b %Y')
        months.append(month_name)
        
        # Find data for this month
        month_data = next(
            (item for item in monthly_orders if item['month'].date().year == month_date.year 
             and item['month'].date().month == month_date.month),
            None
        )
        
        if month_data:
            order_counts.append(month_data['order_count'])
            order_amounts.append(float(month_data['total_amount']))
        else:
            order_counts.append(0)
            order_amounts.append(0)
    
    # ========== RECENT ORDERS ==========
    recent_orders = CartOrder.objects.filter(buyer=user).order_by('-date')[:5]
    
    # ========== ORDER STATUS DISTRIBUTION (PIE CHART) ==========
    status_data = CartOrder.objects.filter(buyer=user).values('order_status').annotate(
        count=Count('id')
    )
    
    status_labels = []
    status_counts = []
    status_colors = {
        'Pending': '#ffc107',
        'Fullfilled': '#28a745',
        'Cancelled': '#dc3545'
    }
    
    for item in status_data:
        status_labels.append(item['order_status'])
        status_counts.append(item['count'])
    
    # ========== TOP PRODUCTS PURCHASED ==========
    top_products = CartOrderItem.objects.filter(
        order__buyer=user
    ).values(
        'product__title', 
        'product__image'
    ).annotate(
        total_quantity=Sum('qty'),
        total_spent=Sum('total')
    ).order_by('-total_quantity')[:5]
    
    # ========== RECENT REVIEWS ==========
    recent_reviews = Review.objects.filter(user=user).order_by('-date')[:3]
    
    # ========== RECENT NOTIFICATIONS ==========
    recent_notifications = Notification.objects.filter(user=user).order_by('-date')[:5]
    
    # ========== WEEKLY ACTIVITY (LAST 7 DAYS) ==========
    weekly_activity = CartOrder.objects.filter(
        buyer=user,
        date__date__gte=last_30_days
    ).annotate(
        day=TruncDate('date')
    ).values('day').annotate(
        order_count=Count('id')
    ).order_by('day')
    
    last_7_days_labels = []
    last_7_days_data = []
    
    for i in range(6, -1, -1):
        day_date = today - timedelta(days=i)
        day_label = day_date.strftime('%a, %b %d')
        last_7_days_labels.append(day_label)
        
        day_data = next(
            (item for item in weekly_activity if item['day'] == day_date),
            None
        )
        last_7_days_data.append(day_data['order_count'] if day_data else 0)
    
    # ========== RECENTLY VIEWED PRODUCTS (if you have this feature) ==========
    # You can implement a recently viewed products model if needed
    recently_viewed = []  # Placeholder for recently viewed products
    
    # ========== FAVORITE CATEGORIES ==========
    favorite_categories = CartOrderItem.objects.filter(
        order__buyer=user
    ).values(
        'product__category__title'
    ).annotate(
        purchase_count=Count('id')
    ).order_by('-purchase_count')[:5]
    
    context = {
        # Basic stats
        'total_orders': total_orders,
        'completed_orders': completed_orders,
        'pending_orders': pending_orders,
        'cancelled_orders': cancelled_orders,
        'total_spent': total_spent,
        'total_saved': total_saved,
        'wishlist_count': wishlist_count,
        'review_count': review_count,
        'unread_notifications': unread_notifications,
        'total_notifications': total_notifications,
        
        # Chart data (as JSON)
        'months_json': json.dumps(months),
        'order_counts_json': json.dumps(order_counts),
        'order_amounts_json': json.dumps(order_amounts),
        'status_labels_json': json.dumps(status_labels),
        'status_counts_json': json.dumps(status_counts),
        'last_7_days_labels_json': json.dumps(last_7_days_labels),
        'last_7_days_data_json': json.dumps(last_7_days_data),
        
        # Lists for display
        'recent_orders': recent_orders,
        'top_products': top_products,
        'recent_reviews': recent_reviews,
        'recent_notifications': recent_notifications,
        'favorite_categories': favorite_categories,
        'recently_viewed': recently_viewed,
        
        # Status colors helper
        'status_colors': status_colors,
    }
    
    return render(request, 'store/user_dashboard.html', context)


@login_required
def user_orders_view(request):
    """User orders list"""
    orders = CartOrder.objects.filter(buyer=request.user).order_by('-date')
    
    paginator = Paginator(orders, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'orders': page_obj,
    }
    return render(request, 'store/user_orders.html', context)


@login_required
def user_order_detail_view(request, order_oid):
    """User order details"""
    order = get_object_or_404(CartOrder, oid=order_oid, buyer=request.user)
    order_items = order.orderitem()
    
    context = {
        'order': order,
        'order_items': order_items,
    }
    return render(request, 'store/user_order_detail.html', context)


@login_required
def user_wishlist_view(request):
    """User wishlist"""
    wishlist_items = Wshlist.objects.filter(user=request.user).select_related('product')
    
    context = {
        'wishlist_items': wishlist_items,
    }
    return render(request, 'store/user_wishlist.html', context)


@login_required
def add_to_wishlist(request, product_id):
    """Add product to wishlist"""
    product = get_object_or_404(Product, id=product_id)
    
    wishlist_item, created = Wshlist.objects.get_or_create(
        user=request.user,
        product=product
    )
    
    if created:
        messages.success(request, f'{product.title} added to wishlist')
    else:
        messages.info(request, f'{product.title} is already in your wishlist')
    
    return redirect(request.META.get('HTTP_REFERER', 'store:shop'))


@login_required
def remove_from_wishlist(request, product_id):
    """Remove product from wishlist"""
    product = get_object_or_404(Product, id=product_id)
    Wshlist.objects.filter(user=request.user, product=product).delete()
    messages.success(request, f'{product.title} removed from wishlist')
    return redirect('store:user_wishlist')


@login_required
def user_reviews_view(request):
    """User reviews list"""
    reviews = Review.objects.filter(user=request.user).select_related('product').order_by('-date')
    
    context = {
        'reviews': reviews,
    }
    return render(request, 'store/user_reviews.html', context)


@login_required
def user_notifications_view(request):
    """User notifications"""
    notifications = Notification.objects.filter(user=request.user).order_by('-date')
    
    # Mark as seen
    notifications.update(seen=True)
    
    context = {
        'notifications': notifications,
    }
    return render(request, 'store/user_notifications.html', context)


# ==================== FAQ VIEWS ====================

@login_required
def product_faq_view(request, product_id):
    """Submit product question"""
    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id)
        question = request.POST.get('question')
        
        if question:
            ProductFeq.objects.create(
                user=request.user,
                product=product,
                email=request.user.email,
                question=question
            )
            messages.success(request, 'Your question has been submitted. We\'ll answer soon.')
        else:
            messages.error(request, 'Please enter a question.')
    
    return redirect('store:product_detail', slug=product.slug)


# ==================== SEARCH VIEW ====================

def search_view(request):
    """Advanced search page with filtering"""
    query = request.GET.get('q', '')
    products = Product.objects.filter(status="published")
    
    if query:
        products = products.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(category__title__icontains=query) |
            Q(vendor__name__icontains=query)
        ).distinct()
    
    # Category filter
    category_ids = request.GET.getlist('category')
    if category_ids:
        products = products.filter(category__id__in=category_ids)
    
    # Price filter
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price:
        try:
            products = products.filter(price__gte=Decimal(min_price))
        except:
            pass
    if max_price:
        try:
            products = products.filter(price__lte=Decimal(max_price))
        except:
            pass
    
    # Rating filter
    rating = request.GET.get('rating')
    if rating:
        try:
            rating_int = int(rating)
            products = products.filter(rating__gte=rating_int)
        except:
            pass
    
    # Stock filter
    in_stock = request.GET.get('in_stock')
    if in_stock == 'true':
        products = products.filter(in_stock=True, stock_qty__gt=0)
    
    # Sorting
    sort_by = request.GET.get('sort', '-date')
    valid_sort_fields = ['date', '-date', 'price', '-price', 'title', '-title', 'views', '-views', 'rating', '-rating']
    if sort_by in valid_sort_fields:
        products = products.order_by(sort_by)
    else:
        products = products.order_by('-date')
    
    # Pagination
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get categories with product counts for sidebar
    categories = Category.objects.filter(active=True)
    for category in categories:
        category.product_count = Product.objects.filter(
            category=category, 
            status="published"
        ).count()
    
    selected_categories = request.GET.getlist('category')
    
    context = {
        'query': query,
        'products': page_obj,
        'product_count': products.count(),
        'categories': categories,
        'selected_categories': selected_categories,
        'ratings': [1, 2, 3, 4, 5],
    }
    return render(request, 'store/search.html', context)


# ==================== COUPON VIEWS ====================

@login_required
def apply_coupon(request):
    """Apply coupon to order"""
    if request.method == 'POST':
        coupon_code = request.POST.get('coupon_code')
        order_id = request.session.get('order_id')
        
        if not order_id:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': 'No active order'})
            messages.error(request, 'No active order')
            return redirect('store:cart')
        
        try:
            coupon = Coupon.objects.get(code=coupon_code, active=True)
            order = CartOrder.objects.get(oid=order_id, buyer=request.user)
            
            # Calculate discount
            discount_amount = (order.total * coupon.discount) / 100
            new_total = order.total - discount_amount
            
            order.saved = discount_amount
            order.total = new_total
            order.save()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'discount': float(discount_amount),
                    'new_total': float(new_total)
                })
            messages.success(request, f'Coupon applied! You saved ${discount_amount}')
            
        except Coupon.DoesNotExist:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': 'Invalid coupon code'})
            messages.error(request, 'Invalid coupon code')
        except CartOrder.DoesNotExist:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': 'Order not found'})
            messages.error(request, 'Order not found')
    
    return redirect('store:checkout')


# ==================== CATEGORY VIEW ====================

def category_view(request, slug):
    """Category page"""
    category = get_object_or_404(Category, slug=slug, active=True)
    products = Product.objects.filter(category=category, status="published")
    
    # Pagination
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'category': category,
        'products': page_obj,
    }
    return render(request, 'store/category.html', context)

def newsletter_subscribe(request):
    """Handle newsletter subscription"""
    if request.method == 'POST':
        email = request.POST.get('email')
        if email:
            # Check if email already exists
            if not Newsletter.objects.filter(email=email).exists():
                Newsletter.objects.create(
                    email=email,
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                messages.success(request, 'Successfully subscribed to newsletter!')
            else:
                messages.info(request, 'You are already subscribed to our newsletter.')
        else:
            messages.error(request, 'Please provide a valid email address.')
    
    # Redirect back to the page user came from
    return redirect(request.META.get('HTTP_REFERER', 'store:home'))