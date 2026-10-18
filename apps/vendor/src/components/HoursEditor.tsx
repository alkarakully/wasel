import { Check, Clock } from '@phosphor-icons/react'
import { useState } from 'react'

import { Api, DAYS, type Day, type OpeningHours, type Store } from '../lib/api'
import { useI18n } from '../lib/i18n'

interface Props {
  api: Api
  store: Store
  onSaved: (hours: OpeningHours) => void
  onError: (error: unknown) => void
}

const DEFAULT: [string, string] = ['10:00', '23:00']

/** One opening per weekday, or closed. Closing before opening means after midnight. */
export function HoursEditor({ api, store, onSaved, onError }: Props) {
  const { t } = useI18n()
  const [hours, setHours] = useState<Record<Day, [string, string] | null>>(() => {
    const saved = store.opening_hours ?? {}
    const known = Object.keys(saved).length > 0
    return Object.fromEntries(DAYS.map((day) => [day, known ? (saved[day] ?? null) : DEFAULT])) as Record<
      Day,
      [string, string] | null
    >
  })
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState(false)

  const change = (day: Day, value: [string, string] | null) => {
    setDone(false)
    setHours((h) => ({ ...h, [day]: value }))
  }

  const save = async () => {
    setBusy(true)
    try {
      const result = await api.setHours(store.id, hours)
      onSaved(result.opening_hours)
      setDone(true)
    } catch (e) {
      onError(e)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="plate-card hours" aria-labelledby="hours-title">
      <h2 id="hours-title">
        <Clock size={20} weight="light" aria-hidden="true" />
        {t('openingHours')}
      </h2>
      <p className="muted small">{t('hoursHelp')}</p>
      <ul>
        {DAYS.map((day) => {
          const value = hours[day]
          return (
            <li key={day} className={value ? '' : 'closed'}>
              <span className="day">{t(`day_${day}` as 'day_sat')}</span>
              <label className="switch">
                <input
                  type="checkbox"
                  role="switch"
                  checked={value !== null}
                  aria-label={t(`day_${day}` as 'day_sat')}
                  onChange={(e) => change(day, e.target.checked ? DEFAULT : null)}
                />
              </label>
              {value ? (
                <span className="times" dir="ltr">
                  <input
                    type="time"
                    aria-label={t('opens')}
                    value={value[0]}
                    onChange={(e) => change(day, [e.target.value, value[1]])}
                  />
                  <span aria-hidden="true">–</span>
                  <input
                    type="time"
                    aria-label={t('closes')}
                    value={value[1]}
                    onChange={(e) => change(day, [value[0], e.target.value])}
                  />
                </span>
              ) : (
                <span className="muted">{t('closedDay')}</span>
              )}
            </li>
          )
        })}
      </ul>
      <div className="actions">
        <button type="button" className="primary" disabled={busy} onClick={save}>
          {done ? <Check size={20} weight="light" aria-hidden="true" /> : null}
          {done ? t('saved') : t('saveHours')}
        </button>
      </div>
    </section>
  )
}
