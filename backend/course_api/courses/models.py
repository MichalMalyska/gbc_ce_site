from django.db import models


class Course(models.Model):
    course_code = models.CharField(max_length=20, unique=True)
    course_prefix = models.CharField(max_length=10)
    course_number = models.CharField(max_length=10)
    course_name = models.CharField(max_length=255)
    course_delivery_type = models.CharField(max_length=50, null=True, blank=True)
    prereqs = models.TextField(null=True, blank=True)
    hours = models.CharField(max_length=20, null=True, blank=True)
    fees = models.CharField(max_length=50, null=True, blank=True)
    course_description = models.TextField(null=True, blank=True)
    course_link = models.URLField(max_length=500, null=True, blank=True)

    def __str__(self):
        return f"{self.course_code} - {self.course_name}"

    class Meta:
        ordering = ["course_prefix", "course_number"]


class Schedule(models.Model):
    course = models.ForeignKey(Course, related_name="schedules", on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    day_of_week = models.CharField(max_length=50)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.course.course_code} - {self.day_of_week}"

    class Meta:
        ordering = ["start_date", "start_time"]
