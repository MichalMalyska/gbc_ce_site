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
          
          if (filters.delivery_type) {
            filtered = filtered.filter(c => 
              c.course_delivery_type?.toLowerCase() === filters.delivery_type?.toLowerCase()
            );
          }
          
          if (filters.search) {
            const searchLower = filters.search.toLowerCase();
            filtered = filtered.filter(c => 
              c.course_code.toLowerCase().includes(searchLower) ||
              c.course_name.toLowerCase().includes(searchLower)
            );
          }

          if (filters.day) {
            filtered = filtered.filter(c => 
              c.schedules.some(s => s.day_of_week === filters.day)
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