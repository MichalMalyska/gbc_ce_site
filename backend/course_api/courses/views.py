from django.db.models import Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Course
from .serializers import CourseSerializer


class CourseViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CourseSerializer

    def get_queryset(self):
        queryset = Course.objects.all().prefetch_related("schedules")

        # Filter by search term
        search = self.request.query_params.get("search", None)
        if search:
            # Split search terms and create Q objects for each term
            terms = search.split()
            query = Q()
            for term in terms:
                term_query = Q(course_code__icontains=term) | Q(
                    course_name__icontains=term
                )
                query &= term_query
            queryset = queryset.filter(query)

        # Filter by prefix (department)
        prefix = self.request.query_params.get("prefix", None)
        if prefix:
            queryset = queryset.filter(course_prefix=prefix)

        # Filter by day of week
        days = self.request.query_params.getlist("day")
        if days:
            day_query = Q()
            for day in days:
                day_query |= Q(schedules__day_of_week=day)
            queryset = queryset.filter(day_query)

        # Filter by time of day
        start_after = self.request.query_params.get("start_after", None)
        if start_after:
            queryset = queryset.filter(schedules__start_time__gte=start_after)

        end_before = self.request.query_params.get("end_before", None)
        if end_before:
            queryset = queryset.filter(schedules__start_time__lte=end_before)

        # Filter by delivery type
        delivery_type = self.request.query_params.get("delivery_type", None)
        if delivery_type:
            queryset = queryset.filter(course_delivery_type__iexact=delivery_type)

        # Filter for courses with schedules
        has_schedules = self.request.query_params.get("has_schedules", None)
        if has_schedules:
            queryset = queryset.filter(schedules__isnull=False)

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
