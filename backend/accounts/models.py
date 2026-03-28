"""
Custom User model and per-user token budget for authentication.
"""
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.db import models
from django.db.models import F


class User(AbstractUser):
    """Custom user model extending Django's AbstractUser."""
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email


class UserTokenBudget(models.Model):
    """Tracks per-user OpenAI token consumption against a configurable limit."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='token_budget')
    # Limit is set from settings.DEFAULT_TOKEN_LIMIT at creation time so it can
    # be overridden per-user later without changing the global default.
    token_limit = models.PositiveIntegerField(default=0)
    tokens_used = models.PositiveIntegerField(default=0)
    period_start = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "User Token Budget"

    def __str__(self):
        return f"{self.user.email}: {self.tokens_used}/{self.token_limit}"

    @property
    def tokens_remaining(self) -> int:
        return max(0, self.token_limit - self.tokens_used)

    @property
    def is_over_limit(self) -> bool:
        return self.tokens_used >= self.token_limit

    def add_tokens(self, count: int) -> None:
        """Atomically increment tokens_used."""
        UserTokenBudget.objects.filter(pk=self.pk).update(tokens_used=F('tokens_used') + count)
