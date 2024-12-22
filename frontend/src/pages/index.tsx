import { CourseCard } from '@/components/CourseCard';
import { Filters } from '@/components/Filters';
import { SearchBar } from '@/components/SearchBar';
import { ThemeToggle } from '@/components/ThemeToggle';
import { useDataSource } from '@/hooks/useDataSource';
import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';

export default function Home() {
  const [search, setSearch] = useState('');
  const [selectedDays, setSelectedDays] = useState<string[]>([]);
  const [selectedTimeOfDay, setSelectedTimeOfDay] = useState('');
  const [selectedPrefix, setSelectedPrefix] = useState('');
  const [selectedDeliveryType, setSelectedDeliveryType] = useState('');

  // Check if any filter is active
  const hasActiveFilters = Boolean(
    search || selectedDays.length > 0 || selectedPrefix || selectedDeliveryType
  );

  const { fetchCourses, isTestMode } = useDataSource();

  const { data, isLoading } = useQuery({
    queryKey: ['courses', { 
      search, 
      selectedDays, 
      selectedTimeOfDay, 
      selectedPrefix,
      selectedDeliveryType,
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
        search: selectedPrefix ? `${selectedPrefix} ${search}` : search,
        days: selectedDays,
        start_after: selectedTimeOfDay === 'evening' ? '17:00' : undefined,
        end_before: selectedTimeOfDay === 'morning' ? '12:00' : 
          selectedTimeOfDay === 'afternoon' ? '17:00' : undefined,
        delivery_type: selectedDeliveryType,
      });
    },
  });

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900 transition-colors">
      <main className="container mx-auto px-4 py-8">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6 mb-8">
          <h1 className="text-3xl font-bold mb-6 text-gray-900 dark:text-white flex justify-between items-center">
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
          />
        </div>

        {!hasActiveFilters ? (
          <div className="text-center py-12 bg-white dark:bg-gray-800 rounded-lg shadow-sm">
            <p className="text-gray-500 dark:text-gray-400">
              Select a department or enter search terms to view courses
            </p>
          </div>
        ) : isLoading ? (
          <div className="flex justify-center items-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-500"></div>
          </div>
        ) : (
          <>
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm overflow-hidden mb-8">
              {data?.results.map((course) => (
                <CourseCard key={course.id} course={course} selectedDays={selectedDays} />
              ))}
            </div>

            {data?.results.length === 0 && (
              <div className="text-center py-12 bg-white dark:bg-gray-800 rounded-lg shadow-sm">
                <p className="text-gray-500 dark:text-gray-400">
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
