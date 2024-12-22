export interface Course {
  id: number;
  course_code: string;
  course_prefix: string;
  course_number: string;
  course_name: string;
  course_delivery_type: string | null;
  prereqs: string | null;
  hours: string | null;
  fees: string | null;
  course_description: string | null;
  course_link: string | null;
  schedules: Schedule[];
}

export interface Schedule {
  id: number;
  start_date: string;  // ISO date string
  end_date: string;    // ISO date string
  day_of_week: string;
  start_time: string | null;  // HH:MM:SS
  end_time: string | null;    // HH:MM:SS
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface CourseFilters {
  search?: string;
  days?: string[];
  start_after?: string;
  end_before?: string;
  delivery_type?: string;
} 