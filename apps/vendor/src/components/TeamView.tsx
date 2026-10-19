import { EnvelopeSimple, PaperPlaneTilt, Trash, UserCircle, X } from '@phosphor-icons/react'
import { useCallback, useEffect, useState, type FormEvent } from 'react'

import { Api, ApiError, type Team, type TeamInvite, type TeamMember } from '../lib/api'
import { useI18n } from '../lib/i18n'

interface Props {
  api: Api
  storeId: number
  myUserId: number
  onError: (error: unknown) => void
}

type Role = TeamMember['role']

/** The owner invites managers and cashiers by phone; they join once they accept at their next sign-in. */
export function TeamView({ api, storeId, myUserId, onError }: Props) {
  const { t, error: errorMessage } = useI18n()
  const [team, setTeam] = useState<Team | null>(null)
  const [phone, setPhone] = useState('')
  const [name, setName] = useState('')
  const [role, setRole] = useState<Role>('cashier')
  const [problem, setProblem] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [sentTo, setSentTo] = useState<string | null>(null)

  const load = useCallback(() => {
    api.team(storeId).then(setTeam, onError)
  }, [api, storeId, onError])
  useEffect(load, [load])

  const add = async (event: FormEvent) => {
    event.preventDefault()
    setBusy(true)
    setProblem(null)
    setSentTo(null)
    try {
      const invite = await api.addMember(storeId, { phone, name, role })
      setSentTo(invite.phone)
      setPhone('')
      setName('')
      load()
    } catch (e) {
      setProblem(e instanceof ApiError ? e.code : 'generic')
    } finally {
      setBusy(false)
    }
  }

  const changeRole = async (member: TeamMember, next: Role) => {
    try {
      await api.setMemberRole(storeId, member.id, next)
      load()
    } catch (e) {
      onError(e)
    }
  }

  const cancelInvite = async (invite: TeamInvite) => {
    try {
      await api.cancelInvite(storeId, invite.id)
      load()
    } catch (e) {
      onError(e)
    }
  }

  const remove = async (member: TeamMember) => {
    try {
      await api.removeMember(storeId, member.id)
      load()
    } catch (e) {
      onError(e)
    }
  }

  return (
    <div className="team">
      <section className="plate-card">
        <h2>{t('team')}</h2>
        <p className="muted small">{t('teamHelp')}</p>
        <ul className="people">
          {team && (
            <li>
              <UserCircle size={36} weight="light" aria-hidden="true" />
              <span className="grow">
                <strong>{team.owner.name || team.owner.phone}</strong>
                <span className="muted" dir="ltr">
                  {team.owner.phone}
                </span>
              </span>
              <span className="role-chip owner">
                {t('owner')}
                {team.owner.user === myUserId && ` · ${t('you')}`}
              </span>
            </li>
          )}
          {team?.members.map((member) => (
            <li key={member.id}>
              <UserCircle size={36} weight="light" aria-hidden="true" />
              <span className="grow">
                <strong>{member.name || member.phone}</strong>
                <span className="muted" dir="ltr">
                  {member.phone}
                </span>
              </span>
              <select
                aria-label={`${t('role')} ${member.name || member.phone}`}
                value={member.role}
                onChange={(e) => changeRole(member, e.target.value as Role)}
              >
                <option value="manager">{t('manager')}</option>
                <option value="cashier">{t('cashier')}</option>
              </select>
              <button
                type="button"
                className="icon-button danger-icon"
                title={t('removeMember')}
                onClick={() => remove(member)}
              >
                <Trash size={18} weight="light" aria-hidden="true" />
                <span className="sr-only">
                  {t('removeMember')} {member.name || member.phone}
                </span>
              </button>
            </li>
          ))}
          {team?.invites.map((invite) => (
            <li key={`invite-${invite.id}`} className="invited">
              <EnvelopeSimple size={36} weight="light" aria-hidden="true" />
              <span className="grow">
                <strong>{invite.name || invite.phone}</strong>
                <span className="muted" dir="ltr">
                  {invite.phone}
                </span>
              </span>
              <span className="role-chip invited-chip">
                {t('invitedChip', { role: t(invite.role) })}
              </span>
              <button
                type="button"
                className="icon-button danger-icon"
                title={t('cancelInvite')}
                onClick={() => cancelInvite(invite)}
              >
                <X size={18} weight="light" aria-hidden="true" />
                <span className="sr-only">
                  {t('cancelInvite')} {invite.name || invite.phone}
                </span>
              </button>
            </li>
          ))}
        </ul>
      </section>

      <form className="plate-card add-person" onSubmit={add}>
        <h2>{t('addPersonTitle')}</h2>
        <div className="form-grid">
          <label>
            {t('phone')}
            <div className="phone-input" dir="ltr">
              <span>+964</span>
              <input
                inputMode="tel"
                aria-label={t('phone')}
                placeholder="0780 000 0000"
                required
                value={phone}
                onChange={(e) => {
                  setPhone(e.target.value)
                  setProblem(null)
                }}
              />
            </div>
          </label>
          <label>
            {t('personName')}
            <input className="text-input" value={name} onChange={(e) => setName(e.target.value)} />
          </label>
        </div>
        <fieldset className="roles">
          <legend>{t('role')}</legend>
          {(['cashier', 'manager'] as const).map((option) => (
            <label key={option} className="radio">
              <input type="radio" name="role" checked={role === option} onChange={() => setRole(option)} />
              <span>
                <strong>{t(option)}</strong>
                <span className="muted small">{t(`role_${option}_help` as 'role_cashier_help')}</span>
              </span>
            </label>
          ))}
        </fieldset>
        {problem && (
          <p className="error" role="alert">
            {errorMessage(problem)}
          </p>
        )}
        {sentTo && (
          <p className="note success-note" role="status">
            {t('inviteSent', { phone: '\u2066' + sentTo + '\u2069' })}
          </p>
        )}
        <div className="actions">
          <button type="submit" className="primary" disabled={busy || !phone.trim()}>
            <PaperPlaneTilt size={20} weight="light" aria-hidden="true" />
            {t('addPerson')}
          </button>
        </div>
      </form>
    </div>
  )
}
