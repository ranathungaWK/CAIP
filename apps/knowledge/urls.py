from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import KnowledgeItemViewSet, KnowledgeRelationshipViewSet

router = DefaultRouter()
router.register(r'items', KnowledgeItemViewSet, basename='knowledge-item')
router.register(r'relationships', KnowledgeRelationshipViewSet, basename='knowledge-relationship')

urlpatterns = [
    path('', include(router.urls)),
]
