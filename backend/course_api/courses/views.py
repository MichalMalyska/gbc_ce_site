from datetime import datetime, time

from django.db.models import Count, Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Course, Schedule
from .serializers import CourseSerializer


class CourseViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CourseSerializer

    def get_queryset(self):
        queryset = Course.objects.all().prefetch_related("schedules")

        # Filter by search term
        search = self.request.query_params.get("search", None)
        if search:
            queryset = queryset.filter(
                Q(course_code__icontains=search)
                | Q(course_name__icontains=search)
                | Q(course_prefix__icontains=search)
            )

        # Filter by day of week
        day = self.request.query_params.get("day", None)
        if day:
            queryset = queryset.filter(schedules__day_of_week=day)

        # Filter by time
        start_after = self.request.query_params.get("start_after", None)
        if start_after:
            queryset = queryset.filter(schedules__start_time__gte=start_after)

        end_before = self.request.query_params.get("end_before", None)
        if end_before:
            queryset = queryset.filter(schedules__end_time__lte=end_before)

        # Filter courses with schedules
        has_schedules = self.request.query_params.get("has_schedules", None)
        if has_schedules == "true":
            queryset = queryset.annotate(schedule_count=Count("schedules")).filter(
                schedule_count__gt=0
            )

        # Filter by delivery type
        delivery_type = self.request.query_params.get("delivery_type", None)
        if delivery_type:
            queryset = queryset.filter(course_delivery_type__iexact=delivery_type)

        return queryset.distinct()

    @action(detail=False, methods=["get"])
    def prefixes(self, request):
        # Get unique prefixes only from courses that have schedules
        prefixes = (
            Course.objects.filter(schedules__isnull=False)
            .values_list("course_prefix", flat=True)
            .distinct()
            .order_by("course_prefix")
        )

        return Response(list(prefixes))
