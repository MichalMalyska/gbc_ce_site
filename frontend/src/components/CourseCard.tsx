import { Course, Schedule } from '@/types/api';
import { format } from 'date-fns';

interface CourseCardProps {
  course: Course;
  selectedDays: string[];
}

// Helper function to filter and group schedules
function groupSchedules(schedules: Schedule[], selectedDays: string[]) {
  // First, filter schedules to only include selected days
  const filteredSchedules = selectedDays.length > 0
    ? schedules.filter(s => selectedDays.includes(s.day_of_week))
    : schedules;

  const groups = new Map<string, Schedule[]>();

  filteredSchedules.forEach(schedule => {
    const timeKey = schedule.start_time && schedule.end_time
      ? `${schedule.start_time}-${schedule.end_time}`
      : 'no-time';
    const dateKey = `${schedule.start_date}-${schedule.end_date}`;
    const key = `${timeKey}-${dateKey}`;

    if (!groups.has(key)) {
      groups.set(key, []);
    }
    groups.get(key)!.push(schedule);
  });

  // Only return groups that have all their days selected
  return Array.from(groups.values()).filter(group => {
    if (selectedDays.length === 0) return true;
    return group.every(schedule => selectedDays.includes(schedule.day_of_week));
  });
}

// Helper function to format days of week
function formatDays(schedules: Schedule[]) {
  // Sort days to ensure consistent order
  const dayOrder = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
  const sortedSchedules = [...schedules].sort((a, b) =>
    dayOrder.indexOf(a.day_of_week) - dayOrder.indexOf(b.day_of_week)
  );

  const days = sortedSchedules.map(s => s.day_of_week.slice(0, 3));
  if (days.length === 1) return days[0];
  if (days.length === 2) return `${days[0]} & ${days[1]}`;
  return days.join(', ');
}

// Helper function to format time display
function formatTimeDisplay(schedule: Schedule) {
  if (schedule.start_time && schedule.end_time) {
    return (
      <span className="w-32 flex-shrink-0">
        {schedule.start_time.slice(0, 5)} - {schedule.end_time.slice(0, 5)}
      </span>
    );
  }
  return (
    <span className="w-32 flex-shrink-0 italic text-gray-400 dark:text-gray-500">
      Time TBD
    </span>
  );
}

// Helper function to get delivery type badge style
function getDeliveryTypeBadge(deliveryType: string | null) {
  if (!deliveryType) return null;

  const baseClasses = "text-xs px-2 py-0.5 rounded-full font-medium";

  switch (deliveryType.toLowerCase()) {
    case 'online':
      return (
        <span className={`${baseClasses} bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300`}>
          Online
        </span>
      );
    case 'on campus':
      return (
        <span className={`${baseClasses} bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300`}>
          On Campus
        </span>
      );
    default:
      return (
        <span className={`${baseClasses} bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300`}>
          {deliveryType}
        </span>
      );
  }
}

export function CourseCard({ course, selectedDays }: CourseCardProps) {
  const groupedSchedules = groupSchedules(course.schedules, selectedDays);

  // Don't render the card if no schedules match the selected days
  if (groupedSchedules.length === 0) return null;

  return (
    <div className="px-4 py-3 bg-white dark:bg-gray-800 border-b dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-750">
      <div className="flex justify-between items-start gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-medium truncate">
              <a
                href={course.course_link || '#'}
                target="_blank"
                rel="noopener noreferrer"
                className="text-indigo-600 hover:text-indigo-500 dark:text-indigo-400 dark:hover:text-indigo-300"
              >
                {course.course_code} - {course.course_name}
              </a>
            </h3>
            {getDeliveryTypeBadge(course.course_delivery_type)}
          </div>
          <div className="mt-1 space-y-1">
            {groupedSchedules.map((scheduleGroup, index) => (
              <div key={index} className="flex items-center text-sm text-gray-500 dark:text-gray-400">
                <span className="w-24 flex-shrink-0">{formatDays(scheduleGroup)}</span>
                {formatTimeDisplay(scheduleGroup[0])}
                <span className="text-xs">
                  {format(new Date(scheduleGroup[0].start_date), 'MMM d')} -
                  {format(new Date(scheduleGroup[0].end_date), 'MMM d')}
                </span>
              </div>
            ))}
          </div>
        </div>
        <div className="flex-shrink-0 text-right">
          <div className="text-sm font-medium text-gray-900 dark:text-gray-200">
            {course.fees}
          </div>
          {course.hours && (
            <div className="text-xs text-gray-500 dark:text-gray-400">
              {course.hours} hours
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
