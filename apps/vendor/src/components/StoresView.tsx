import { CheckCircle, Plus, Storefront } from '@phosphor-icons/react'
import { useCallback, useEffect, useState } from 'react'

import { Api, type ApplicationInput, type Applications } from '../lib/api'
import { useI18n } from '../lib/i18n'
import { storeTypeIcon } from '../lib/storeTypes'
import { StatusChip } from './Onboarding'
import { StoreForm } from './StoreForm'

interface Props {
  api: Api
  onError: (error: unknown) => void
}

/** Store settings for owners: every branch and its approval state, and applying for another one. */
export function StoresView({ api, onError }: Props) {
  const { t } = useI18n()
  const [data, setData] = useState<Applications | null>(null)
  const [adding, setAdding] = useState(false)
  const [sent, setSent] = useState(false)

  const load = useCallback(() => {
    api.applications().then(setData, onError)
  }, [api, onError])
  useEffect(load, [load])

  const submit = async (input: ApplicationInput) => {
    await api.apply(input)
    setAdding(false)
    setSent(true)
    load()
  }

  return (
    <div className="stores-page">
      <section className="plate-card">
        <div className="form-head">
          <h2>
            <Storefront size={22} weight="light" aria-hidden="true" />
            {t('yourStores')}
          </h2>
          {!adding && data?.can_apply && (
            <button type="button" className="primary" onClick={() => (setAdding(true), setSent(false))}>
              <Plus size={20} weight="light" aria-hidden="true" />
              {t('addBranch')}
            </button>
          )}
        </div>
        <p className="muted small">{t('branchesHelp')}</p>
        {sent && (
          <p className="note success-note" role="status">
            <CheckCircle size={20} weight="light" aria-hidden="true" />
            {t('branchSent')}
          </p>
        )}
        {data && !data.can_apply && data.reason === 'too_many_applications' && (
          <p className="note">{t('err_too_many_applications')}</p>
        )}
        <ul className="applications">
          {data?.applications.map((store) => {
            const Icon = storeTypeIcon(store.type)
            return (
              <li key={store.id}>
                <Icon size={28} weight="light" aria-hidden="true" className="store-icon" />
                <span className="grow">
                  <strong>{store.name}</strong>
                  <span className="muted small">{store.address || t(`type_${store.type}`)}</span>
                  {store.status === 'rejected' && store.rejection_reason && (
                    <span className="reason">{t('rejectedBecause', { reason: store.rejection_reason })}</span>
                  )}
                </span>
                <StatusChip status={store.status} />
              </li>
            )
          })}
        </ul>
      </section>

      {adding && (
        <section className="plate-card">
          <h2>{t('newBranchTitle')}</h2>
          <p className="muted small">{t('newBranchLead')}</p>
          <StoreForm mode="branch" onSubmit={submit} onCancel={() => setAdding(false)} />
        </section>
      )}
    </div>
  )
}
