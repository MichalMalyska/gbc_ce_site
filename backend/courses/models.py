from django.db import models

class Course(models.Model):
    course_code = models.CharField(max_length=20, unique=True)
    course_name = models.CharField(max_length=255)
    course_delivery_type = models.CharField(max_length=50, null=True, blank=True)
    prereqs = models.TextField(null=True, blank=True)
    hours = models.CharField(max_length=50, null=True, blank=True)
    fees = models.CharField(max_length=100, null=True, blank=True)
    course_description = models.TextField(null=True, blank=True)
    course_link = models.URLField(null=True, blank=True)

    def __str__(self):
        return f"{self.course_code} - {self.course_name}"

class Schedule(models.Model):
    course = models.ForeignKey(Course, related_name='schedules', on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    day_of_week = models.CharField(max_length=50)  # Store as comma-separated string
    start_time = models.TimeField()
    end_time = models.TimeField()

    def __str__(self):
        return f"{self.course.course_code} - {self.day_of_week} {self.start_time}"

    class Meta:
        indexes = [
            models.Index(fields=['day_of_week']),
            models.Index(fields=['start_time']),
            models.Index(fields=['end_time']),
        ] 