from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Repository
from .serializers import RepositorySerializer
from apps.authentication.authentication import SupabaseAuthentication

class RepositoryViewSet(viewsets.ModelViewSet):
    serializer_class = RepositorySerializer
    authentication_classes = [SupabaseAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Only return repositories for projects owned by the user
        return Repository.objects.filter(project__owner=self.request.user)
