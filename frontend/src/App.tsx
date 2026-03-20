import { useState, useEffect } from 'react'
import {
  QueryClient,
  QueryClientProvider,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query'
import { Check, Plus, Trash2, Calendar, Sun, Moon } from 'lucide-react'
import { formatDistanceToNow, isPast, isToday, parseISO } from 'date-fns'
import { api } from './api/client'
import type { CreateTodoRequest, Priority, Todo } from './types/api'
import './index.css'

type FilterMode = 'all' | 'active' | 'completed'

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 2000, retry: 1 } },
})

// ── Sidebar ──────────────────────────────────────────────────────────────────

function Sidebar() {
  const { data: me } = useQuery({ queryKey: ['me'], queryFn: () => api.getMe() })
  const { data: stats } = useQuery({
    queryKey: ['stats'],
    queryFn: () => api.getStats(),
    refetchInterval: 30000,
  })

  const total       = stats?.total        ?? 0
  const completed   = stats?.completed    ?? 0
  const pending     = stats?.pending      ?? 0
  const highPri     = stats?.high_priority ?? 0
  const pct         = total > 0 ? Math.round((completed / total) * 100) : 0
  const displayName = me?.display_name || me?.name || me?.email?.split('@')[0] || '—'
  const initials    = displayName.slice(0, 2).toUpperCase()
  const email       = me?.email ?? ''

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="brand-mark">
          <div className="brand-icon">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path d="M7 1L13 4V10L7 13L1 10V4L7 1Z" fill="#0B2026" />
              <path d="M7 4L10 5.5V8.5L7 10L4 8.5V5.5L7 4Z" fill="#FF3621" />
            </svg>
          </div>
          <span className="brand-name">Lakebase</span>
        </div>
        <span className="brand-sub">Todo App</span>
      </div>

      <div className="user-chip">
        <div className="user-avatar">{initials}</div>
        <span className="user-name">{email}</span>
      </div>

      <div className="sidebar-stats">
        <div className="stats-eyebrow">Overview</div>

        <div className="stat-hero">
          <div className="stat-hero-number">{total}</div>
          <div className="stat-hero-label">total tasks</div>
        </div>

        <div className="stat-divider" />

        <div className="stat-row">
          <span className="stat-row-left">
            <span className="stat-pip" style={{ background: 'var(--accent)' }} />
            completed
          </span>
          <span className="stat-row-value">{completed}</span>
        </div>
        <div className="stat-row">
          <span className="stat-row-left">
            <span className="stat-pip" style={{ background: 'var(--warning)' }} />
            pending
          </span>
          <span className="stat-row-value">{pending}</span>
        </div>
        <div className="stat-row">
          <span className="stat-row-left">
            <span className="stat-pip" style={{ background: 'var(--danger)' }} />
            high priority
          </span>
          <span className="stat-row-value">{highPri}</span>
        </div>

        <div className="progress-wrap">
          <div className="progress-head">
            <span className="stats-eyebrow" style={{ marginBottom: 0 }}>Progress</span>
            <span className="progress-pct">{pct}%</span>
          </div>
          <div className="progress-track">
            <div className="progress-fill" style={{ width: `${pct}%` }} />
          </div>
        </div>
      </div>

      <div className="sidebar-footer">
        <img
          src="https://cdn.bfldr.com/9AYANS2F/at/k8bgnnxhb4bggjk88r4x9snf/databricks-symbol-color.svg?auto=webp&format=png"
          alt="Databricks"
          className="footer-logo"
        />
        <span className="footer-text">Powered by Databricks Apps</span>
      </div>
    </aside>
  )
}

// ── Add todo ──────────────────────────────────────────────────────────────────

function AddSection() {
  const qc = useQueryClient()
  const [open, setOpen]               = useState(false)
  const [title, setTitle]             = useState('')
  const [description, setDescription] = useState('')
  const [priority, setPriority]       = useState<Priority>('medium')
  const [dueDate, setDueDate]         = useState('')

  const createMutation = useMutation({
    mutationFn: (req: CreateTodoRequest) => api.createTodo(req),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['todos'] })
      qc.invalidateQueries({ queryKey: ['stats'] })
      setTitle(''); setDescription(''); setPriority('medium'); setDueDate(''); setOpen(false)
    },
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!title.trim()) return
    createMutation.mutate({
      title: title.trim(),
      description: description.trim() || undefined,
      priority,
      due_date: dueDate || undefined,
    })
  }

  function handleCancel() {
    setOpen(false); setTitle(''); setDescription(''); setPriority('medium'); setDueDate('')
  }

  return (
    <div className="add-section">
      {!open ? (
        <button className="add-trigger" onClick={() => setOpen(true)}>
          <span className="add-trigger-ring">
            <Plus size={12} strokeWidth={2.5} />
          </span>
          New task…
        </button>
      ) : (
        <form onSubmit={handleSubmit} className="add-form">
          <div className="form-title-row">
            <input
              autoFocus
              className="form-title-input"
              placeholder="Task title"
              value={title}
              onChange={e => setTitle(e.target.value)}
              onKeyDown={e => e.key === 'Escape' && handleCancel()}
            />
          </div>
          <div className="form-body">
            <textarea
              className="form-desc"
              placeholder="Add a description…"
              value={description}
              onChange={e => setDescription(e.target.value)}
              rows={2}
            />
            <div className="form-controls">
              {(['high', 'medium', 'low'] as Priority[]).map(p => (
                <button
                  key={p}
                  type="button"
                  className={`p-btn${priority === p ? ` sel-${p}` : ''}`}
                  onClick={() => setPriority(p)}
                >
                  {p}
                </button>
              ))}
              <input
                type="date"
                className="date-input"
                value={dueDate}
                onChange={e => setDueDate(e.target.value)}
              />
            </div>
          </div>
          <div className="form-footer">
            <button type="button" className="btn-ghost" onClick={handleCancel}>Cancel</button>
            <button
              type="submit"
              className="btn-primary"
              disabled={!title.trim() || createMutation.isPending}
            >
              {createMutation.isPending ? 'Adding…' : 'Add task'}
            </button>
          </div>
        </form>
      )}
    </div>
  )
}

// ── Todo item ─────────────────────────────────────────────────────────────────

function TodoItem({ todo, index }: { todo: Todo; index: number }) {
  const qc = useQueryClient()

  const toggleMutation = useMutation({
    mutationFn: () => api.toggleTodo(todo.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['todos'] })
      qc.invalidateQueries({ queryKey: ['stats'] })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: () => api.deleteTodo(todo.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['todos'] })
      qc.invalidateQueries({ queryKey: ['stats'] })
    },
  })

  function dueClass() {
    if (!todo.due_date || todo.completed) return ''
    const d = parseISO(todo.due_date)
    if (isToday(d)) return 'today'
    if (isPast(d)) return 'overdue'
    return ''
  }

  function dueLabel() {
    if (!todo.due_date) return null
    return parseISO(todo.due_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }

  const timeAgo = formatDistanceToNow(new Date(todo.created_at), { addSuffix: true })
  const due = dueLabel()

  return (
    <div
      className={`todo-item p-${todo.priority}${todo.completed ? ' done' : ''}`}
      style={{ animationDelay: `${index * 35}ms` }}
    >
      <button
        className="todo-check"
        onClick={() => toggleMutation.mutate()}
        disabled={toggleMutation.isPending}
        title={todo.completed ? 'Mark incomplete' : 'Mark complete'}
      >
        {todo.completed && <Check size={11} strokeWidth={3} />}
      </button>

      <div className="todo-body">
        <div className="todo-title">{todo.title}</div>
        <div className="todo-meta">
          {todo.description && (
            <>
              <span className="todo-desc">{todo.description}</span>
              <span className="meta-dot" />
            </>
          )}
          <span className={`p-tag ${todo.priority}`}>{todo.priority}</span>
          {due && (
            <>
              <span className="meta-dot" />
              <span className={`due-tag ${dueClass()}`}>
                <Calendar size={10} />
                {due}
              </span>
            </>
          )}
          <span className="meta-dot" />
          <span className="time-tag">{timeAgo}</span>
        </div>
      </div>

      <div className="todo-actions">
        <button
          className="btn-del"
          onClick={() => deleteMutation.mutate()}
          disabled={deleteMutation.isPending}
          title="Delete"
        >
          <Trash2 size={13} />
        </button>
      </div>
    </div>
  )
}

// ── Todo list ─────────────────────────────────────────────────────────────────

function TodoList({ filter }: { filter: FilterMode }) {
  const completed = filter === 'all' ? undefined : filter === 'completed'
  const { data, isLoading } = useQuery({
    queryKey: ['todos', filter],
    queryFn: () => api.listTodos(completed),
  })

  const todos = data?.todos ?? []

  if (isLoading) {
    return (
      <div className="todo-scroll">
        {[60, 45, 75, 50].map((w, i) => (
          <div key={i} className="skeleton-row">
            <div className="skel" style={{ width: 20, height: 20, borderRadius: '50%' }} />
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 6 }}>
              <div className="skel" style={{ height: 14, width: `${w}%` }} />
              <div className="skel" style={{ height: 10, width: '28%' }} />
            </div>
          </div>
        ))}
      </div>
    )
  }

  if (todos.length === 0) {
    return (
      <div className="todo-scroll">
        <div className="empty">
          <span className="empty-glyph">∅</span>
          <span className="empty-label">
            {filter === 'completed' ? 'Nothing completed yet'
              : filter === 'active' ? 'All caught up'
              : 'No tasks yet'}
          </span>
        </div>
      </div>
    )
  }

  return (
    <div className="todo-scroll">
      {todos.map((todo, i) => (
        <TodoItem key={todo.id} todo={todo} index={i} />
      ))}
    </div>
  )
}

// ── App ───────────────────────────────────────────────────────────────────────

function AppContent() {
  const [filter, setFilter] = useState<FilterMode>('all')
  const [dark, setDark] = useState(() => {
    const saved = localStorage.getItem('theme')
    return saved ? saved === 'dark' : true
  })

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light')
    localStorage.setItem('theme', dark ? 'dark' : 'light')
  }, [dark])

  return (
    <div className="app-layout">
      <Sidebar />
      <div className="main-area">
        <div className="main-header">
          <span className="main-heading">Tasks</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div className="filter-tabs">
              {(['all', 'active', 'completed'] as FilterMode[]).map(f => (
                <button
                  key={f}
                  className={`filter-tab${filter === f ? ' active' : ''}`}
                  onClick={() => setFilter(f)}
                >
                  {f}
                </button>
              ))}
            </div>
            <button className="theme-toggle" onClick={() => setDark(d => !d)} title="Toggle theme">
              {dark ? <Sun size={14} /> : <Moon size={14} />}
            </button>
          </div>
        </div>
        <AddSection />
        <TodoList filter={filter} />
      </div>
    </div>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppContent />
    </QueryClientProvider>
  )
}
