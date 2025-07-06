from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

UserModel = get_user_model()

class EmailBackend(ModelBackend):
    """Custom authentication backend that allows users to login with email or username."""
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
        if username is None or password is None:
            return
        
        # Normalize the username/email
        username = username.strip()
        if '@' in username:
            username = username.lower()
        
        try:
            user = UserModel.objects.get(
                Q(username__iexact=username) | Q(email__iexact=username)
            )
        except UserModel.DoesNotExist:
            UserModel().set_password(password)
        except UserModel.MultipleObjectsReturned:
            try:
                user = UserModel.objects.get(username__iexact=username)
            except UserModel.DoesNotExist:
                try:
                    user = UserModel.objects.get(email__iexact=username)
                except UserModel.DoesNotExist:
                    return None
        else:
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
