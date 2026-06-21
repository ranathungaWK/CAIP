from django.db import models
from django.conf import settings

class GithubInstallation(models.Model):
    installation_id = models.CharField(max_length=255, unique=True)
    account_name = models.CharField(max_length=255, help_text="GitHub username or organization name")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='github_installations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.account_name} ({self.installation_id})"
