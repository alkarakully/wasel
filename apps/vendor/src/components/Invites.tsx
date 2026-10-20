import { Check, X } from '@phosphor-icons/react'
import { useState } from 'react'

import { Api, ApiError, type Invite } from '../lib/api'
import { useI18n } from '../lib/i18n'
import { storeTypeIcon } from '../lib/storeTypes'

interface Props {
  api: Api
  invites: Invite[]
  /** Called after each answer, with what was answered. */
  onAnswered: (invite: Invite, answer: 'accept' | 'decline') => void
}

/** Team invites waiting for the signed-in person: join the store, or say no. */
export function InviteList({ api, invites, onAnswered }: Props) {
  const { t, error: errorMessage } = useI18n()
  const [busy, setBusy] = useState<number | null>(null)
  const [problem, setProblem] = useState<{ id: number; code: string } | null>(null)

  const answer = async (invite: Invite, choice: 'accept' | 'decline') => {
    setBusy(invite.id)
    setProblem(null)
    try {
      await api.answerInvite(invite.id, choice)
      onAnswered(invite, choice)
    } catch (e) {
      setProblem({ id: invite.id, code: e instanceof ApiError ? e.code : 'generic' })
    } finally {
      setBusy(null)
    }
  }

  return (
    <ul className="invites">
      {invites.map((invite) => {
        const Icon = storeTypeIcon(invite.store.type)
        return (
          <li key={invite.id} className="invite">
            <span className="invite-icon glaze" aria-hidden="true">
              <Icon size={26} weight="light" />
            </span>
            <span className="grow">
              <strong>{invite.store.name}</strong>
              <span>
                {t('invitedAs', { who: invite.invited_by || t('owner'), role: t(invite.role) })}
              </span>
              <span className="muted small">{t(`role_${invite.role}_help`)}</span>
              {problem?.id === invite.id && (
                <span className="error small" role="alert">
                  {errorMessage(problem.code)}
                </span>
              )}
            </span>
            <span className="invite-actions">
              <button
                type="button"
                className="secondary"
                disabled={busy === invite.id}
                onClick={() => answer(invite, 'decline')}
                aria-label={`${t('decline')} ${invite.store.name}`}
              >
                <X size={18} weight="light" aria-hidden="true" />
                {t('decline')}
              </button>
              <button
                type="button"
                className="primary"
                disabled={busy === invite.id}
                onClick={() => answer(invite, 'accept')}
                aria-label={`${t('acceptInvite')} ${invite.store.name}`}
              >
                <Check size={18} weight="light" aria-hidden="true" />
                {t('acceptInvite')}
              </button>
            </span>
          </li>
        )
      })}
    </ul>
  )
}
