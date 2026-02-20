import type {
  CreateTodoRequest,
  CurrentUser,
  HealthResponse,
  Todo,
  TodoListResponse,
  TodoStats,
  UpdateTodoRequest,
} from '../types/api';

const API_BASE = '/api';

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function request<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
    },
    ...options,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new ApiError(error.detail || 'Request failed', response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

export const api = {
  health: () => request<HealthResponse>('/health'),

  getMe: () => request<CurrentUser>('/me'),

  listTodos: (completed?: boolean) => {
    const params = new URLSearchParams();
    if (completed !== undefined) params.set('completed', String(completed));
    const query = params.toString();
    return request<TodoListResponse>(`/todos${query ? `?${query}` : ''}`);
  },

  createTodo: (data: CreateTodoRequest) =>
    request<Todo>('/todos', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateTodo: (id: string, data: UpdateTodoRequest) =>
    request<Todo>(`/todos/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  toggleTodo: (id: string) =>
    request<Todo>(`/todos/${id}/toggle`, { method: 'PATCH' }),

  deleteTodo: (id: string) =>
    request<void>(`/todos/${id}`, { method: 'DELETE' }),

  getStats: () => request<TodoStats>('/stats'),
};
