from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import NotificationSettingsView, NotificationViewSet

router = DefaultRouter()
router.register('', NotificationViewSet, basename='notification')

urlpatterns = [
    path('settings/', NotificationSettingsView.as_view(), name='notification-settings'),
] + router.urls
