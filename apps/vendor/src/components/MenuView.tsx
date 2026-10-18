import { PencilSimple, Plus, Trash, X } from '@phosphor-icons/react'
import { useState, type CSSProperties, type FormEvent } from 'react'

import { Api, type Product, type ProductInput, type Store } from '../lib/api'
import { useI18n } from '../lib/i18n'

interface Props {
  api: Api
  store: Store
  onChanged: (product: Pick<Product, 'id' | 'is_available'>) => void
  onError: (error: unknown) => void
  /** Owners and managers can add, edit and remove items. */
  canEdit?: boolean
  /** Reload the menu after an edit. */
  onReload?: () => void
}

const EMPTY: ProductInput = { name_ar: '', name_ku: '', name_en: '', menu_section: '', price: '', unit_type: 'item' }

/** Every item with an in-stock switch. Out-of-stock items can't be ordered. */
export function MenuView({ api, store, onChanged, onError, canEdit = false, onReload }: Props) {
  const { t, lang, money } = useI18n()
  const [editing, setEditing] = useState<number | 'new' | null>(null)

  const sections = new Map<string, Product[]>()
  for (const product of store.products) {
    const list = sections.get(product.menu_section) ?? []
    list.push(product)
    sections.set(product.menu_section, list)
  }

  const toggle = async (product: Product) => {
    // Flip right away so the switch feels instant; undo if the server says no.
    onChanged({ id: product.id, is_available: !product.is_available })
    try {
      onChanged(await api.setAvailable(product.id, !product.is_available))
    } catch (e) {
      onChanged({ id: product.id, is_available: product.is_available })
      onError(e)
    }
  }

  const remove = async (product: Product, label: string) => {
    if (!window.confirm(t('removeItemConfirm', { name: label }))) return
    try {
      await api.removeProduct(product.id)
      onReload?.()
    } catch (e) {
      onError(e)
    }
  }

  const saved = () => {
    setEditing(null)
    onReload?.()
  }

  return (
    <div className="menu">
      {canEdit && (
        <div className="menu-tools">
          {editing === 'new' ? (
            <ItemForm
              api={api}
              storeId={store.id}
              sections={[...sections.keys()].filter(Boolean)}
              onSaved={saved}
              onCancel={() => setEditing(null)}
              onError={onError}
            />
          ) : (
            <button type="button" className="primary" onClick={() => setEditing('new')}>
              <Plus size={20} weight="light" aria-hidden="true" />
              {t('addItem')}
            </button>
          )}
        </div>
      )}
      {[...sections.entries()].map(([section, products]) => (
        <section key={section}>
          {section && <h2>{section}</h2>}
          <ul>
            {products.map((product, index) => {
              const label = (lang !== 'ar' && product[`name_${lang}`]) || product.name_ar
              if (editing === product.id) {
                return (
                  <li key={product.id} className="editing">
                    <ItemForm
                      api={api}
                      storeId={store.id}
                      product={product}
                      sections={[...sections.keys()].filter(Boolean)}
                      onSaved={saved}
                      onCancel={() => setEditing(null)}
                      onError={onError}
                    />
                  </li>
                )
              }
              return (
                <li
                  key={product.id}
                  className={product.is_available ? '' : 'unavailable'}
                  style={{ '--i': Math.min(index, 10) } as CSSProperties}
                >
                  <span className="product-name">{label}</span>
                  <span className="price">
                    {money(product.price)}
                    {product.unit_type === 'kg' && <span className="muted"> / kg</span>}
                  </span>
                  <label className="switch">
                    <input
                      type="checkbox"
                      role="switch"
                      checked={product.is_available}
                      onChange={() => toggle(product)}
                      aria-label={label}
                    />
                    <span>{product.is_available ? t('available') : t('outOfStock')}</span>
                  </label>
                  {canEdit && (
                    <span className="row-actions">
                      <button
                        type="button"
                        className="icon-button"
                        title={t('editItem')}
                        onClick={() => setEditing(product.id)}
                      >
                        <PencilSimple size={18} weight="light" aria-hidden="true" />
                        <span className="sr-only">
                          {t('editItem')} {label}
                        </span>
                      </button>
                      <button
                        type="button"
                        className="icon-button danger-icon"
                        title={t('remove')}
                        onClick={() => remove(product, label)}
                      >
                        <Trash size={18} weight="light" aria-hidden="true" />
                        <span className="sr-only">
                          {t('remove')} {label}
                        </span>
                      </button>
                    </span>
                  )}
                </li>
              )
            })}
          </ul>
        </section>
      ))}
    </div>
  )
}

interface FormProps {
  api: Api
  storeId: number
  product?: Product
  sections: string[]
  onSaved: () => void
  onCancel: () => void
  onError: (error: unknown) => void
}

/** Add or edit one item: names in three languages, section, price, sold per item or per kg. */
function ItemForm({ api, storeId, product, sections, onSaved, onCancel, onError }: FormProps) {
  const { t } = useI18n()
  const [values, setValues] = useState<ProductInput>(
    product
      ? {
          name_ar: product.name_ar,
          name_ku: product.name_ku,
          name_en: product.name_en,
          menu_section: product.menu_section,
          price: String(Math.round(Number(product.price))),
          unit_type: product.unit_type,
        }
      : EMPTY,
  )
  const [busy, setBusy] = useState(false)
  const set = (key: keyof ProductInput) => (value: string) => setValues((v) => ({ ...v, [key]: value }))
  const valid = values.name_ar.trim() !== '' && Number(values.price) > 0

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (!valid) return
    setBusy(true)
    try {
      if (product) await api.updateProduct(product.id, values)
      else await api.addProduct(storeId, values)
      onSaved()
    } catch (e) {
      onError(e)
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="item-form" onSubmit={submit}>
      <div className="form-head">
        <strong>{product ? t('editItem') : t('newItem')}</strong>
        <button type="button" className="icon-button" onClick={onCancel} title={t('cancel')}>
          <X size={18} weight="light" aria-hidden="true" />
          <span className="sr-only">{t('cancel')}</span>
        </button>
      </div>
      <div className="form-grid">
        <label>
          {t('nameAr')}
          <input
            className="text-input"
            dir="rtl"
            required
            value={values.name_ar}
            onChange={(e) => set('name_ar')(e.target.value)}
          />
        </label>
        <label>
          {t('nameKu')}
          <input
            className="text-input"
            dir="rtl"
            value={values.name_ku}
            onChange={(e) => set('name_ku')(e.target.value)}
          />
        </label>
        <label>
          {t('nameEn')}
          <input
            className="text-input"
            dir="ltr"
            value={values.name_en}
            onChange={(e) => set('name_en')(e.target.value)}
          />
        </label>
        <label>
          {t('section')}
          <input
            className="text-input"
            list={`sections-${storeId}`}
            placeholder={t('sectionHint')}
            value={values.menu_section}
            onChange={(e) => set('menu_section')(e.target.value)}
          />
          <datalist id={`sections-${storeId}`}>
            {sections.map((section) => (
              <option key={section} value={section} />
            ))}
          </datalist>
        </label>
        <label>
          {t('price')}
          <input
            className="text-input"
            dir="ltr"
            inputMode="numeric"
            required
            value={values.price}
            onChange={(e) => set('price')(e.target.value.replace(/[^\d]/g, ''))}
          />
        </label>
        <fieldset className="unit">
          <legend>{t('unit')}</legend>
          <div className="segmented">
            {(['item', 'kg'] as const).map((unit) => (
              <button
                key={unit}
                type="button"
                aria-pressed={values.unit_type === unit}
                onClick={() => set('unit_type')(unit)}
              >
                {unit === 'item' ? t('perItem') : t('perKg')}
              </button>
            ))}
          </div>
        </fieldset>
      </div>
      <div className="actions">
        <button type="submit" className="primary" disabled={!valid || busy}>
          {t('save')}
        </button>
        <button type="button" className="secondary" onClick={onCancel}>
          {t('cancel')}
        </button>
      </div>
    </form>
  )
}
