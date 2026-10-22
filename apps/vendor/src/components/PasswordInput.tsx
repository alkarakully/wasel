import { Eye, EyeSlash } from '@phosphor-icons/react'
import { useState } from 'react'

import { useI18n } from '../lib/i18n'

interface Props {
  id: string
  value: string
  onChange: (value: string) => void
  /** Lets the browser's password manager suggest a strong new password. */
  newPassword?: boolean
  invalid?: boolean
  describedBy?: string
  autoFocus?: boolean
}

/** A password field with a show/hide eye. */
export function PasswordInput({ id, value, onChange, newPassword, invalid, describedBy, autoFocus }: Props) {
  const { t } = useI18n()
  const [shown, setShown] = useState(false)
  return (
    <div className="password-input" dir="ltr">
      <input
        id={id}
        className="text-input"
        type={shown ? 'text' : 'password'}
        autoComplete={newPassword ? 'new-password' : 'current-password'}
        autoFocus={autoFocus}
        value={value}
        aria-invalid={invalid}
        aria-describedby={describedBy}
        onChange={(e) => onChange(e.target.value)}
      />
      <button
        type="button"
        className="icon-button"
        aria-pressed={shown}
        title={t('showPassword')}
        onClick={() => setShown(!shown)}
      >
        {shown ? (
          <EyeSlash size={20} weight="light" aria-hidden="true" />
        ) : (
          <Eye size={20} weight="light" aria-hidden="true" />
        )}
        <span className="sr-only">{t('showPassword')}</span>
      </button>
    </div>
  )
}
