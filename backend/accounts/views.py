from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .forms import LoginForm, StaffCreationForm, StaffEditForm, RegistrationForm
from .models import User
from .role_access import dashboard_url_for_user
from .audit import log_audit


def login_view(request):
    if request.user.is_authenticated:
        return redirect(dashboard_url_for_user(request.user))
    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user)
        log_audit(request, 'login', f'User {user.username} logged in', status='success')
        messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
        next_url = request.GET.get('next', '')
        return redirect(next_url or dashboard_url_for_user(user))
    elif request.method == 'POST':
        username = request.POST.get('username', '')
        log_audit(request, 'failed_login', f'Failed login attempt for username: {username}', status='failed')
    return render(request, 'accounts/login.html', {'form': form})


def register_view(request):
    if request.user.is_authenticated:
        return redirect(dashboard_url_for_user(request.user))
    form = RegistrationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        log_audit(request, 'register', f'New user {user.username} registered', status='success')
        messages.success(request, 'Account created successfully! You can now login.')
        return redirect('login')
    return render(request, 'accounts/register.html', {'form': form})


def logout_view(request):
    username = request.user.username if request.user.is_authenticated else 'Unknown'
    logout(request)
    log_audit(request, 'logout', f'User {username} logged out', status='success')
    messages.info(request, 'You have been signed out.')
    return redirect('login')


@login_required
def staff_list(request):
    if not request.user.is_admin:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    query = request.GET.get('q', '')
    role = request.GET.get('role', '')

    staff = User.objects.all().order_by('first_name')

    if query:
        staff = staff.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(username__icontains=query)
        )

    if role:
        staff = staff.filter(role=role)

    context = {
        'staff': staff,
        'query': query,
        'role_filter': role,
        'role_choices': User.ROLE_CHOICES,

        'admin_count': User.objects.filter(
            role='admin',
            is_active=True
        ).count(),

        'doctor_count': User.objects.filter(
            role='doctor',
            is_active=True
        ).count(),

        'nurse_count': User.objects.filter(
            role='nurse',
            is_active=True
        ).count(),

        'care_assistant_count': User.objects.filter(
            role='care_assistant',
            is_active=True
        ).count(),

        'family_count': User.objects.filter(
            role='family',
            is_active=True
        ).count(),
    }

    return render(
        request,
        'accounts/staff_list.html',
        context
    )


@login_required
def staff_add(request):
    if not request.user.is_admin:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    form = StaffCreationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        messages.success(request, f'Staff account for {user.get_full_name()} created.')
        return redirect('staff_list')
    return render(request, 'accounts/staff_form.html', {'form': form, 'action': 'Add'})


@login_required
def staff_edit(request, pk):
    if not request.user.is_admin:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    staff_member = get_object_or_404(User, pk=pk)
    form = StaffEditForm(request.POST or None, instance=staff_member)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Staff account updated.')
        return redirect('staff_list')
    return render(request, 'accounts/staff_form.html', {'form': form, 'action': 'Edit', 'staff_member': staff_member})


@login_required
def profile_view(request):
    user = request.user

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        job_title = request.POST.get('job_title', '').strip()
        profile_image = request.FILES.get('profile_image')

        # Validate email
        if not email:
            messages.error(request, 'Email is required.')
            return render(request, 'accounts/profile.html', {'user': user})

        # Check if email is unique (and not the same as current)
        if User.objects.filter(email=email).exclude(pk=user.pk).exists():
            messages.error(request, 'This email is already in use.')
            return render(request, 'accounts/profile.html', {'user': user})

        # Update user
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.phone_number = phone
        user.job_title = job_title

        if profile_image:
            user.profile_image = profile_image

        user.save()
        messages.success(request, 'Your profile has been updated successfully!')
        return render(request, 'accounts/profile.html', {'user': user})

    return render(request, 'accounts/profile.html', {'user': user})


@login_required
def change_password_view(request):
    user = request.user

    if request.method == 'POST':
        old_password = request.POST.get('old_password', '').strip()
        new_password = request.POST.get('new_password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()

        # Validate old password
        if not user.check_password(old_password):
            messages.error(request, 'Your current password is incorrect.')
            return render(request, 'accounts/change_password.html')

        # Validate new password
        if len(new_password) < 8:
            messages.error(request, 'New password must be at least 8 characters long.')
            return render(request, 'accounts/change_password.html')

        # Check passwords match
        if new_password != confirm_password:
            messages.error(request, 'New passwords do not match.')
            return render(request, 'accounts/change_password.html')

        # Check password complexity
        import re
        has_upper = re.search(r'[A-Z]', new_password)
        has_lower = re.search(r'[a-z]', new_password)
        has_number = re.search(r'[0-9]', new_password)
        has_special = re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]', new_password)

        if not (has_upper and has_lower and has_number and has_special):
            messages.error(request, 'Password must contain uppercase, lowercase, number, and special character.')
            return render(request, 'accounts/change_password.html')

        # Change password
        user.set_password(new_password)
        user.save()

        messages.success(request, 'Your password has been changed successfully! Please login again.')
        return redirect('login')

    return render(request, 'accounts/change_password.html')
