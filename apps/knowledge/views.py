from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import KnowledgeItem, KnowledgeRelationship
from .serializers import KnowledgeItemSerializer, KnowledgeRelationshipSerializer
from apps.authentication.authentication import SupabaseAuthentication

class KnowledgeItemViewSet(viewsets.ModelViewSet):
    serializer_class = KnowledgeItemSerializer
    authentication_classes = [SupabaseAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return KnowledgeItem.objects.filter(project__owner=self.request.user)

class KnowledgeRelationshipViewSet(viewsets.ModelViewSet):
    serializer_class = KnowledgeRelationshipSerializer
    authentication_classes = [SupabaseAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return KnowledgeRelationship.objects.filter(source_item__project__owner=self.request.user)
