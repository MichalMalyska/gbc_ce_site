from django.core.management.base import BaseCommand
from datetime import datetime
import json
from pathlib import Path
from courses.models import Course, Schedule

class Command(BaseCommand):
    help = 'Load course data from JSON files'

    def parse_time(self, time_str):
        """Convert time string (e.g., '6:15PM') to time object"""
        return datetime.strptime(time_str, '%I:%M%p').time()

    def parse_date(self, date_str):
        """Convert date string (e.g., '07Nov2024') to datetime object"""
        return datetime.strptime(date_str, '%d%b%Y').date()

    def handle(self, *args, **options):
        json_dir = Path("data/course_data")
        
        for json_file in json_dir.glob('*.json'):
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            course, created = Course.objects.update_or_create(
                course_code=data['course_code'],
                defaults={
                    'course_name': data['course_name'],
                    'course_delivery_type': data.get('course_delivery_type'),
                    'prereqs': data.get('prereqs'),
                    'hours': data.get('hours'),
                    'fees': data.get('fees'),
                    'course_description': data.get('course_description'),
                    'course_link': data.get('course_link')
                }
            )

            if 'schedules' in data:
                for schedule_data in data['schedules']:
                    Schedule.objects.update_or_create(
                        course=course,
                        start_date=self.parse_date(schedule_data['start_date']),
                        end_date=self.parse_date(schedule_data['end_date']),
                        defaults={
                            'day_of_week': schedule_data['day_or_days_of_week'],
                            'start_time': self.parse_time(schedule_data['start_time']),
                            'end_time': self.parse_time(schedule_data['end_time'])
                        }
                    )

        self.stdout.write(self.style.SUCCESS('Successfully loaded course data')) 