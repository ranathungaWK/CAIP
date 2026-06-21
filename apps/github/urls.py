from django.urls import path
from .views import GithubInstallCallbackView, GithubRepositoriesView, GithubBranchesView

urlpatterns = [
    path('install/callback/', GithubInstallCallbackView.as_view(), name='github-install-callback'),
    path('repositories/', GithubRepositoriesView.as_view(), name='github-repositories'),
    path('branches/', GithubBranchesView.as_view(), name='github-branches'),
]
