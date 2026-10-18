from rest_framework.routers import DefaultRouter

from .views import (
    CustomPriorityViewSet, CustomTaskStatusViewSet, SavedTaskFilterViewSet,
    TaskTagViewSet, TaskViewSet,
)

router = DefaultRouter()
router.register('statuses', CustomTaskStatusViewSet, basename='custom-status')
router.register('priorities', CustomPriorityViewSet, basename='custom-priority')
router.register('tags', TaskTagViewSet, basename='task-tag')
router.register('saved-filters', SavedTaskFilterViewSet, basename='saved-task-filter')
router.register('', TaskViewSet, basename='task')

urlpatterns = router.urls
