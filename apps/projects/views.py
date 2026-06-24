from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Project
from .serializers import ProjectSerializer
from apps.authentication.authentication import SupabaseAuthentication
from services.project_knowledge import get_project_knowledge_base

class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    authentication_classes = [SupabaseAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Project.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['get'], url_path='knowledge-base')
    def knowledge_base(self, request, pk=None):
        data = get_project_knowledge_base(pk, request.user)
        if data is None:
            return Response({"detail": "Project not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(data)

