from decimal import Decimal
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from .models import User, Profile
from .forms import UserRegistrationForm, UserLoginForm, UserUpdateForm, ProfileUpdateForm, PasswordResetForm

# Registration View (without OTP)
def register_view(request):
    if request.user.is_authenticated:
        return redirect('store:user_dashboard')
    
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save(commit=False)
                user.set_password(form.cleaned_data['password1'])
                user.is_active = True
                user.save()
                
                # লগইন করে দিন
                login(request, user)
                
                messages.success(request, f'Welcome {user.full_name or user.username}! Registration successful.')
                return redirect('store:user_dashboard')
            except Exception as e:
                messages.error(request, f'Registration error: {str(e)}')
        else:
            # ফর্মের ত্রুটিগুলো দেখান
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'accounts/register.html', {'form': form})

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
                    next_url = request.GET.get('next', 'store:user_dashboard')
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
    return redirect('store:home')

# Profile View
@login_required
def profile_view(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
    
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
                # TODO: ইমেইল সেন্ডিং লজিক যোগ করুন
                messages.success(request, 'Password reset link sent to your email!')
                return redirect('accounts:login')
            except User.DoesNotExist:
                messages.error(request, 'No user found with this email address.')
    else:
        form = PasswordResetForm()
    
    return render(request, 'accounts/password_reset_request.html', {'form': form})