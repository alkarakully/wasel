import { useEffect, useRef, useState } from 'react'

import { useI18n } from '../lib/i18n'

const PRESETS = ['reason_out_of_stock', 'reason_busy', 'reason_closing'] as const

interface Props {
  orderId: number
  onCancel: () => void
  onConfirm: (reason: string) => void
}

/** Pick a common reason or type one; the customer sees it. */
export function RejectDialog({ orderId, onCancel, onConfirm }: Props) {
  const { t } = useI18n()
  const dialog = useRef<HTMLDialogElement>(null)
  const [preset, setPreset] = useState<(typeof PRESETS)[number] | 'other'>('reason_out_of_stock')
  const [other, setOther] = useState('')

  useEffect(() => {
    dialog.current?.showModal()
  }, [])

  const reason = preset === 'other' ? other.trim() : t(preset)

  return (
    <dialog ref={dialog} className="dialog" aria-labelledby={`reject-${orderId}`} onCancel={onCancel}>
      <form
        method="dialog"
        onSubmit={(e) => {
          e.preventDefault()
          if (reason) onConfirm(reason)
        }}
      >
        <h2 id={`reject-${orderId}`}>{t('rejectTitle', { id: orderId })}</h2>
        <fieldset>
          <legend>{t('rejectReason')}</legend>
          {PRESETS.map((key) => (
            <label key={key} className="radio">
              <input type="radio" name="reason" checked={preset === key} onChange={() => setPreset(key)} />
              {t(key)}
            </label>
          ))}
          <label className="radio">
            <input type="radio" name="reason" checked={preset === 'other'} onChange={() => setPreset('other')} />
            {t('otherReason')}
          </label>
          {preset === 'other' && (
            <input
              className="text-input"
              autoFocus
              maxLength={255}
              value={other}
              aria-label={t('otherReason')}
              onChange={(e) => setOther(e.target.value)}
            />
          )}
        </fieldset>
        <div className="actions">
          <button type="submit" className="danger" disabled={!reason}>
            {t('confirmReject')}
          </button>
          <button type="button" className="secondary" onClick={onCancel}>
            {t('cancel')}
          </button>
        </div>
      </form>
    </dialog>
  )
}
