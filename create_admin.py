import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nextlook.settings')
django.setup()

from userauths.models import User

email = "hasibsk1606@gmail.com"
password = "adminpassword123"

if not User.objects.filter(email=email).exists():
    user = User.objects.create_superuser(
        username="hasibsk",
        email=email,
        password=password
    )
    user.is_staff = True
    user.is_superuser = True
    user.save()
    print("Superuser created successfully!")
else:
    user = User.objects.get(email=email)
    user.set_password(password)
    user.is_staff = True
    user.is_superuser = True
    user.save()
    print("Superuser updated successfully!")