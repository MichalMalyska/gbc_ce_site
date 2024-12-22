from courses.views import CourseViewSet
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r"courses", CourseViewSet, basename="course")

urlpatterns = [
    path("", RedirectView.as_view(url="/api/", permanent=False)),
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
]
