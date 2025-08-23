# Update user (manager to admin)
from django.contrib.auth import get_user_model

U = get_user_model()

# base attributes
attrs = dict(
    email="user@company.com",
    first_name="Admin",
    last_name="As",
    designation="Admin",
    user_type="admin",  # <-- must be the *value* from USER_TYPE_CHOICES
)

# ensure the required USERNAME_FIELD is present
if U.USERNAME_FIELD == "username":
    identifier = {"username": "admin_user"}
else:
    # if you've switched to email auth
    identifier = {U.USERNAME_FIELD: attrs["email"]}

# create or update without duplicate errors
u, created = U.objects.get_or_create(**identifier, defaults=attrs)

# if we found an existing user, update any changed fields
if not created:
    for k, v in attrs.items():
        setattr(u, k, v)

# set/refresh password as needed (only on first creation here)
if created:
    u.set_password("Password12@/")

# not a Django superuser; staff = can log into /admin
u.is_superuser = False
u.is_staff = True
u.save()

print(("Created" if created else "Updated") + ":",
      getattr(u, U.USERNAME_FIELD), u.email, u.user_type,
      "is_staff=", u.is_staff, "is_superuser=", u.is_superuser)
