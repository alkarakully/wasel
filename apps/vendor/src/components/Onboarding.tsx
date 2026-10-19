import { ArrowClockwise, HourglassMedium, SealCheck, SignOut, WarningCircle } from '@phosphor-icons/react'
import { useEffect, useState, type ReactNode } from 'react'

import { Api, type ApplicationInput, type Invite, type Lang, type StoreApplication, type User } from '../lib/api'
import { useI18n } from '../lib/i18n'
import { InviteList } from './Invites'
import { LanguageSwitch } from './LanguageSwitch'
import { StoreForm } from './StoreForm'
import { Logo } from './Logo'

interface ShellProps {
  setLang: (lang: Lang) => void
  onLogout: () => void
  wide?: boolean
  children: ReactNode
}

/** The login page's frame (brand panel and plate) for the steps before the portal. */
function Shell({ setLang, onLogout, wide, children }: ShellProps) {
  const { t } = useI18n()
  return (
    <main className="login onboarding">
      <aside className="login-brand glaze on-glaze">
        <p className="eyebrow">{t('portalTag')}</p>
        <div className="brand-copy" aria-hidden="true">
          <Logo className="wordmark" />
          <span className="gold-rule" />
          <p>{t('joinBrandLine')}</p>
        </div>
      </aside>
      <section className={`login-panel ${wide ? 'wide' : ''}`}>
        <div className="panel-tools">
          <button type="button" className="link" onClick={onLogout}>
            <SignOut size={18} weight="light" aria-hidden="true" />
            {t('logout')}
          </button>
          <LanguageSwitch setLang={setLang} />
        </div>
        <div className="bezel">
          <div className="plate">{children}</div>
        </div>
      </section>
    </main>
  )
}

interface StepProps {
  api: Api
  user: User
  setLang: (lang: Lang) => void
  onLogout: () => void
  /** Something changed (applied, answered an invite, got approved): work out the next step. */
  onDone: () => void
}

/** Invites first: the person joins (or turns down) the stores that asked them. */
export function InvitesStep({ invites, ...props }: StepProps & { invites: Invite[] }) {
  const { t } = useI18n()
  const [left, setLeft] = useState(invites)
  return (
    <Shell setLang={props.setLang} onLogout={props.onLogout}>
      <h1>{t('invitesTitle')}</h1>
      <p className="lead">{t('invitesLead')}</p>
      <InviteList
        api={props.api}
        invites={left}
        onAnswered={(invite) => {
          const rest = left.filter((i) => i.id !== invite.id)
          setLeft(rest)
          if (!rest.length) props.onDone()
        }}
      />
    </Shell>
  )
}

/** Joining Wasel: the owner's name and their first store. */
export function ApplyStep({ from, ...props }: StepProps & { from?: StoreApplication | null }) {
  const { t } = useI18n()
  const submit = async (input: ApplicationInput) => {
    await props.api.apply(input)
    props.onDone()
  }
  return (
    <Shell setLang={props.setLang} onLogout={props.onLogout} wide>
      <h1>{t('applyTitle')}</h1>
      <p className="lead">{t('applyLead')}</p>
      <StoreForm mode="first" from={from} askName={!props.user.name} onSubmit={submit} />
    </Shell>
  )
}

const RECHECK_MS = 30000

/** The store is with Wasel for review; checks back by itself and when the tab comes back. */
export function WaitingStep({
  applications,
  canApply,
  ...props
}: StepProps & { applications: StoreApplication[]; canApply: boolean }) {
  const { t } = useI18n()
  const [retrying, setRetrying] = useState<StoreApplication | null>(null)
  const latest = applications[0]
  const pending = applications.some((a) => a.status === 'pending')
  const { onDone } = props

  useEffect(() => {
    if (!pending) return
    const timer = setInterval(onDone, RECHECK_MS)
    const onVisible = () => document.visibilityState === 'visible' && onDone()
    document.addEventListener('visibilitychange', onVisible)
    return () => {
      clearInterval(timer)
      document.removeEventListener('visibilitychange', onVisible)
    }
  }, [pending, onDone])

  if (retrying) return <ApplyStep {...props} from={retrying} />

  return (
    <Shell setLang={props.setLang} onLogout={props.onLogout}>
      {pending ? (
        <div className="waiting-state">
          <span className="status-badge pending" aria-hidden="true">
            <HourglassMedium size={34} weight="light" />
          </span>
          <h1>{t('waitingTitle')}</h1>
          <p className="lead">{t('waitingLead', { phone: '⁦' + props.user.phone + '⁩' })}</p>
        </div>
      ) : (
        <div className="waiting-state">
          <span className="status-badge rejected" aria-hidden="true">
            <WarningCircle size={34} weight="light" />
          </span>
          <h1>{t('rejectedTitle')}</h1>
          <p className="lead">{t('rejectedLead')}</p>
        </div>
      )}
      <ul className="applications">
        {applications.map((app) => (
          <li key={app.id}>
            <span className="grow">
              <strong>{app.name}</strong>
              <span className="muted small">{app.address}</span>
              {app.status === 'rejected' && app.rejection_reason && (
                <span className="reason">{t('rejectedBecause', { reason: app.rejection_reason })}</span>
              )}
            </span>
            <StatusChip status={app.status} />
          </li>
        ))}
      </ul>
      <div className="actions">
        {pending ? (
          <button type="button" className="secondary" onClick={onDone}>
            <ArrowClockwise size={18} weight="light" aria-hidden="true" />
            {t('checkAgain')}
          </button>
        ) : (
          canApply && (
            <button type="button" className="primary" onClick={() => setRetrying(latest)}>
              {t('applyAgain')}
            </button>
          )
        )}
      </div>
    </Shell>
  )
}

export function StatusChip({ status }: { status: StoreApplication['status'] }) {
  const { t } = useI18n()
  const Icon = status === 'approved' ? SealCheck : status === 'pending' ? HourglassMedium : WarningCircle
  return (
    <span className={`status-chip ${status}`}>
      <Icon size={16} weight="light" aria-hidden="true" />
      {t(`app_${status}`)}
    </span>
  )
}
