import os

from courses.models import Course, Schedule
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import joinedload, sessionmaker

from python_scrape.db.database import Base
from python_scrape.db.database import Course as SACourse


class Command(BaseCommand):
    help = "Import courses from SQLAlchemy database"

    def handle(self, *args, **options):
        # Load environment variables
        load_dotenv()
        db_uri = os.getenv("DB_URI")

        if not db_uri:
            self.stderr.write(self.style.ERROR("DB_URI environment variable not found"))
            return

        try:
            # Ensure migrations are applied
            self.stdout.write("Applying migrations...")
            call_command("migrate", "courses")

            # Connect to SQLAlchemy DB using environment variable
            engine = create_engine(db_uri)
            Base.metadata.bind = engine
            Session = sessionmaker(bind=engine)
            sa_session = Session()

            with transaction.atomic():
                # Clear existing data
                Course.objects.all().delete()

                # Import courses and schedules
                courses_imported = 0
                schedules_imported = 0

                # Query with eager loading of schedules
                query = sa_session.query(SACourse).options(
                    joinedload(SACourse.schedules)
                )
                total_courses = query.count()
                self.stdout.write(f"Found {total_courses} courses to import")

                # Use batching for better performance
                batch_size = 100
                for i in range(0, total_courses, batch_size):
                    batch = query.slice(i, i + batch_size).all()
                    self.stdout.write(f"Processing batch {i // batch_size + 1}...")

                    for sa_course in batch:
                        course = Course.objects.create(
                            course_code=sa_course.course_code,
                            course_prefix=sa_course.course_prefix,
                            course_number=sa_course.course_number,
                            course_name=sa_course.course_name,
                            course_delivery_type=sa_course.course_delivery_type,
                            prereqs=sa_course.prereqs,
                            hours=sa_course.hours,
                            fees=sa_course.fees,
                            course_description=sa_course.course_description,
                            course_link=sa_course.course_link,
                        )
                        courses_imported += 1

                        for sa_schedule in sa_course.schedules:
                            Schedule.objects.create(
                                course=course,
                                start_date=sa_schedule.start_date,
                                end_date=sa_schedule.end_date,
                                day_of_week=sa_schedule.day_of_week,
                                start_time=sa_schedule.start_time,
                                end_time=sa_schedule.end_time,
                            )
                            schedules_imported += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully imported {courses_imported} courses and {schedules_imported} schedules"
                    )
                )
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error importing courses: {str(e)}"))
            import traceback

            self.stderr.write(self.style.ERROR(traceback.format_exc()))
        finally:
            if "sa_session" in locals():
                sa_session.close()
