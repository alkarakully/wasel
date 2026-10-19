import type { OrderStatus } from '../lib/api'
import { COUNTRIES } from '../lib/countries'
import { useI18n } from '../lib/i18n'
import type { StringKey } from '../lib/strings'
import { Badge, type BadgeTone } from './ui'

const STATUS_TONE: Record<OrderStatus, BadgeTone> = {
  received: 'gold',
  preparing: 'lapis',
  ready: 'lapis',
  out_for_delivery: 'lapis',
  delivered: 'good',
  cancelled: 'bad',
}

export function StatusBadge({ status }: { status: OrderStatus }) {
  const { t } = useI18n()
  return <Badge tone={STATUS_TONE[status]}>{t(`st_${status}` as StringKey)}</Badge>
}

/** Phone numbers read left to right even in Arabic: Iraqi ones the local way, others with their + code. */
export function Phone({ value }: { value: string }) {
  if (value.startsWith('staff:')) return <span className="muted">—</span>
  let shown = value
  if (value.startsWith('+964')) {
    shown = `0${value.slice(4)}`.replace(/^(\d{4})(\d{3})(\d{4})$/, '$1 $2 $3')
  } else if (value.startsWith('+')) {
    const dial = [3, 2, 1].map((n) => value.slice(1, 1 + n)).find((d) => COUNTRIES.some((c) => c.dial === d))
    if (dial) shown = `+${dial} ${value.slice(1 + dial.length)}`
  }
  return (
    <bdi dir="ltr" className="phone">
      {shown}
    </bdi>
  )
}

export function Who({ name, phone }: { name: string; phone: string }) {
  return (
    <span className="who">
      <span>{name || '—'}</span>
      <Phone value={phone} />
    </span>
  )
}
