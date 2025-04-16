import { Course, CourseFilters, PaginatedResponse } from '@/types/api';
import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const fetchCourses = async (filters: CourseFilters): Promise<PaginatedResponse<Course>> => {
  const params = new URLSearchParams();

  if (filters.search) params.append('search', filters.search);
  if (filters.prefix) params.append('prefix', filters.prefix);
  if (filters.days?.length) filters.days.forEach(day => params.append('day', day));
  if (filters.start_after) params.append('start_after', filters.start_after);
  if (filters.end_before) params.append('end_before', filters.end_before);
  if (filters.delivery_type) params.append('delivery_type', filters.delivery_type);

  params.append('has_schedules', 'true');

  const { data } = await api.get<PaginatedResponse<Course>>(`/courses/?${params}`);
  return data;
};

export const fetchPrefixes = async (): Promise<string[]> => {
  const { data } = await api.get<string[]>('/courses/prefixes/');
  return data;
};
