import { fetchCourses as fetchApiCourses } from '@/api/courses';
import { Course, CourseFilters, PaginatedResponse } from '@/types/api';
import { testCourses } from '@/utils/testData';

export function useDataSource() {
  const useTestData = process.env.NEXT_PUBLIC_USE_TEST_DATA === 'true';

  const fetchCourses = async (filters: CourseFilters): Promise<PaginatedResponse<Course>> => {
    if (useTestData) {
      // Test data logic
      return new Promise((resolve) => {
        setTimeout(() => {
          let filtered = testCourses;

          if (filters.prefix) {
            filtered = filtered.filter(c =>
              c.course_prefix === filters.prefix
            );
          }

          if (filters.search) {
            const searchTerms = filters.search.toLowerCase().split(' ').filter(Boolean);
            filtered = filtered.filter(c =>
              searchTerms.every(term =>
                c.course_code.toLowerCase().includes(term) ||
                c.course_name.toLowerCase().includes(term)
              )
            );
          }

          if (filters.days && filters.days.length > 0) {
            filtered = filtered.filter(c =>
              c.schedules.some(s => filters.days!.includes(s.day_of_week))
            );
          }

          resolve({
            count: filtered.length,
            next: null,
            previous: null,
            results: filtered,
          });
        }, 500);
      });
    }

    // Production data logic
    return fetchApiCourses(filters);
  };

  return {
    fetchCourses,
    isTestMode: useTestData,
  };
}
