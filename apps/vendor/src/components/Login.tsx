import { ArrowLeft, ArrowRight } from '@phosphor-icons/react'
import { useState, type FormEvent } from 'react'

import { Api, ApiError, type Lang, type User } from '../lib/api'
import { useI18n } from '../lib/i18n'
import { isRtl } from '../lib/strings'
import { LanguageSwitch } from './LanguageSwitch'

interface Props {
  api: Api
  onSignedIn: (token: string, user: User) => void
  setLang: (lang: Lang) => void
}

/** Phone number, then the 6-digit code. Only store owners get in. */
export function Login({ api, onSignedIn, setLang }: Props) {
  const { t, error: errorMessage, lang } = useI18n()
  const rtl = isRtl(lang)
  const Forward = rtl ? ArrowLeft : ArrowRight
  const Back = rtl ? ArrowRight : ArrowLeft
  const [phone, setPhone] = useState('')
  const [code, setCode] = useState('')
  const [sentTo, setSentTo] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  // Put the phone number inside the sentence, kept left-to-right.
  const [before, after] = t('codeLead', { phone: '\u0000' }).split('\u0000')

  const sendCode = async (event: FormEvent) => {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const sent = await api.requestCode(phone, 'whatsapp')
      setSentTo(sent.phone)
      setCode('')
    } catch (e) {
      setError(e instanceof ApiError ? e.code : 'generic')
    } finally {
      setBusy(false)
    }
  }

  const verify = async (value: string) => {
    if (value.length !== 6 || !sentTo) return
    setBusy(true)
    setError(null)
    try {
      const result = await api.verifyCode(sentTo, value)
      if (result.user.role !== 'vendor') {
        // Don't leave a usable token behind for an account the portal refuses.
        const check = new Api(result.token)
        await check.logout().catch(() => {})
        setError('not_vendor')
        return
      }
      onSignedIn(result.token, result.user)
    } catch (e) {
      setError(e instanceof ApiError ? e.code : 'generic')
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="login">
      <aside className="login-brand glaze on-glaze">
        <p className="eyebrow">{t('portalTag')}</p>
        <div className="brand-copy" aria-hidden="true">
          <p className="wordmark">واصل</p>
          <span className="gold-rule" />
          <p>{t('brandLine')}</p>
        </div>
      </aside>
      <section className="login-panel">
        <LanguageSwitch setLang={setLang} />
        <div className="bezel">
          <div className="plate">
            {sentTo === null ? (
              <form onSubmit={sendCode} noValidate>
                <h1>{t('loginTitle')}</h1>
                <p className="lead">{t('loginLead')}</p>
                <label htmlFor="phone">{t('phone')}</label>
                <div className="phone-input" dir="ltr">
                  <span>+964</span>
                  <input
                    id="phone"
                    type="tel"
                    inputMode="tel"
                    autoComplete="tel-national"
                    placeholder="0780 000 0999"
                    value={phone}
                    aria-invalid={Boolean(error)}
                    aria-describedby="phone-help phone-error"
                    onChange={(e) => {
                      setPhone(e.target.value)
                      setError(null)
                    }}
                  />
                </div>
                <p className="help" id="phone-help">
                  {t('phoneHelp')}
                </p>
                {error && (
                  <p className="error" id="phone-error" role="alert">
                    {errorMessage(error)}
                  </p>
                )}
                <button className="primary cta" type="submit" disabled={busy}>
                  {t('sendCode')}
                  <span className="cta-icon" aria-hidden="true">
                    <Forward size={20} weight="light" />
                  </span>
                </button>
              </form>
            ) : (
              <form onSubmit={(e) => (e.preventDefault(), verify(code))} noValidate>
                <button type="button" className="link" onClick={() => (setSentTo(null), setError(null))}>
                  <Back size={18} weight="light" aria-hidden="true" />
                  {t('changeNumber')}
                </button>
                <h1>{t('codeTitle')}</h1>
                <p className="lead">
                  {before}
                  <bdi dir="ltr">{sentTo}</bdi>
                  {after}
                </p>
                <label htmlFor="code">{t('code')}</label>
                <input
                  id="code"
                  className="code-input"
                  dir="ltr"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  maxLength={6}
                  autoFocus
                  value={code}
                  aria-invalid={Boolean(error)}
                  onChange={(e) => {
                    const digits = e.target.value.replace(/\D/g, '').slice(0, 6)
                    setCode(digits)
                    setError(null)
                    if (digits.length === 6) verify(digits)
                  }}
                />
                {error && (
                  <p className="error" role="alert">
                    {errorMessage(error)}
                  </p>
                )}
                <button className="primary cta" type="submit" disabled={busy || code.length !== 6}>
                  {t('confirm')}
                  <span className="cta-icon" aria-hidden="true">
                    <Forward size={20} weight="light" />
                  </span>
                </button>
              </form>
            )}
          </div>
        </div>
      </section>
    </main>
  )
}
