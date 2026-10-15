from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import AttachmentSettingsView, AttachmentViewSet

router = DefaultRouter()
router.register('', AttachmentViewSet, basename='attachment')

urlpatterns = [
    path('settings/', AttachmentSettingsView.as_view(), name='attachment-settings'),
] + router.urls
