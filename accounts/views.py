from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, UpdateView

from .forms import (
    CustomPasswordChangeForm,
    CustomUserCreationForm,
    CustomUserLoginForm,
    CustomUserUpdateForm,
)
from .models import CustomUser

# Register a new user
class RegisterView(CreateView):
    model = CustomUser
    form_class = CustomUserCreationForm
    template_name = "accounts/register.html"
    success_url = reverse_lazy("accounts:login")

# user login page
class CustomLoginView(LoginView):
    form_class = CustomUserLoginForm
    template_name = "accounts/login.html"

# display the logged-in user's profile
class ProfileView(LoginRequiredMixin, DetailView):
    model = CustomUser
    template_name = "accounts/profile.html"
    context_object_name = "user_profile"

    def get_object(self):
        return self.request.user

# Update profile information
class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = CustomUser
    form_class = CustomUserUpdateForm
    template_name = "accounts/edit_profile.html"
    success_url = reverse_lazy("accounts:profile")

    def get_object(self):
        return self.request.user

# Change account password
class CustomPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    form_class = CustomPasswordChangeForm
    template_name = "accounts/change_password.html"
    success_url = reverse_lazy("accounts:profile")


# Delete the current user's account
class AccountDeleteView(LoginRequiredMixin, DeleteView):
    model = CustomUser
    template_name = "accounts/delete_account.html"
    success_url = reverse_lazy("accounts:login")

    def get_object(self):
        return self.request.user

    # logout user before deleting to clean session from memory
    def form_valid(self, form):
        user = self.get_object()
        logout(self.request)
        user.delete()
        return redirect(self.success_url)