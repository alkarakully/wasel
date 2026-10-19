import { Key, ShieldCheck, ShieldSlash, UserPlus } from '@phosphor-icons/react'
import { useState, type FormEvent } from 'react'

import {
  Badge,
  Button,
  Drawer,
  Empty,
  ErrorNote,
  Modal,
  PageHeader,
  SelectField,
  Skeleton,
  TextField,
  Toggle,
  useToast,
} from '../components/ui'
import { api, type Me, type Role, type StaffRow } from '../lib/api'
import { useI18n } from '../lib/i18n'
import type { StringKey } from '../lib/strings'
import { useAction, useLoad } from '../lib/useLoad'

const ROLES: Role[] = ['admin', 'operations', 'support', 'finance', 'marketing']

export function StaffPage({ me }: { me: Me }) {
  const { t, when } = useI18n()
  const { data, error, loading, reload } = useLoad<StaffRow[]>('staff/')
  const [adding, setAdding] = useState(false)
  const [editing, setEditing] = useState<StaffRow | null>(null)

  return (
    <>
      <PageHeader
        title={t('nav_staff')}
        actions={
          <Button tone="primary" icon={<UserPlus weight="light" size={18} />} onClick={() => setAdding(true)}>
            {t('add_staff')}
          </Button>
        }
      />
      <section className="panel table-panel">
        <ErrorNote error={error} onRetry={reload} />
        {loading && !data ? (
          <Skeleton rows={4} />
        ) : data && data.length === 0 ? (
          <Empty icon={<ShieldCheck weight="light" />}>{t('nothing_here')}</Empty>
        ) : (
          data && (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>{t('name')}</th>
                    <th>{t('email')}</th>
                    <th>{t('role')}</th>
                    <th>{t('two_factor')}</th>
                    <th>{t('last_login')}</th>
                    <th>{t('status')}</th>
                  </tr>
                </thead>
                <tbody>
                  {data.map((s) => (
                    <tr key={s.id} className="clickable" onClick={() => setEditing(s)}>
                      <td>
                        <button
                          type="button"
                          className="row-link"
                          onClick={(e) => (e.stopPropagation(), setEditing(s))}
                        >
                          {s.name || '—'}
                        </button>
                        {s.user === me.id && <span className="sub">{t('you')}</span>}
                      </td>
                      <td>
                        <bdi dir="ltr">{s.email}</bdi>
                      </td>
                      <td>
                        <Badge tone={s.role === 'admin' ? 'lapis' : 'neutral'}>
                          {t(`role_${s.role}` as StringKey)}
                        </Badge>
                      </td>
                      <td>
                        {s.two_factor ? (
                          <Badge tone="good">{t('set_up')}</Badge>
                        ) : (
                          <Badge tone="warn">{t('not_set_up')}</Badge>
                        )}
                      </td>
                      <td className="muted">{when(s.last_login)}</td>
                      <td>
                        {!s.is_active ? (
                          <Badge tone="bad">{t('blocked')}</Badge>
                        ) : s.locked ? (
                          <Badge tone="warn">{t('locked')}</Badge>
                        ) : (
                          <Badge tone="good">{t('active')}</Badge>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        )}
      </section>
      {adding && <AddStaff onClose={() => setAdding(false)} onAdded={() => (setAdding(false), void reload())} />}
      {editing && (
        <EditStaff
          key={editing.id}
          staff={editing}
          isMe={editing.user === me.id}
          onClose={() => setEditing(null)}
          onSaved={(row) => {
            setEditing(row)
            void reload()
          }}
        />
      )}
    </>
  )
}

function AddStaff({ onClose, onAdded }: { onClose: () => void; onAdded: () => void }) {
  const { t } = useI18n()
  const toast = useToast()
  const { busy, error, run } = useAction()
  const [form, setForm] = useState({ name: '', email: '', role: 'support', password: '' })
  const set = (key: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm((f) => ({ ...f, [key]: e.target.value }))
  const errors = error?.fields ?? {}
  async function submit(e: FormEvent) {
    e.preventDefault()
    if (await run(() => api('staff/', { method: 'POST', body: form }))) {
      toast(t('saved'))
      onAdded()
    }
  }
  return (
    <Drawer title={t('add_staff')} onClose={onClose}>
      <form className="stack" onSubmit={submit}>
        <TextField label={t('name')} required value={form.name} onChange={set('name')} errors={errors.name} />
        <TextField
          label={t('email')}
          type="email"
          dir="ltr"
          autoComplete="off"
          required
          value={form.email}
          onChange={set('email')}
          errors={errors.email}
        />
        <SelectField
          label={t('role')}
          value={form.role}
          onChange={set('role')}
          options={ROLES.map((r) => ({ value: r, label: t(`role_${r}` as StringKey) }))}
        />
        <TextField
          label={t('password')}
          type="password"
          dir="ltr"
          autoComplete="new-password"
          minLength={10}
          required
          hint={t('temp_password_hint')}
          value={form.password}
          onChange={set('password')}
          errors={errors.password}
        />
        {Object.keys(errors).length === 0 && <ErrorNote error={error} />}
        <Button tone="primary" type="submit" busy={busy}>
          {t('add_staff')}
        </Button>
      </form>
    </Drawer>
  )
}

function EditStaff({
  staff,
  isMe,
  onClose,
  onSaved,
}: {
  staff: StaffRow
  isMe: boolean
  onClose: () => void
  onSaved: (row: StaffRow) => void
}) {
  const { t } = useI18n()
  const toast = useToast()
  const action = useAction()
  const [passwordOpen, setPasswordOpen] = useState(false)

  async function patch(body: Partial<Pick<StaffRow, 'role' | 'is_active' | 'name'>>) {
    const row = await action.run(() => api<StaffRow>(`staff/${staff.id}/`, { method: 'PATCH', body }))
    if (row) {
      toast(t('saved'))
      onSaved(row)
    }
  }
  async function resetTwoFactor() {
    const row = await action.run(() =>
      api<StaffRow>(`staff/${staff.id}/reset/`, { method: 'POST', body: { what: 'two_factor' } }),
    )
    if (row) {
      toast(t('saved'))
      onSaved(row)
    }
  }

  return (
    <Drawer title={staff.name || staff.email} onClose={onClose}>
      <div className="stack">
        <p className="muted">
          <bdi dir="ltr">{staff.email}</bdi>
        </p>
        <SelectField
          label={t('role')}
          value={staff.role}
          disabled={isMe || action.busy}
          onChange={(e) => patch({ role: e.target.value as Role })}
          options={ROLES.map((r) => ({ value: r, label: t(`role_${r}` as StringKey) }))}
        />
        <Toggle
          label={staff.is_active ? t('active') : t('blocked')}
          checked={staff.is_active}
          disabled={isMe || action.busy}
          onChange={(v) => patch({ is_active: v })}
        />
        <ErrorNote error={action.error} />
        {!isMe && (
          <section className="stack">
            <h3>{t('two_factor')}</h3>
            <p className="muted">{staff.two_factor ? t('reset_2fa_lead') : t('not_set_up')}</p>
            <div className="row-start">
              <Button
                icon={<ShieldSlash weight="light" size={18} />}
                busy={action.busy}
                disabled={!staff.two_factor}
                onClick={resetTwoFactor}
              >
                {t('reset_2fa')}
              </Button>
              <Button icon={<Key weight="light" size={18} />} onClick={() => setPasswordOpen(true)}>
                {t('set_password')}
              </Button>
            </div>
          </section>
        )}
      </div>
      {passwordOpen && (
        <SetPassword
          staffId={staff.id}
          onClose={() => setPasswordOpen(false)}
          onDone={(row) => {
            setPasswordOpen(false)
            toast(t('saved'))
            onSaved(row)
          }}
        />
      )}
    </Drawer>
  )
}

function SetPassword({
  staffId,
  onClose,
  onDone,
}: {
  staffId: number
  onClose: () => void
  onDone: (row: StaffRow) => void
}) {
  const { t } = useI18n()
  const { busy, error, run } = useAction()
  const [password, setPassword] = useState('')
  async function submit(e: FormEvent) {
    e.preventDefault()
    const row = await run(() =>
      api<StaffRow>(`staff/${staffId}/reset/`, { method: 'POST', body: { what: 'password', password } }),
    )
    if (row) onDone(row)
  }
  return (
    <Modal title={t('set_password')} onClose={onClose}>
      <form className="stack" onSubmit={submit}>
        <TextField
          label={t('new_password')}
          type="password"
          dir="ltr"
          autoComplete="new-password"
          minLength={10}
          required
          autoFocus
          hint={t('temp_password_hint')}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          errors={error?.fields.password}
        />
        {!error?.fields.password && <ErrorNote error={error} />}
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
