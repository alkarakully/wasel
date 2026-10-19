import {
  ChartBar,
  ClipboardText,
  Gauge,
  Key,
  Megaphone,
  Money,
  Receipt,
  ShieldCheck,
  SignOut,
  Storefront,
  UsersThree,
  UserCircle,
  List,
  X,
} from '@phosphor-icons/react'
import { useState, type FormEvent, type ReactNode } from 'react'

import { api, type Area, type Lang, type Me } from '../lib/api'
import { useI18n } from '../lib/i18n'
import { navigate } from '../lib/router'
import type { StringKey } from '../lib/strings'
import { useAction } from '../lib/useLoad'
import { LanguageSwitch } from './LanguageSwitch'
import { Button, ErrorNote, Modal, TextField, useToast } from './ui'

export const SECTIONS: { area: Area; path: string; label: StringKey; icon: ReactNode; group: StringKey }[] = [
  { area: 'overview', path: '', label: 'nav_overview', icon: <Gauge weight="light" />, group: 'group_operate' },
  { area: 'orders', path: 'orders', label: 'nav_orders', icon: <Receipt weight="light" />, group: 'group_operate' },
  { area: 'stores', path: 'stores', label: 'nav_stores', icon: <Storefront weight="light" />, group: 'group_operate' },
  { area: 'people', path: 'people', label: 'nav_people', icon: <UsersThree weight="light" />, group: 'group_operate' },
  { area: 'money', path: 'money', label: 'nav_money', icon: <Money weight="light" />, group: 'group_grow' },
  { area: 'reports', path: 'reports', label: 'nav_reports', icon: <ChartBar weight="light" />, group: 'group_grow' },
  {
    area: 'marketing',
    path: 'marketing',
    label: 'nav_marketing',
    icon: <Megaphone weight="light" />,
    group: 'group_grow',
  },
  { area: 'staff', path: 'team', label: 'nav_staff', icon: <ShieldCheck weight="light" />, group: 'group_control' },
  { area: 'audit', path: 'audit', label: 'nav_audit', icon: <ClipboardText weight="light" />, group: 'group_control' },
]

// Areas some role can change; "view only" is shown only there.
const CHANGEABLE: Area[] = ['orders', 'stores', 'people', 'money', 'marketing', 'staff']

export function Shell({
  me,
  section,
  setLang,
  onSignOut,
  children,
}: {
  me: Me
  section: string
  setLang: (l: Lang) => void
  onSignOut: () => void
  children: ReactNode
}) {
  const { t } = useI18n()
  const [menuOpen, setMenuOpen] = useState(false)
  const [passwordOpen, setPasswordOpen] = useState(false)
  const visible = SECTIONS.filter((s) => me.areas[s.area])
  const groups = [...new Set(visible.map((s) => s.group))]

  return (
    <div className={`shell ${menuOpen ? 'menu-open' : ''}`}>
      <aside className="sidebar" aria-label={t('app_name')}>
        <div className="sidebar-brand">
          <span className="wordmark small">واصل</span>
          <span className="sidebar-tag">{t('app_name')}</span>
          <button
            type="button"
            className="icon-btn menu-close"
            onClick={() => setMenuOpen(false)}
            aria-label={t('close')}
          >
            <X weight="light" size={20} />
          </button>
        </div>
        <nav className="nav">
          {groups.map((group) => (
            <div key={group} className="nav-group">
              <p className="nav-group-label">{t(group)}</p>
              {visible
                .filter((s) => s.group === group)
                .map((s) => (
                  <a
                    key={s.area}
                    href={`${import.meta.env.BASE_URL}${s.path}`}
                    aria-current={section === s.path ? 'page' : undefined}
                    onClick={(e) => {
                      if (e.metaKey || e.ctrlKey) return
                      e.preventDefault()
                      setMenuOpen(false)
                      navigate(`/${s.path}`)
                    }}
                  >
                    {s.icon}
                    <span>{t(s.label)}</span>
                    {me.areas[s.area] === 'read' && CHANGEABLE.includes(s.area) && (
                      <span className="nav-ro">{t('read_only')}</span>
                    )}
                  </a>
                ))}
            </div>
          ))}
        </nav>
        <div className="sidebar-foot">
          <div className="me">
            <UserCircle weight="light" size={32} aria-hidden="true" />
            <div>
              <strong>{me.name || me.email}</strong>
              <span>{t(`role_${me.role}` as StringKey)}</span>
            </div>
          </div>
          <div className="me-actions">
            <button
              type="button"
              className="icon-btn"
              onClick={() => setPasswordOpen(true)}
              aria-label={t('change_password')}
              title={t('change_password')}
            >
              <Key weight="light" size={18} />
            </button>
            <button
              type="button"
              className="icon-btn"
              onClick={onSignOut}
              aria-label={t('sign_out')}
              title={t('sign_out')}
            >
              <SignOut weight="light" size={18} />
            </button>
          </div>
        </div>
      </aside>
      <div className="main">
        <div className="topbar">
          <button type="button" className="icon-btn menu-open-btn" onClick={() => setMenuOpen(true)} aria-label="Menu">
            <List weight="light" size={20} />
          </button>
          <span className="topbar-spacer" />
          <LanguageSwitch setLang={setLang} />
        </div>
        <main className="content">{children}</main>
      </div>
      {passwordOpen && <PasswordDialog onClose={() => setPasswordOpen(false)} />}
    </div>
  )
}

function PasswordDialog({ onClose }: { onClose: () => void }) {
  const { t } = useI18n()
  const toast = useToast()
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const { busy, error, run } = useAction()
  async function submit(e: FormEvent) {
    e.preventDefault()
    const ok = await run(() => api('auth/password/', { method: 'POST', body: { current, new: next } }).then(() => true))
    if (ok) {
      toast(t('password_changed'))
      onClose()
    }
  }
  return (
    <Modal title={t('change_password')} onClose={onClose}>
      <form onSubmit={submit} className="stack">
        <TextField
          label={t('current_password')}
          type="password"
          autoComplete="current-password"
          dir="ltr"
          required
          value={current}
          onChange={(e) => setCurrent(e.target.value)}
        />
        <TextField
          label={t('new_password')}
          type="password"
          autoComplete="new-password"
          dir="ltr"
          minLength={10}
          required
          hint={t('temp_password_hint')}
          value={next}
          onChange={(e) => setNext(e.target.value)}
        />
        <ErrorNote error={error} />
        <div className="row-end">
          <Button onClick={onClose}>{t('cancel')}</Button>
          <Button tone="primary" type="submit" busy={busy}>
            {t('save')}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
