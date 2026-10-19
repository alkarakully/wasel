import { CaretLeft, CaretRight, MagnifyingGlass, WarningCircle, X } from '@phosphor-icons/react'
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useId,
  useRef,
  useState,
  type ButtonHTMLAttributes,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
} from 'react'

import type { ApiError } from '../lib/api'
import { useI18n } from '../lib/i18n'

// --- Buttons -----------------------------------------------------------------

type Tone = 'primary' | 'secondary' | 'ghost' | 'danger'

export function Button({
  tone = 'secondary',
  busy,
  icon,
  children,
  className = '',
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { tone?: Tone; busy?: boolean; icon?: ReactNode }) {
  return (
    <button
      type="button"
      className={`btn btn-${tone} ${className}`}
      disabled={busy || rest.disabled}
      aria-busy={busy}
      {...rest}
    >
      {icon}
      {children && <span>{children}</span>}
    </button>
  )
}

// --- Form fields ---------------------------------------------------------------

export function Field({
  label,
  hint,
  errors,
  children,
}: {
  label: string
  hint?: string
  errors?: string[]
  children: (id: string, describedBy?: string) => ReactNode
}) {
  const id = useId()
  const describedBy = errors?.length ? `${id}-error` : hint ? `${id}-hint` : undefined
  return (
    <div className={`field ${errors?.length ? 'has-error' : ''}`}>
      <label htmlFor={id}>{label}</label>
      {children(id, describedBy)}
      {errors?.length ? (
        <p className="field-error" id={`${id}-error`}>
          {errors.join(' ')}
        </p>
      ) : hint ? (
        <p className="field-hint" id={`${id}-hint`}>
          {hint}
        </p>
      ) : null}
    </div>
  )
}

export function TextField({
  label,
  hint,
  errors,
  ...input
}: InputHTMLAttributes<HTMLInputElement> & { label: string; hint?: string; errors?: string[] }) {
  return (
    <Field label={label} hint={hint} errors={errors}>
      {(id, describedBy) => <input id={id} aria-describedby={describedBy} aria-invalid={!!errors?.length} {...input} />}
    </Field>
  )
}

export function SelectField({
  label,
  hint,
  errors,
  options,
  ...select
}: SelectHTMLAttributes<HTMLSelectElement> & {
  label: string
  hint?: string
  errors?: string[]
  options: { value: string; label: string }[]
}) {
  return (
    <Field label={label} hint={hint} errors={errors}>
      {(id, describedBy) => (
        <select id={id} aria-describedby={describedBy} {...select}>
          {options.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      )}
    </Field>
  )
}

export function Toggle({
  checked,
  onChange,
  label,
  disabled,
}: {
  checked: boolean
  onChange: (v: boolean) => void
  label: string
  disabled?: boolean
}) {
  return (
    <label className="toggle">
      <input
        type="checkbox"
        role="switch"
        checked={checked}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
      />
      <span className="toggle-track" aria-hidden="true" />
      <span>{label}</span>
    </label>
  )
}

export function SearchBox({
  value,
  onChange,
  placeholder,
}: {
  value: string
  onChange: (v: string) => void
  placeholder: string
}) {
  const [text, setText] = useState(value)
  useEffect(() => setText(value), [value])
  useEffect(() => {
    if (text === value) return
    const timer = window.setTimeout(() => onChange(text.trim()), 300)
    return () => window.clearTimeout(timer)
  }, [text, value, onChange])
  return (
    <label className="search">
      <MagnifyingGlass weight="light" size={18} aria-hidden="true" />
      <input
        type="search"
        value={text}
        placeholder={placeholder}
        aria-label={placeholder}
        onChange={(e) => setText(e.target.value)}
      />
    </label>
  )
}

// --- Errors ------------------------------------------------------------------

export function errorMessage(error: ApiError | null, t: ReturnType<typeof useI18n>['t']) {
  if (!error) return ''
  if (error.status === 403 && error.code === 'forbidden') return t('error_forbidden')
  if (error.status === 404) return t('not_found')
  if (error.message && !error.message.startsWith('HTTP')) return error.message
  const first = Object.values(error.fields)[0]
  return first?.join(' ') || t('error_generic')
}

export function ErrorNote({ error, onRetry }: { error: ApiError | null; onRetry?: () => void }) {
  const { t } = useI18n()
  if (!error) return null
  return (
    <div className="error-note" role="alert">
      <WarningCircle weight="light" size={20} aria-hidden="true" />
      <span>{errorMessage(error, t)}</span>
      {onRetry && (
        <button type="button" className="link" onClick={onRetry}>
          {t('retry')}
        </button>
      )}
    </div>
  )
}

// --- Layout pieces ------------------------------------------------------------

export function PageHeader({
  title,
  eyebrow,
  actions,
  children,
}: {
  title: string
  eyebrow?: string
  actions?: ReactNode
  children?: ReactNode
}) {
  return (
    <header className="page-header">
      <div>
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h1>{title}</h1>
        {children}
      </div>
      {actions && <div className="page-actions">{actions}</div>}
    </header>
  )
}

export function Tabs<T extends string>({
  value,
  onChange,
  options,
  label,
}: {
  value: T
  onChange: (v: T) => void
  options: { value: T; label: string; count?: number }[]
  label: string
}) {
  return (
    <div className="tabs" role="tablist" aria-label={label}>
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          role="tab"
          aria-selected={value === o.value}
          onClick={() => onChange(o.value)}
        >
          {o.label}
          {o.count !== undefined && <span className="count">{o.count}</span>}
        </button>
      ))}
    </div>
  )
}

export type BadgeTone = 'neutral' | 'lapis' | 'gold' | 'good' | 'bad' | 'warn'

export function Badge({ tone = 'neutral', children }: { tone?: BadgeTone; children: ReactNode }) {
  return <span className={`badge badge-${tone}`}>{children}</span>
}

export function Empty({ icon, children }: { icon?: ReactNode; children: ReactNode }) {
  return (
    <div className="empty">
      {icon}
      <p>{children}</p>
    </div>
  )
}

export function Skeleton({ rows = 6 }: { rows?: number }) {
  return (
    <div className="skeleton" aria-hidden="true">
      {Array.from({ length: rows }, (_, i) => (
        <span key={i} style={{ animationDelay: `${i * 60}ms` }} />
      ))}
    </div>
  )
}

export function Pager({
  page,
  count,
  size = 50,
  onPage,
}: {
  page: number
  count: number
  size?: number
  onPage: (p: number) => void
}) {
  const { num, lang } = useI18n()
  const pages = Math.max(1, Math.ceil(count / size))
  if (pages <= 1) return null
  const Prev = lang === 'ar' ? CaretRight : CaretLeft
  const Next = lang === 'ar' ? CaretLeft : CaretRight
  return (
    <nav className="pager" aria-label="Pages">
      <button
        type="button"
        className="icon-btn"
        disabled={page <= 1}
        onClick={() => onPage(page - 1)}
        aria-label="Previous"
      >
        <Prev weight="light" size={18} />
      </button>
      <span>
        {num(page)} / {num(pages)}
      </span>
      <button
        type="button"
        className="icon-btn"
        disabled={page >= pages}
        onClick={() => onPage(page + 1)}
        aria-label="Next"
      >
        <Next weight="light" size={18} />
      </button>
    </nav>
  )
}

/** A number tile. */
export function Stat({
  label,
  value,
  sub,
  tone,
}: {
  label: string
  value: ReactNode
  sub?: ReactNode
  tone?: 'hero' | 'alert'
}) {
  return (
    <div className={`stat ${tone ?? ''}`}>
      <span className="stat-label">{label}</span>
      <strong className="stat-value">{value}</strong>
      {sub && <span className="stat-sub">{sub}</span>}
    </div>
  )
}

/** Simple vertical bars for a daily series. */
export function Bars({
  data,
  label,
  format,
}: {
  data: { key: string; value: number; label: string }[]
  label: string
  format: (v: number) => string
}) {
  const max = Math.max(1, ...data.map((d) => d.value))
  return (
    <figure className="bars" aria-label={label}>
      <div className="bars-plot">
        {data.map((d, i) => (
          <div key={d.key} className="bar-col" title={`${d.label}: ${format(d.value)}`}>
            <span
              className="bar"
              style={{ height: `${Math.max(2, (d.value / max) * 100)}%`, animationDelay: `${i * 25}ms` }}
            />
          </div>
        ))}
      </div>
      <figcaption className="bars-axis">
        <span>{data[0]?.label}</span>
        <span>{data[data.length - 1]?.label}</span>
      </figcaption>
    </figure>
  )
}

// --- Overlays -------------------------------------------------------------------

/** A side panel for one record. Escape or the scrim closes it. */
export function Drawer({
  title,
  onClose,
  children,
  footer,
  wide,
}: {
  title: ReactNode
  onClose: () => void
  children: ReactNode
  footer?: ReactNode
  wide?: boolean
}) {
  const { t } = useI18n()
  const panel = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null
    panel.current?.focus()
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !document.querySelector('dialog[open]')) onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => {
      window.removeEventListener('keydown', onKey)
      previous?.focus()
    }
  }, [onClose])
  return (
    <div className="drawer-layer">
      <div className="scrim" onClick={onClose} aria-hidden="true" />
      <aside
        className={`drawer ${wide ? 'wide' : ''}`}
        role="dialog"
        aria-modal="true"
        aria-label={typeof title === 'string' ? title : undefined}
        tabIndex={-1}
        ref={panel}
      >
        <header className="drawer-head">
          <h2>{title}</h2>
          <button type="button" className="icon-btn" onClick={onClose} aria-label={t('close')}>
            <X weight="light" size={20} />
          </button>
        </header>
        <div className="drawer-body">{children}</div>
        {footer && <footer className="drawer-foot">{footer}</footer>}
      </aside>
    </div>
  )
}

/** A small modal form (confirmations, reasons, amounts). */
export function Modal({
  title,
  lead,
  onClose,
  children,
}: {
  title: string
  lead?: string
  onClose: () => void
  children: ReactNode
}) {
  const ref = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    const dialog = ref.current
    dialog?.showModal()
    return () => dialog?.close()
  }, [])
  return (
    <dialog ref={ref} className="modal" onCancel={(e) => (e.preventDefault(), onClose())} aria-labelledby="modal-title">
      <h2 id="modal-title">{title}</h2>
      {lead && <p className="muted">{lead}</p>}
      {children}
    </dialog>
  )
}

// --- Toasts ---------------------------------------------------------------------

const ToastContext = createContext<(text: string) => void>(() => {})
export const useToast = () => useContext(ToastContext)

export function ToastHost({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<{ id: number; text: string }[]>([])
  const show = useCallback((text: string) => {
    const id = Date.now() + Math.random()
    setToasts((all) => [...all, { id, text }])
    window.setTimeout(() => setToasts((all) => all.filter((t) => t.id !== id)), 3600)
  }, [])
  return (
    <ToastContext.Provider value={show}>
      {children}
      <div className="toasts" role="status" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className="toast">
            {t.text}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}
