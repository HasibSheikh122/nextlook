from decimal import Decimal
from django.db.models.functions import TruncMonth, TruncDate
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from .models import User, Profile
import json
from store.models import CartOrder, CartOrderItem, Review, Wshlist, Notification
from django.db.models import Count, Sum
from .forms import (
    UserRegistrationForm, UserLoginForm, 
    UserUpdateForm, ProfileUpdateForm, 
    PasswordResetForm, OTPVerificationForm
)
import random
from django.utils import timezone
from datetime import timedelta

# Helper function to send OTP
def send_otp_email(user, otp):
    subject = 'Your OTP for Verification'
    message = f'Hello {user.full_name or user.email},\n\nYour OTP for verification is: {otp}\n\nThis OTP is valid for 10 minutes.\n\nThank you for using our service!'
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [user.email]
    
    try:
        send_mail(subject, message, from_email, recipient_list)
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

# Registration View
def register_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')
    
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            
            # Generate OTP
            otp = str(random.randint(100000, 999999))
            user.otp = otp
            user.is_active = False  # User inactive until OTP verification
            user.save()
            
            # Send OTP email
            if send_otp_email(user, otp):
                request.session['verification_email'] = user.email
                messages.success(request, 'Registration successful! Please verify your email with the OTP sent.')
                return redirect('verify_otp')
            else:
                user.delete()
                messages.error(request, 'Failed to send OTP. Please try again.')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'accounts/register.html', {'form': form})

# OTP Verification View
def verify_otp_view(request):
    email = request.session.get('verification_email')
    if not email:
        messages.error(request, 'Session expired. Please register again.')
        return redirect('register')
    
    user = User.objects.get(email=email)
    
    if request.method == 'POST':
        form = OTPVerificationForm(request.POST)
        if form.is_valid():
            entered_otp = form.cleaned_data['otp']
            if user.otp == entered_otp:
                user.is_active = True
                user.otp = None
                user.save()
                login(request, user)
                messages.success(request, 'Email verified successfully! Welcome aboard!')
                return redirect('dashboard')
            else:
                messages.error(request, 'Invalid OTP. Please try again.')
    else:
        form = OTPVerificationForm()
    
    return render(request, 'accounts/verify_otp.html', {'form': form, 'email': email})

# Resend OTP View
def resend_otp_view(request):
    email = request.session.get('verification_email')
    if not email:
        return redirect('register')
    
    user = User.objects.get(email=email)
    new_otp = str(random.randint(100000, 999999))
    user.otp = new_otp
    user.save()
    
    if send_otp_email(user, new_otp):
        messages.success(request, 'New OTP sent to your email!')
    else:
        messages.error(request, 'Failed to send OTP. Please try again.')
    
    return redirect('verify_otp')

# Login View
def login_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')
    
    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user = authenticate(request, email=email, password=password)
            
            if user is not None:
                if user.is_active:
                    login(request, user)
                    messages.success(request, f'Welcome back, {user.full_name or user.email}!')
                    next_url = request.GET.get('next', 'accounts:user_dashboard')
                    return redirect(next_url)
                else:
                    messages.warning(request, 'Please verify your email first.')
            else:
                messages.error(request, 'Invalid email or password.')
    else:
        form = UserLoginForm()
    
    return render(request, 'accounts/login.html', {'form': form})

# Logout View
@login_required
def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('accounts:login')

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

# Profile View
@login_required
def profile_view(request):
    profile = request.user.profile
    
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('accounts:profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=profile)
    
    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'profile': profile,
    }
    return render(request, 'accounts/profile.html', context)

# Password Reset Request View
def password_reset_request_view(request):
    if request.method == 'POST':
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(email=email)
                otp = str(random.randint(100000, 999999))
                user.otp = otp
                user.save()
                
                if send_otp_email(user, otp):
                    request.session['reset_email'] = email
                    messages.success(request, 'OTP sent to your email for password reset.')
                    return redirect('password_reset_verify')
                else:
                    messages.error(request, 'Failed to send OTP. Please try again.')
            except User.DoesNotExist:
                messages.error(request, 'No user found with this email address.')
    else:
        form = PasswordResetForm()
    
    return render(request, 'accounts/password_reset_request.html', {'form': form})

# Password Reset Verify OTP View
def password_reset_verify_view(request):
    email = request.session.get('reset_email')
    if not email:
        return redirect('password_reset_request')
    
    if request.method == 'POST':
        form = OTPVerificationForm(request.POST)
        if form.is_valid():
            otp = form.cleaned_data['otp']
            try:
                user = User.objects.get(email=email, otp=otp)
                request.session['reset_verified'] = True
                return redirect('password_reset_confirm')
            except User.DoesNotExist:
                messages.error(request, 'Invalid OTP. Please try again.')
    else:
        form = OTPVerificationForm()
    
    return render(request, 'accounts/password_reset_verify.html', {'form': form, 'email': email})

# Password Reset Confirm View
def password_reset_confirm_view(request):
    if not request.session.get('reset_verified'):
        return redirect('password_reset_request')
    
    email = request.session.get('reset_email')
    user = User.objects.get(email=email)
    
    if request.method == 'POST':
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        
        if password == confirm_password and len(password) >= 8:
            user.set_password(password)
            user.otp = None
            user.save()
            del request.session['reset_email']
            del request.session['reset_verified']
            messages.success(request, 'Password reset successful! Please login with your new password.')
            return redirect('login')
        else:
            messages.error(request, 'Passwords do not match or are too short.')
    
    return render(request, 'accounts/password_reset_confirm.html')