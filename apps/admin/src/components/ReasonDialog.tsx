import { useState, type FormEvent } from 'react'

import type { ApiError } from '../lib/api'
import { useI18n } from '../lib/i18n'
import { Button, ErrorNote, Field, Modal } from './ui'

/** Ask for a reason before a change that needs one (it lands in the audit log). */
export function ReasonDialog({
  title,
  lead,
  confirm,
  danger,
  hint,
  busy,
  error,
  onSubmit,
  onClose,
}: {
  title: string
  lead?: string
  confirm: string
  danger?: boolean
  hint?: string
  busy: boolean
  error: ApiError | null
  onSubmit: (reason: string) => void
  onClose: () => void
}) {
  const { t } = useI18n()
  const [reason, setReason] = useState('')
  function submit(e: FormEvent) {
    e.preventDefault()
    if (reason.trim()) onSubmit(reason.trim())
  }
  return (
    <Modal title={title} lead={lead} onClose={onClose}>
      <form onSubmit={submit} className="stack">
        <Field label={t('reason')} hint={hint ?? t('reason_hint')} errors={error?.fields.reason}>
          {(id, describedBy) => (
            <textarea
              id={id}
              aria-describedby={describedBy}
              rows={3}
              maxLength={255}
              required
              autoFocus
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
          )}
        </Field>
        {!error?.fields.reason && <ErrorNote error={error} />}
        <div className="row-end">
          <Button onClick={onClose}>{t('cancel')}</Button>
          <Button tone={danger ? 'danger' : 'primary'} type="submit" busy={busy} disabled={!reason.trim()}>
            {confirm}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
