import { fetchPrefixes } from '@/api/courses';
import { useQuery } from '@tanstack/react-query';

interface FiltersProps {
  selectedDays: string[];
  onDaysChange: (days: string[]) => void;
  selectedTimeOfDay: string;
  onTimeOfDayChange: (time: string) => void;
  selectedPrefix: string;
  onPrefixChange: (prefix: string) => void;
  selectedDeliveryType: string;
  onDeliveryTypeChange: (type: string) => void;
  startDateAfter: string;
  onStartDateChange: (date: string) => void;
  endDateBefore: string;
  onEndDateChange: (date: string) => void;
  ordering: string;
  onOrderingChange: (order: string) => void;
}

const DAYS_OF_WEEK = [
  'Monday',
  'Tuesday',
  'Wednesday',
  'Thursday',
  'Friday',
  'Saturday',
  'Sunday',
];

const TIMES_OF_DAY = [
  { label: 'All Times', value: '' },
  { label: 'Morning (before 12:00)', value: 'morning' },
  { label: 'Afternoon (12:00-17:00)', value: 'afternoon' },
  { label: 'Evening (after 17:00)', value: 'evening' },
];

const DELIVERY_TYPES = [
  { label: 'All Types', value: '' },
  { label: 'Online', value: 'online' },
  { label: 'On Campus', value: 'on campus' },
];

const SORTING_OPTIONS = [
  { label: 'Course Code (A-Z)', value: 'course_code' },
  { label: 'Course Code (Z-A)', value: '-course_code' },
  { label: 'Course Name (A-Z)', value: 'course_name' },
  { label: 'Course Name (Z-A)', value: '-course_name' },
  { label: 'Start Date (Earliest)', value: 'schedules__start_date' },
  { label: 'Start Date (Latest)', value: '-schedules__start_date' },
];

const selectClassName = "mt-1 block w-full rounded-md border-gray-300 dark:border-slate-600 shadow-sm focus:border-accent focus:ring-accent focus:ring-opacity-50 bg-white dark:bg-slate-700 text-foreground dark:text-foreground-dark";
const labelClassName = "text-sm font-medium text-muted-foreground dark:text-muted-foreground-dark mb-1";
const dateInputClassName = "mt-1 block w-full rounded-md border-gray-300 dark:border-slate-600 shadow-sm focus:border-accent focus:ring-accent focus:ring-opacity-50 bg-white dark:bg-slate-700 text-foreground dark:text-foreground-dark";

export function Filters({
  selectedDays,
  onDaysChange,
  selectedTimeOfDay,
  onTimeOfDayChange,
  selectedPrefix,
  onPrefixChange,
  selectedDeliveryType,
  onDeliveryTypeChange,
  startDateAfter,
  onStartDateChange,
  endDateBefore,
  onEndDateChange,
  ordering,
  onOrderingChange,
}: FiltersProps) {
  const { data: prefixes } = useQuery({
    queryKey: ['prefixes'],
    queryFn: fetchPrefixes,
  });

  const handleDayToggle = (day: string) => {
    if (selectedDays.includes(day)) {
      onDaysChange(selectedDays.filter(d => d !== day));
    } else {
      onDaysChange([...selectedDays, day]);
    }
  };

  return (
    <div className="flex flex-wrap gap-4 mt-6">
      {/* Day Filter */}
      <div className="flex flex-col flex-1 min-w-[200px]">
        <label className={labelClassName}>Days</label>
        <div className="mt-1 grid grid-cols-2 gap-2">
          {DAYS_OF_WEEK.map((day) => (
            <label
              key={day}
              className="flex items-center space-x-2 text-sm text-foreground dark:text-foreground-dark hover:bg-gray-100 dark:hover:bg-slate-700 p-1.5 rounded cursor-pointer"
            >
              <input
                type="checkbox"
                checked={selectedDays.includes(day)}
                onChange={() => handleDayToggle(day)}
                className="rounded border-gray-300 dark:border-slate-600 text-accent focus:ring-accent focus:ring-opacity-50 dark:bg-slate-700"
              />
              <span>{day}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Time of Day Filter */}
      <div className="flex flex-col flex-1 min-w-[200px]">
        <label className={labelClassName}>Time of Day</label>
        <select
          value={selectedTimeOfDay}
          onChange={(e) => onTimeOfDayChange(e.target.value)}
          className={selectClassName}
        >
          {TIMES_OF_DAY.map((time) => (
            <option key={time.value} value={time.value}>
              {time.label}
            </option>
          ))}
        </select>
      </div>

      {/* Course Prefix Filter */}
      <div className="flex flex-col flex-1 min-w-[200px]">
        <label className={labelClassName}>Department</label>
        <select
          value={selectedPrefix}
          onChange={(e) => onPrefixChange(e.target.value)}
          className={selectClassName}
        >
          <option value="">All Departments</option>
          {prefixes?.map((prefix) => (
            <option key={prefix} value={prefix}>
              {prefix}
            </option>
          ))}
        </select>
      </div>

      {/* Delivery Type Filter */}
      <div className="flex flex-col flex-1 min-w-[200px]">
        <label className={labelClassName}>Delivery Type</label>
        <select
          value={selectedDeliveryType}
          onChange={(e) => onDeliveryTypeChange(e.target.value)}
          className={selectClassName}
        >
          {DELIVERY_TYPES.map((type) => (
            <option key={type.value} value={type.value}>
              {type.label}
            </option>
          ))}
        </select>
      </div>

      {/* Start Date Filter */}
      <div className="flex flex-col flex-1 min-w-[150px]">
        <label className={labelClassName}>Start After</label>
        <input
          type="date"
          value={startDateAfter}
          onChange={(e) => onStartDateChange(e.target.value)}
          className={dateInputClassName}
        />
      </div>

      {/* End Date Filter */}
      <div className="flex flex-col flex-1 min-w-[150px]">
        <label className={labelClassName}>End Before</label>
        <input
          type="date"
          value={endDateBefore}
          onChange={(e) => onEndDateChange(e.target.value)}
          className={dateInputClassName}
        />
      </div>

      {/* Sort Order */}
      <div className="flex flex-col flex-1 min-w-[200px]">
        <label className={labelClassName}>Sort By</label>
        <select
          value={ordering}
          onChange={(e) => onOrderingChange(e.target.value)}
          className={selectClassName}
        >
          {SORTING_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
