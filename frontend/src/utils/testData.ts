import { Course } from '@/types/api';

export const testCourses: Course[] = [
  {
    // Example 1: Complex course with multiple sections and days
    id: 1,
    course_code: "HOSF 9134",
    course_prefix: "HOSF",
    course_number: "9134",
    course_name: "Baking Arts",
    course_delivery_type: "on campus",
    prereqs: null,
    hours: "252",
    fees: "$3,186.58",
    course_description: "Professional baker training program",
    course_link: "https://coned.georgebrown.ca/courses/hosf-9134",
    schedules: [
      {
        id: 1,
        start_date: "2024-01-15",
        end_date: "2024-04-15",
        day_of_week: "Monday",
        start_time: "08:00:00",
        end_time: "16:00:00"
      },
      {
        id: 2,
        start_date: "2024-01-15",
        end_date: "2024-04-15",
        day_of_week: "Tuesday",
        start_time: "08:00:00",
        end_time: "16:00:00"
      },
      {
        id: 3,
        start_date: "2024-05-13",
        end_date: "2024-08-13",
        day_of_week: "Monday",
        start_time: "08:00:00",
        end_time: "16:00:00"
      },
      {
        id: 4,
        start_date: "2024-05-13",
        end_date: "2024-08-13",
        day_of_week: "Wednesday",
        start_time: "08:00:00",
        end_time: "16:00:00"
      },
      {
        id: 9,
        start_date: "2024-09-09",
        end_date: "2024-12-16",
        day_of_week: "Friday",
        start_time: "08:00:00",
        end_time: "16:00:00"
      }
    ]
  },
  {
    // Example 2: Simple online course
    id: 2,
    course_code: "COMP 1234",
    course_prefix: "COMP",
    course_number: "1234",
    course_name: "Introduction to Programming",
    course_delivery_type: "online",
    prereqs: null,
    hours: "42",
    fees: "$425.00",
    course_description: "Learn the basics of programming",
    course_link: "https://coned.georgebrown.ca/courses/comp-1234",
    schedules: [
      {
        id: 5,
        start_date: "2024-01-15",
        end_date: "2024-04-15",
        day_of_week: "Monday",
        start_time: "18:15:00",
        end_time: "21:15:00"
      }
    ]
  },
  {
    // Example 3: Course with TBD times
    id: 3,
    course_code: "COMM 1162",
    course_prefix: "COMM",
    course_number: "1162",
    course_name: "Business Communications",
    course_delivery_type: "online",
    prereqs: null,
    hours: "42",
    fees: "$425.00",
    course_description: "Develop business communication skills",
    course_link: "https://coned.georgebrown.ca/courses/comm-1162",
    schedules: [
      {
        id: 6,
        start_date: "2024-01-15",
        end_date: "2024-04-15",
        day_of_week: "Tuesday",
        start_time: null,
        end_time: null
      }
    ]
  },
  {
    // Example 4: Evening course with multiple days
    id: 4,
    course_code: "ARTS 1001",
    course_prefix: "ARTS",
    course_number: "1001",
    course_name: "Drawing Fundamentals",
    course_delivery_type: "on campus",
    prereqs: null,
    hours: "42",
    fees: "$395.00",
    course_description: "Learn drawing basics",
    course_link: "https://coned.georgebrown.ca/courses/arts-1001",
    schedules: [
      {
        id: 7,
        start_date: "2024-01-15",
        end_date: "2024-04-15",
        day_of_week: "Tuesday",
        start_time: "18:15:00",
        end_time: "21:15:00"
      },
      {
        id: 8,
        start_date: "2024-01-15",
        end_date: "2024-04-15",
        day_of_week: "Thursday",
        start_time: "18:15:00",
        end_time: "21:15:00"
      }
    ]
  }
];
