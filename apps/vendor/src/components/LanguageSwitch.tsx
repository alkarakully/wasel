import type { Lang } from '../lib/api'
import { useI18n } from '../lib/i18n'
import { LANGUAGES } from '../lib/strings'

export function LanguageSwitch({ setLang }: { setLang: (lang: Lang) => void }) {
  const { lang } = useI18n()
  return (
    <div className="segmented" role="group" aria-label="Language">
      {LANGUAGES.map((option) => (
        <button
          key={option.code}
          type="button"
          aria-pressed={lang === option.code}
          onClick={() => setLang(option.code)}
        >
          {option.label}
        </button>
      ))}
    </div>
  )
}
