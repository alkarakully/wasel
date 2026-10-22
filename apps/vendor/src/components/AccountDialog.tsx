import { DeviceMobile, EnvelopeSimple, Key, Trash, X } from '@phosphor-icons/react'
import { useEffect, useRef, useState, type FormEvent } from 'react'

import { Api, ApiError, type User } from '../lib/api'
import { useI18n } from '../lib/i18n'
import { codeDigits, displayPhone } from '../lib/strings'
import { PasswordInput } from './PasswordInput'

interface Props {
  api: Api
  user: User
  onChanged: (user: User) => void
  onClose: () => void
}

type Editing = null | 'email' | 'password'
type Saved = 'emailSaved' | 'passwordSaved'

/** The signed-in person's ways to sign in: phone, an email (confirmed with a code) and a password. */
export function AccountDialog({ api, user, onChanged, onClose }: Props) {
  const { t, error: errorMessage } = useI18n()
  const dialog = useRef<HTMLDialogElement>(null)
  const [editing, setEditing] = useState<Editing>(null)
  const [email, setEmail] = useState('')
  const [sentTo, setSentTo] = useState<string | null>(null)
  const [code, setCode] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<Saved | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    dialog.current?.showModal()
  }, [])

  const run = async (action: () => Promise<void>) => {
    if (busy) return
    setBusy(true)
    setError(null)
    try {
      await action()
    } catch (e) {
      setError(e instanceof ApiError ? e.code : 'generic')
    } finally {
      setBusy(false)
    }
  }

  const done = (updated: User, message: Saved) => {
    onChanged(updated)
    setEditing(null)
    setSentTo(null)
    setEmail('')
    setCode('')
    setPassword('')
    setNotice(message)
  }

  const sendEmailCode = (event: FormEvent) => {
    event.preventDefault()
    run(async () => {
      const sent = await api.addEmail(email.trim().toLowerCase())
      setSentTo(sent.email)
    })
  }

  const confirmEmail = (value: string) => run(async () => done(await api.confirmEmail(sentTo!, value), 'emailSaved'))

  const savePassword = (event: FormEvent) => {
    event.preventDefault()
    run(async () => done(await api.setPassword(password), 'passwordSaved'))
  }

  const removeEmail = () => run(async () => onChanged(await api.removeEmail()))

  const open = (what: Editing) => {
    setEditing(what)
    setError(null)
    setNotice(null)
  }

  return (
    <dialog ref={dialog} className="dialog account" aria-labelledby="account-title" onCancel={onClose}>
      <div className="form-head">
        <h2 id="account-title">{t('account')}</h2>
        <button type="button" className="icon-button" onClick={onClose} title={t('close')}>
          <X size={18} weight="light" aria-hidden="true" />
          <span className="sr-only">{t('close')}</span>
        </button>
      </div>

      <ul className="account-rows">
        <li>
          <DeviceMobile size={22} weight="light" aria-hidden="true" />
          <span className="grow">
            <span className="muted small">{t('accountPhone')}</span>
            <bdi dir="ltr">{displayPhone(user.phone)}</bdi>
          </span>
        </li>
        <li>
          <EnvelopeSimple size={22} weight="light" aria-hidden="true" />
          <span className="grow">
            <span className="muted small">{t('accountEmail')}</span>
            {user.email ? <bdi dir="ltr">{user.email}</bdi> : <span className="muted">{t('noEmail')}</span>}
          </span>
          <button type="button" className="link" onClick={() => open('email')}>
            {t(user.email ? 'changeEmail' : 'addEmail')}
          </button>
          {user.email && (
            <button type="button" className="icon-button" title={t('removeEmail')} onClick={removeEmail}>
              <Trash size={18} weight="light" aria-hidden="true" />
              <span className="sr-only">{t('removeEmail')}</span>
            </button>
          )}
        </li>
        <li>
          <Key size={22} weight="light" aria-hidden="true" />
          <span className="grow">
            <span className="muted small">{t('accountPassword')}</span>
            <span className={user.has_password ? '' : 'muted'}>
              {t(user.has_password ? 'passwordSet' : 'passwordNotSet')}
            </span>
          </span>
          <button type="button" className="link" onClick={() => open('password')}>
            {t(user.has_password ? 'changePassword' : 'setPassword')}
          </button>
        </li>
      </ul>

      {editing === 'email' && sentTo === null && (
        <form className="account-form" onSubmit={sendEmailCode} noValidate>
          <label htmlFor="new-email">{t('addEmail')}</label>
          <input
            id="new-email"
            className="text-input"
            type="email"
            dir="ltr"
            autoComplete="email"
            autoFocus
            placeholder={t('emailHint')}
            value={email}
            onChange={(e) => (setEmail(e.target.value), setError(null))}
          />
          {error && (
            <p className="error" role="alert">
              {errorMessage(error)}
            </p>
          )}
          <button type="submit" className="primary" disabled={busy || !email.includes('@')}>
            {t('sendCode')}
          </button>
        </form>
      )}
      {editing === 'email' && sentTo !== null && (
        <form className="account-form" onSubmit={(e) => (e.preventDefault(), confirmEmail(code))} noValidate>
          <p className="muted">{t('emailCodeSent', { email: sentTo })}</p>
          <label htmlFor="email-code">{t('code')}</label>
          <input
            id="email-code"
            className="code-input"
            dir="ltr"
            inputMode="numeric"
            autoComplete="one-time-code"
            autoFocus
            value={code}
            onChange={(e) => {
              const digits = codeDigits(e.target.value)
              setCode(digits)
              setError(null)
              if (digits.length === 6) confirmEmail(digits)
            }}
          />
          {error && (
            <p className="error" role="alert">
              {errorMessage(error)}
            </p>
          )}
          <button type="submit" className="primary" disabled={busy || code.length !== 6}>
            {t('confirm')}
          </button>
        </form>
      )}
      {editing === 'password' && (
        <form className="account-form" onSubmit={savePassword} noValidate>
          <label htmlFor="account-password">{t('newPassword')}</label>
          <PasswordInput
            id="account-password"
            value={password}
            newPassword
            autoFocus
            describedBy="account-password-help"
            onChange={(value) => (setPassword(value), setError(null))}
          />
          <p className="help" id="account-password-help">
            {t('passwordHelp')}
          </p>
          {error && (
            <p className="error" role="alert">
              {errorMessage(error)}
            </p>
          )}
          <button type="submit" className="primary" disabled={busy || password.length < 8}>
            {t('savePassword')}
          </button>
        </form>
      )}
      {notice && (
        <p className="note success-note" role="status">
          {t(notice)}
        </p>
      )}
    </dialog>
  )
}
