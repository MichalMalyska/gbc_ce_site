import { CourseCard } from '@/components/CourseCard';
import { Filters } from '@/components/Filters';
import { SearchBar } from '@/components/SearchBar';
import { ThemeToggle } from '@/components/ThemeToggle';
import { useDataSource } from '@/hooks/useDataSource';
import { useQuery } from '@tanstack/react-query';
import { useRouter } from 'next/router';
import { useEffect, useState } from 'react';

// Helper function to create a consistent query string representation
const normalizeQuery = (query: Record<string, string | string[] | undefined>): string => {
  const params = new URLSearchParams();
  Object.keys(query).sort().forEach(key => {
    // Ignore nextjs internal params
    if (key.startsWith('__next')) return;

    const value = query[key];
    if (value !== undefined && value !== null) { // Ensure value exists
      if (Array.isArray(value)) {
        if (value.length > 0) {
          // Sort array values for consistent order
          [...value].sort().forEach(item => params.append(key, item));
        }
      } else if (String(value).length > 0) {
         params.append(key, String(value));
      }
    }
  });
  // Exclude common pagination/internal params if necessary, ensure stable sort
  params.sort();
  return params.toString(); // Returns sorted, encoded string like "a=1&b=2"
};

export default function Home() {
  const router = useRouter();

  const [search, setSearch] = useState('');
  const [selectedDays, setSelectedDays] = useState<string[]>([]);
  const [selectedTimeOfDay, setSelectedTimeOfDay] = useState('');
  const [selectedPrefix, setSelectedPrefix] = useState('');
  const [selectedDeliveryType, setSelectedDeliveryType] = useState('');

  // New state for date filtering and sorting
  const [startDateAfter, setStartDateAfter] = useState(''); // YYYY-MM-DD
  const [endDateBefore, setEndDateBefore] = useState('');   // YYYY-MM-DD
  const [ordering, setOrdering] = useState('course_code'); // Default sort

  // Effect to initialize state from URL query parameters on mount
  useEffect(() => {
    const { query } = router;
    setSearch(query.search ? String(query.search) : '');
    setSelectedDays(query.days ? (Array.isArray(query.days) ? query.days : [query.days]) : []);
    setSelectedTimeOfDay(query.timeOfDay ? String(query.timeOfDay) : '');
    setSelectedPrefix(query.prefix ? String(query.prefix) : '');
    setSelectedDeliveryType(query.deliveryType ? String(query.deliveryType) : '');
    setStartDateAfter(query.startDateAfter ? String(query.startDateAfter) : '');
    setEndDateBefore(query.endDateBefore ? String(query.endDateBefore) : '');
    setOrdering(query.ordering ? String(query.ordering) : 'course_code');
    // We only want this to run once on mount, based on initial query params.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [router.isReady]); // Run when router is ready and query is available

  // Effect to update URL query parameters when filters change
  useEffect(() => {
    if (!router.isReady) return;

    const currentQuery = router.query;
    const newQuery: Record<string, string | string[]> = {};

    if (search) newQuery.search = search;
    if (selectedDays.length > 0) newQuery.days = selectedDays;
    if (selectedTimeOfDay) newQuery.timeOfDay = selectedTimeOfDay;
    if (selectedPrefix) newQuery.prefix = selectedPrefix;
    if (selectedDeliveryType) newQuery.deliveryType = selectedDeliveryType;
    if (startDateAfter) newQuery.startDateAfter = startDateAfter;
    if (endDateBefore) newQuery.endDateBefore = endDateBefore;
    if (ordering && ordering !== 'course_code') newQuery.ordering = ordering; // Only add if not default

    // Use the normalized comparison
    const currentQueryString = normalizeQuery(currentQuery);
    const newQueryString = normalizeQuery(newQuery);

    if (currentQueryString !== newQueryString) {
        const urlObject = {
            pathname: router.pathname,
            query: newQuery,
        };
        router.replace(
            urlObject,
            undefined,
            { shallow: true } // Use shallow routing to prevent re-running data fetching logic unnecessarily
        );
    }

  }, [search, selectedDays, selectedTimeOfDay, selectedPrefix, selectedDeliveryType, startDateAfter, endDateBefore, ordering, router.isReady, router.pathname, router.query]);

  // Check if any filter is active
  const hasActiveFilters = Boolean(
    search || selectedDays.length > 0 || selectedPrefix || selectedDeliveryType || selectedTimeOfDay || startDateAfter || endDateBefore
  );

  const { fetchCourses, isTestMode } = useDataSource();

  const { data, isLoading } = useQuery({
    queryKey: ['courses', {
      search,
      selectedDays,
      selectedTimeOfDay,
      selectedPrefix,
      selectedDeliveryType,
      startDateAfter,
      endDateBefore,
      ordering,
    }],
    queryFn: () => {
      if (!hasActiveFilters) {
        return Promise.resolve({
          count: 0,
          next: null,
          previous: null,
          results: [],
        });
      }

      return fetchCourses({
        search: search,
        prefix: selectedPrefix,
        days: selectedDays,
        start_after: selectedTimeOfDay === 'evening' ? '17:00' : undefined,
        end_before: selectedTimeOfDay === 'morning' ? '12:00' :
          selectedTimeOfDay === 'afternoon' ? '17:00' : undefined,
        delivery_type: selectedDeliveryType,
        start_date_after: startDateAfter,
        end_date_before: endDateBefore,
        ordering: ordering,
      });
    },
    enabled: hasActiveFilters || Object.keys(router.query).length > 0,
    placeholderData: (previousData) => previousData,
  });

  return (
    <div className="min-h-screen bg-background text-foreground transition-colors">
      <main className="container mx-auto px-4 py-8">
        <div className="bg-card dark:bg-card-dark rounded-lg shadow-sm p-6 mb-8">
          <h1 className="text-3xl font-bold mb-6 text-card-foreground dark:text-card-foreground-dark flex justify-between items-center">
            GBC Course Catalog
            <div className="flex items-center gap-4">
              {isTestMode && (
                <span className="text-sm font-normal px-2 py-1 bg-yellow-100 text-yellow-800 rounded">
                  Test Mode
                </span>
              )}
              <ThemeToggle />
            </div>
          </h1>

          <SearchBar value={search} onChange={setSearch} />

          <Filters
            selectedDays={selectedDays}
            onDaysChange={setSelectedDays}
            selectedTimeOfDay={selectedTimeOfDay}
            onTimeOfDayChange={setSelectedTimeOfDay}
            selectedPrefix={selectedPrefix}
            onPrefixChange={setSelectedPrefix}
            selectedDeliveryType={selectedDeliveryType}
            onDeliveryTypeChange={setSelectedDeliveryType}
            startDateAfter={startDateAfter}
            onStartDateChange={setStartDateAfter}
            endDateBefore={endDateBefore}
            onEndDateChange={setEndDateBefore}
            ordering={ordering}
            onOrderingChange={setOrdering}
          />
        </div>

        {/* Show initial message only if no filters are active AND no query params exist */}
        {!hasActiveFilters && Object.keys(router.query).length === 0 ? (
          <div className="text-center py-12 bg-card dark:bg-card-dark rounded-lg shadow-sm">
            <p className="text-muted-foreground dark:text-muted-foreground-dark">
              Select a department or enter search terms to view courses
            </p>
          </div>
        ) : isLoading ? (
          <div className="flex justify-center items-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent dark:border-accent-dark"></div>
          </div>
        ) : (
          <>
            <div className="bg-card dark:bg-card-dark rounded-lg shadow-sm overflow-hidden mb-8">
              {data?.results.map((course) => (
                <CourseCard
                  key={course.id}
                  course={course}
                  selectedDays={selectedDays}
                  startDateFilter={startDateAfter}
                  endDateFilter={endDateBefore}
                />
              ))}
            </div>

            {data?.results.length === 0 && (
              <div className="text-center py-12 bg-card dark:bg-card-dark rounded-lg shadow-sm">
                <p className="text-muted-foreground dark:text-muted-foreground-dark">
                  No courses found matching your criteria
                </p>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
