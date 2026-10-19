import { ArrowLeft, ArrowRight, Copy, ShieldCheck } from '@phosphor-icons/react'
import QRCode from 'qrcode'
import { useEffect, useState, type FormEvent } from 'react'

import { api, type Lang, type Me } from '../lib/api'
import { useI18n } from '../lib/i18n'
import { useAction } from '../lib/useLoad'
import { LanguageSwitch } from './LanguageSwitch'
import { Button, ErrorNote, TextField } from './ui'
import { Logo } from './Logo'

type Step = { kind: 'password' } | { kind: 'code' } | { kind: 'setup'; secret: string; uri: string }

/** Email and password, then an authenticator code (set up on first sign-in). */
export function SignIn({ onSignedIn, setLang }: { onSignedIn: (me: Me) => void; setLang: (l: Lang) => void }) {
  const { t, lang } = useI18n()
  const [step, setStep] = useState<Step>({ kind: 'password' })
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [code, setCode] = useState('')
  const { busy, error, run, clear } = useAction()
  const Arrow = lang === 'ar' ? ArrowLeft : ArrowRight

  async function submitPassword(e: FormEvent) {
    e.preventDefault()
    const result = await run(() =>
      api<{ next: 'code' } | { next: 'setup'; secret: string; uri: string }>('auth/login/', {
        method: 'POST',
        body: { email, password },
      }),
    )
    if (!result) return
    setPassword('')
    setCode('')
    setStep(result.next === 'setup' ? { kind: 'setup', secret: result.secret, uri: result.uri } : { kind: 'code' })
  }

  async function submitCode(e: FormEvent) {
    e.preventDefault()
    const result = await run(() => api<{ user: Me }>('auth/verify/', { method: 'POST', body: { code } }))
    if (result) onSignedIn(result.user)
    else setCode('')
  }

  return (
    <div className="signin">
      <section className="signin-brand glaze" aria-hidden="true">
        <Logo className="wordmark" />
        <span className="gold-rule" />
        <p className="signin-tag">{t('app_name')}</p>
      </section>
      <section className="signin-panel">
        <div className="signin-top">
          <LanguageSwitch setLang={setLang} />
        </div>
        <div className="signin-card">
          {step.kind === 'password' ? (
            <form onSubmit={submitPassword} className="stack">
              <h1>{t('sign_in_title')}</h1>
              <p className="muted">{t('sign_in_lead')}</p>
              <TextField
                label={t('email')}
                type="email"
                autoComplete="username"
                dir="ltr"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
              <TextField
                label={t('password')}
                type="password"
                autoComplete="current-password"
                dir="ltr"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              <ErrorNote error={error} />
              <Button tone="primary" type="submit" busy={busy} className="cta">
                {t('continue')}
                <span className="cta-icon">
                  <Arrow weight="light" size={18} />
                </span>
              </Button>
            </form>
          ) : (
            <form onSubmit={submitCode} className="stack">
              <ShieldCheck weight="light" size={40} className="signin-shield" aria-hidden="true" />
              <h1>{step.kind === 'setup' ? t('setup_title') : t('code_title')}</h1>
              <p className="muted">{step.kind === 'setup' ? t('setup_lead') : t('code_lead')}</p>
              {step.kind === 'setup' && <SetupKey secret={step.secret} uri={step.uri} />}
              <TextField
                label={t('code')}
                inputMode="numeric"
                autoComplete="one-time-code"
                pattern="[0-9٠-٩ ]{6,7}"
                maxLength={7}
                dir="ltr"
                className="code-input"
                required
                autoFocus
                value={code}
                onChange={(e) => setCode(e.target.value)}
              />
              <ErrorNote error={error} />
              <Button tone="primary" type="submit" busy={busy}>
                {t('verify')}
              </Button>
              <button
                type="button"
                className="link"
                onClick={() => {
                  clear()
                  setStep({ kind: 'password' })
                }}
              >
                {t('back')}
              </button>
            </form>
          )}
        </div>
      </section>
    </div>
  )
}

function SetupKey({ secret, uri }: { secret: string; uri: string }) {
  const { t } = useI18n()
  const [svg, setSvg] = useState('')
  const [copied, setCopied] = useState(false)
  useEffect(() => {
    QRCode.toString(uri, {
      type: 'svg',
      margin: 1,
      errorCorrectionLevel: 'M',
      color: { dark: '#131f5c', light: '#ffffff' },
    })
      .then(setSvg)
      .catch(() => setSvg(''))
  }, [uri])
  const grouped = secret.match(/.{1,4}/g)?.join(' ') ?? secret
  return (
    <div className="setup">
      {svg && <div className="qr" role="img" aria-label="QR code" dangerouslySetInnerHTML={{ __html: svg }} />}
      <p className="field-hint">{t('setup_manual')}</p>
      <div className="secret">
        <code dir="ltr">{grouped}</code>
        <button
          type="button"
          className="icon-btn"
          aria-label={copied ? t('copied') : t('copy')}
          onClick={() => {
            void navigator.clipboard?.writeText(secret)
            setCopied(true)
          }}
        >
          <Copy weight="light" size={18} />
        </button>
      </div>
    </div>
  )
}
