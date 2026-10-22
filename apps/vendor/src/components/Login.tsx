import { ArrowLeft, ArrowRight, DeviceMobile, EnvelopeSimple, Storefront, WhatsappLogo } from '@phosphor-icons/react'
import { useState, type FormEvent } from 'react'

import { Api, ApiError, type Lang, type User } from '../lib/api'
import { useI18n } from '../lib/i18n'
import { nextStep, type Step } from '../lib/onboarding'
import { codeDigits, displayPhone, isRtl } from '../lib/strings'
import { CountryPicker, savedPhoneCountry } from './CountryPicker'
import { LanguageSwitch } from './LanguageSwitch'
import { Logo } from './Logo'
import { PasswordInput } from './PasswordInput'

interface Props {
  api: Api
  onSignedIn: (token: string, user: User, step: Step, joining: boolean) => void
  setLang: (lang: Lang) => void
}

// Once "Not now" is clicked, the password offer doesn't come back in this browser.
const OFFER_SKIPPED = 'wasel_password_offer_skipped'

function offerSkipped() {
  try {
    return localStorage.getItem(OFFER_SKIPPED) === '1'
  } catch {
    return false
  }
}

interface Pending {
  token: string
  user: User
  step: Step
}

/**
 * Sign in with a code (WhatsApp to a phone, or email to an address on the
 * account) or with a password (phone number or email). "Join Wasel as a
 * store" lets a new owner verify their number and apply. After a code
 * sign-in, someone without a password is offered one.
 */
export function Login({ api, onSignedIn, setLang }: Props) {
  const { t, error: errorMessage, lang } = useI18n()
  const rtl = isRtl(lang)
  const Forward = rtl ? ArrowLeft : ArrowRight
  const Back = rtl ? ArrowRight : ArrowLeft
  const [mode, setMode] = useState<'code' | 'password'>('code')
  const [by, setBy] = useState<'phone' | 'email'>('phone')
  const [phone, setPhone] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [country, setCountry] = useState(savedPhoneCountry)
  const [code, setCode] = useState('')
  const [sentTo, setSentTo] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [joining, setJoining] = useState(false)
  const [pending, setPending] = useState<Pending | null>(null)
  const [newPassword, setNewPassword] = useState('')

  // A new store signs up with its phone number; email and passwords come later.
  const passwordMode = mode === 'password' && !joining
  const byEmail = by === 'email' && !joining

  // Put the phone number (or email) inside the sentence, kept left-to-right.
  const [before, after] = t('codeLead', { phone: '\u0000' }).split('\u0000')

  const switchTo = (next: { mode?: 'code' | 'password'; by?: 'phone' | 'email' }) => {
    if (next.mode) setMode(next.mode)
    if (next.by) setBy(next.by)
    setError(null)
  }

  const fail = (e: unknown) => setError(e instanceof ApiError ? e.code : 'generic')

  const sendCode = async (event: FormEvent) => {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const sent = await api.requestCode(byEmail ? { email: email.trim() } : { phone }, country)
      setSentTo(sent.email ?? sent.phone)
      setCode('')
    } catch (e) {
      fail(e)
    } finally {
      setBusy(false)
    }
  }

  /** Lets in an account the portal takes; after a code, may offer a password first. */
  const finish = async (result: { token: string; user: User }, byCode: boolean) => {
    const session = new Api(result.token)
    const step = await nextStep(session, result.user, joining)
    if (step.kind === 'refused') {
      // Don't leave a usable token behind for an account the portal refuses.
      await session.logout().catch(() => {})
      setError(step.code)
      return
    }
    if (byCode && !result.user.has_password && !offerSkipped()) {
      setPending({ ...result, step })
      return
    }
    onSignedIn(result.token, result.user, step, joining)
  }

  const verify = async (value: string) => {
    // Typing the 6th digit verifies, so a quick Enter must not send it twice.
    if (value.length !== 6 || !sentTo || busy) return
    setBusy(true)
    setError(null)
    try {
      await finish(await api.verifyCode(sentTo, value, country), true)
    } catch (e) {
      fail(e)
    } finally {
      setBusy(false)
    }
  }

  const passwordSignIn = async (event: FormEvent) => {
    event.preventDefault()
    if (!password || busy) return
    setBusy(true)
    setError(null)
    try {
      await finish(await api.passwordLogin(byEmail ? email.trim() : phone, password, country), false)
    } catch (e) {
      fail(e)
    } finally {
      setBusy(false)
    }
  }

  const savePassword = async (event: FormEvent) => {
    event.preventDefault()
    if (!pending || busy) return
    setBusy(true)
    setError(null)
    try {
      const user = await new Api(pending.token).setPassword(newPassword)
      onSignedIn(pending.token, user, pending.step, joining)
    } catch (e) {
      fail(e)
    } finally {
      setBusy(false)
    }
  }

  const skipPassword = () => {
    try {
      localStorage.setItem(OFFER_SKIPPED, '1')
    } catch {
      // Private mode: the offer may come back next time.
    }
    if (pending) onSignedIn(pending.token, pending.user, pending.step, joining)
  }

  const errorLine = (id?: string) =>
    error && (
      <p className="error" id={id} role="alert">
        {errorMessage(error)}
      </p>
    )

  const phoneField = (
    <>
      <label htmlFor="phone">{t('phone')}</label>
      <div className="phone-input" dir="ltr">
        <CountryPicker value={country} onChange={(code) => (setCountry(code), setError(null))} />
        <input
          id="phone"
          type="tel"
          inputMode="tel"
          autoComplete="tel-national"
          placeholder={country === 'IQ' ? '0780 000 0999' : ''}
          value={phone}
          aria-invalid={Boolean(error)}
          aria-describedby="phone-help phone-error"
          onChange={(e) => {
            setPhone(e.target.value)
            setError(null)
          }}
        />
      </div>
    </>
  )

  const emailField = (
    <>
      <label htmlFor="email">{t('email')}</label>
      <input
        id="email"
        className="text-input"
        type="email"
        dir="ltr"
        autoComplete="email"
        placeholder={t('emailHint')}
        value={email}
        aria-invalid={Boolean(error)}
        aria-describedby="phone-help phone-error"
        onChange={(e) => {
          setEmail(e.target.value)
          setError(null)
        }}
      />
    </>
  )

  const choice = (value: 'phone' | 'email', Icon: typeof DeviceMobile, label: string) => (
    <button type="button" className="kind-tile" aria-pressed={by === value} onClick={() => switchTo({ by: value })}>
      <Icon size={22} weight="light" aria-hidden="true" />
      {label}
    </button>
  )

  let panel
  if (pending) {
    panel = (
      <form onSubmit={savePassword} noValidate>
        <h1>{t('setPasswordTitle')}</h1>
        <p className="lead">{t('setPasswordLead')}</p>
        <label htmlFor="new-password">{t('newPassword')}</label>
        <PasswordInput
          id="new-password"
          value={newPassword}
          newPassword
          autoFocus
          invalid={Boolean(error)}
          describedBy="password-help"
          onChange={(value) => (setNewPassword(value), setError(null))}
        />
        <p className="help" id="password-help">
          {t('passwordHelp')}
        </p>
        {errorLine()}
        <button className="primary cta" type="submit" disabled={busy || newPassword.length < 8}>
          {t('savePassword')}
          <span className="cta-icon" aria-hidden="true">
            <Forward size={20} weight="light" />
          </span>
        </button>
        <button type="button" className="link center" onClick={skipPassword}>
          {t('notNow')}
        </button>
      </form>
    )
  } else if (sentTo !== null) {
    panel = (
      <form onSubmit={(e) => (e.preventDefault(), verify(code))} noValidate>
        <button type="button" className="link" onClick={() => (setSentTo(null), setError(null))}>
          <Back size={18} weight="light" aria-hidden="true" />
          {t(sentTo.includes('@') ? 'changeAddress' : 'changeNumber')}
        </button>
        <h1>{t('codeTitle')}</h1>
        <p className="lead">
          {before}
          <bdi dir="ltr">{sentTo.includes('@') ? sentTo : displayPhone(sentTo)}</bdi>
          {after}
        </p>
        <label htmlFor="code">{t('code')}</label>
        <input
          id="code"
          className="code-input"
          dir="ltr"
          inputMode="numeric"
          autoComplete="one-time-code"
          autoFocus
          value={code}
          aria-invalid={Boolean(error)}
          onChange={(e) => {
            const digits = codeDigits(e.target.value)
            setCode(digits)
            setError(null)
            if (digits.length === 6) verify(digits)
          }}
        />
        {errorLine()}
        <button className="primary cta" type="submit" disabled={busy || code.length !== 6}>
          {t('confirm')}
          <span className="cta-icon" aria-hidden="true">
            <Forward size={20} weight="light" />
          </span>
        </button>
      </form>
    )
  } else {
    panel = (
      <form onSubmit={passwordMode ? passwordSignIn : sendCode} noValidate>
        <h1>{t(joining ? 'joinTitle' : 'loginTitle')}</h1>
        <p className="lead">{t(joining ? 'joinLead' : passwordMode ? 'loginLeadPassword' : 'loginLead')}</p>
        {!joining && (
          <div className="segmented login-mode" role="group" aria-label={t('loginTitle')}>
            <button type="button" aria-pressed={mode === 'code'} onClick={() => switchTo({ mode: 'code' })}>
              {t('byCode')}
            </button>
            <button type="button" aria-pressed={mode === 'password'} onClick={() => switchTo({ mode: 'password' })}>
              {t('byPassword')}
            </button>
          </div>
        )}
        {!joining && (
          <fieldset className="login-by">
            <legend>{passwordMode ? t('phone') + ' / ' + t('email') : t('sendBy')}</legend>
            <div className="kind-tiles">
              {choice('phone', passwordMode ? DeviceMobile : WhatsappLogo, passwordMode ? t('phone') : t('whatsapp'))}
              {choice('email', EnvelopeSimple, t('email'))}
            </div>
          </fieldset>
        )}
        {byEmail ? emailField : phoneField}
        {!passwordMode && (
          <p className="help" id="phone-help">
            {byEmail ? t('emailCodeHelp') : t('phoneHelp')}
          </p>
        )}
        {passwordMode && (
          <>
            <label htmlFor="password">{t('password')}</label>
            <PasswordInput
              id="password"
              value={password}
              invalid={Boolean(error)}
              describedBy="phone-error"
              onChange={(value) => (setPassword(value), setError(null))}
            />
          </>
        )}
        {errorLine('phone-error')}
        <button className="primary cta" type="submit" disabled={busy}>
          {t(passwordMode ? 'signIn' : 'sendCode')}
          <span className="cta-icon" aria-hidden="true">
            <Forward size={20} weight="light" />
          </span>
        </button>
        {passwordMode && (
          <button type="button" className="link center" onClick={() => switchTo({ mode: 'code' })}>
            {t('forgotPassword')}
          </button>
        )}
        <div className="join-switch">
          <span className="muted">{t(joining ? 'haveStore' : 'newToWasel')}</span>
          <button
            type="button"
            className="link"
            onClick={() => {
              setJoining(!joining)
              setError(null)
            }}
          >
            {!joining && <Storefront size={18} weight="light" aria-hidden="true" />}
            {t(joining ? 'backToLogin' : 'joinAsStore')}
          </button>
        </div>
      </form>
    )
  }

  return (
    <main className="login">
      <aside className="login-brand glaze on-glaze">
        <p className="eyebrow">{t('portalTag')}</p>
        <div className="brand-copy" aria-hidden="true">
          <Logo className="wordmark" />
          <span className="gold-rule" />
          <p>{t('brandLine')}</p>
        </div>
      </aside>
      <section className="login-panel">
        <LanguageSwitch setLang={setLang} />
        <div className="bezel">
          <div className="plate">{panel}</div>
        </div>
      </section>
    </main>
  )
}
