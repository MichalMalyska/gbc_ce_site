import { Course, Schedule } from '@/types/api';
import { format, isAfter, isBefore, isEqual, parseISO } from 'date-fns';

interface CourseCardProps {
  course: Course;
  selectedDays: string[];
  startDateFilter: string;
  endDateFilter: string;
}

// Helper function to filter and group schedules
function groupSchedules(
  schedules: Schedule[],
  selectedDays: string[],
  startDateFilter: string,
  endDateFilter: string
) {
  // First, filter schedules to only include selected days
  const filterStartDate = startDateFilter ? parseISO(startDateFilter) : null;
  const filterEndDate = endDateFilter ? parseISO(endDateFilter) : null;

  const filteredSchedules = schedules.filter(s => {
    // Day of week filter
    const dayMatch = selectedDays.length === 0 || selectedDays.includes(s.day_of_week);
    if (!dayMatch) return false;

    // Date range filter
    const scheduleStartDate = parseISO(s.start_date);
    const scheduleEndDate = parseISO(s.end_date);

    const startMatch = !filterStartDate || isAfter(scheduleStartDate, filterStartDate) || isEqual(scheduleStartDate, filterStartDate);
    const endMatch = !filterEndDate || isBefore(scheduleEndDate, filterEndDate) || isEqual(scheduleEndDate, filterEndDate);

    return startMatch && endMatch;
  });

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

export function CourseCard({ course, selectedDays, startDateFilter, endDateFilter }: CourseCardProps) {
  const groupedSchedules = groupSchedules(
    course.schedules,
    selectedDays,
    startDateFilter,
    endDateFilter
  );

  // Don't render the card if no schedules match the selected days AND dates
  if (groupedSchedules.length === 0) return null;

  return (
    <div className="px-4 py-3 bg-card dark:bg-card-dark border-b border-gray-200 dark:border-slate-700 hover:bg-gray-50 dark:hover:bg-slate-700">
      <div className="flex justify-between items-start gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h3 className="text-base font-semibold">
              <a
                href={course.course_link || '#'}
                target="_blank"
                rel="noopener noreferrer"
                className="text-accent dark:text-accent-dark hover:opacity-80"
              >
                {course.course_code} - {course.course_name}
              </a>
            </h3>
            {getDeliveryTypeBadge(course.course_delivery_type)}
          </div>
          <div className="mt-2 space-y-2">
            {groupedSchedules.map((scheduleGroup, index) => (
              <div key={index} className="flex items-center text-sm text-muted-foreground dark:text-muted-foreground-dark">
                <span className="w-24 flex-shrink-0">{formatDays(scheduleGroup)}</span>
                {formatTimeDisplay(scheduleGroup[0])}
                <span className="text-xs">
                  {format(parseISO(scheduleGroup[0].start_date), 'MMM d')} -
                  {format(parseISO(scheduleGroup[0].end_date), 'MMM d')}
                </span>
              </div>
            ))}
          </div>
        </div>
        <div className="flex-shrink-0 text-right">
          <div className="text-sm font-medium text-foreground dark:text-foreground-dark">
            {course.fees}
          </div>
          {course.hours && (
            <div className="text-xs text-muted-foreground dark:text-muted-foreground-dark">
              {course.hours} hours
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
