from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProjectArtifactViewSet

router = DefaultRouter()
router.register(r'', ProjectArtifactViewSet, basename='artifact')

urlpatterns = [
    path('', include(router.urls)),
]
