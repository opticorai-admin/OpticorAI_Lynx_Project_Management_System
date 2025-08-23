# Create user (as manager)
from django.contrib.auth import get_user_model

U = get_user_model()
u, created = U.objects.get_or_create(
    username="admin_user",
    defaults={"email": "user@company.com"}
)
u.first_name = "Admin"
u.last_name = "As"
u.user_type = "Admin"
u.user_type = "admin"
u.is_superuser = False
u.is_staff = True
u.set_password("Password12@/")
u.save()

print(("Created" if created else "Updated") + ":", u.username, u.user_type, "is_staff=", u.is_staff, "is_superuser=", u.is_superuser)
