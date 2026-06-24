from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import ProjectArtifact
from .serializers import ProjectArtifactSerializer
from apps.authentication.authentication import SupabaseAuthentication

class ProjectArtifactViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectArtifactSerializer
    authentication_classes = [SupabaseAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ProjectArtifact.objects.filter(project__owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)
