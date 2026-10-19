import type { OrderStatus } from '../lib/api'
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

/** Phone numbers read left to right even in Arabic. */
export function Phone({ value }: { value: string }) {
  if (value.startsWith('staff:')) return <span className="muted">—</span>
  const local = value.startsWith('+964') ? `0${value.slice(4)}` : value
  return (
    <bdi dir="ltr" className="phone">
      {local.replace(/^(\d{4})(\d{3})(\d{4})$/, '$1 $2 $3')}
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
