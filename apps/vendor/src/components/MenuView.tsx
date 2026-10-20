import { ForkKnife, ImageSquare, PencilSimple, Plus, Trash, X } from '@phosphor-icons/react'
import { useEffect, useMemo, useRef, useState, type CSSProperties, type FormEvent } from 'react'

import { Api, type Product, type ProductInput, type Store } from '../lib/api'
import { regionForCurrency } from '../lib/countries'
import { useI18n } from '../lib/i18n'
import { shrinkPhoto } from '../lib/photo'
import { amountInput } from '../lib/strings'

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

const EMPTY: ProductInput = {
  name_ar: '',
  name_ku: '',
  name_en: '',
  description_ar: '',
  description_ku: '',
  description_en: '',
  menu_section: '',
  price: '',
  unit_type: 'item',
}

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
              currency={store.currency}
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
              const description = (lang !== 'ar' && product[`description_${lang}`]) || product.description_ar
              if (editing === product.id) {
                return (
                  <li key={product.id} className="editing">
                    <ItemForm
                      api={api}
                      storeId={store.id}
                      currency={store.currency}
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
                  <span className="thumb" aria-hidden="true">
                    {product.image ? (
                      <img src={product.image} alt="" loading="lazy" />
                    ) : (
                      <ForkKnife size={22} weight="light" />
                    )}
                  </span>
                  <span className="product-text">
                    <span className="product-name">{label}</span>
                    {description && <span className="product-description">{description}</span>}
                  </span>
                  <span className="price">
                    {money(product.price, store.currency)}
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
  /** The store's currency: prices may use its decimals (none for IQD, 3 for KWD). */
  currency: string
  product?: Product
  sections: string[]
  onSaved: () => void
  onCancel: () => void
  onError: (error: unknown) => void
}

/** Add or edit one item: names in three languages, section, price, sold per item or per kg. */
function ItemForm({ api, storeId, currency, product, sections, onSaved, onCancel, onError }: FormProps) {
  const { t, error } = useI18n()
  const decimals = regionForCurrency(currency).decimals
  const [values, setValues] = useState<ProductInput>(
    product
      ? {
          name_ar: product.name_ar,
          name_ku: product.name_ku,
          name_en: product.name_en,
          description_ar: product.description_ar,
          description_ku: product.description_ku,
          description_en: product.description_en,
          menu_section: product.menu_section,
          price: product.price,
          unit_type: product.unit_type,
        }
      : EMPTY,
  )
  const [busy, setBusy] = useState(false)
  // A newly picked photo (uploaded on save), or 'remove' to drop the current one.
  const [photo, setPhoto] = useState<File | 'remove' | null>(null)
  const [photoProblem, setPhotoProblem] = useState<string | null>(null)
  const picker = useRef<HTMLInputElement>(null)
  const preview = useMemo(() => (photo instanceof File ? URL.createObjectURL(photo) : null), [photo])
  useEffect(() => () => void (preview && URL.revokeObjectURL(preview)), [preview])
  const shownPhoto = photo === 'remove' ? null : (preview ?? product?.image ?? null)

  const set = (key: keyof ProductInput) => (value: string) => setValues((v) => ({ ...v, [key]: value }))
  const valid = values.name_ar.trim() !== '' && Number(values.price) > 0

  const pick = (file: File | undefined) => {
    setPhotoProblem(null)
    if (!file) return
    if (!file.type.startsWith('image/')) return setPhotoProblem(error('invalid_image'))
    setPhoto(file)
  }

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (!valid) return
    setBusy(true)
    let saved: Product
    try {
      saved = product ? await api.updateProduct(product.id, values) : await api.addProduct(storeId, values)
    } catch (e) {
      onError(e)
      setBusy(false)
      return
    }
    try {
      if (photo instanceof File) await api.setProductImage(saved.id, await shrinkPhoto(photo))
      else if (photo === 'remove') await api.removeProductImage(saved.id)
      onSaved()
    } catch (e) {
      // The item itself is saved; the photo can be added again from Edit.
      onError(e)
      onSaved()
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
      <div className="photo-field">
        <button
          type="button"
          className="photo-drop"
          // A big drop target for the mouse; the labelled button beside it is the keyboard way in.
          tabIndex={-1}
          aria-hidden="true"
          onClick={() => picker.current?.click()}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault()
            pick(e.dataTransfer.files[0])
          }}
        >
          {shownPhoto ? <img src={shownPhoto} alt="" /> : <ImageSquare size={34} weight="light" aria-hidden="true" />}
        </button>
        <div className="photo-text">
          <strong>{t('photo')}</strong>
          <span className="muted">{t('photoHint')}</span>
          <div className="photo-actions">
            <button type="button" className="secondary small-button" onClick={() => picker.current?.click()}>
              {shownPhoto ? t('changePhoto') : t('addPhoto')}
            </button>
            {shownPhoto && (
              <button
                type="button"
                className="link danger-link"
                onClick={() => setPhoto(product?.image ? 'remove' : null)}
              >
                {t('removePhoto')}
              </button>
            )}
          </div>
          {photoProblem && (
            <p className="error small" role="alert">
              {photoProblem}
            </p>
          )}
        </div>
        <input
          ref={picker}
          type="file"
          accept="image/*"
          hidden
          data-testid="photo-input"
          onChange={(e) => {
            pick(e.target.files?.[0])
            e.target.value = ''
          }}
        />
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
        <label className="wide">
          {t('descriptionAr')}
          <textarea
            className="text-input"
            dir="rtl"
            rows={2}
            maxLength={300}
            placeholder={t('descriptionHint')}
            value={values.description_ar}
            onChange={(e) => set('description_ar')(e.target.value)}
          />
        </label>
        <label>
          {t('descriptionKu')}
          <textarea
            className="text-input"
            dir="rtl"
            rows={2}
            maxLength={300}
            value={values.description_ku}
            onChange={(e) => set('description_ku')(e.target.value)}
          />
        </label>
        <label>
          {t('descriptionEn')}
          <textarea
            className="text-input"
            dir="ltr"
            rows={2}
            maxLength={300}
            value={values.description_en}
            onChange={(e) => set('description_en')(e.target.value)}
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
          {t('price')} · {currency}
          <input
            className="text-input"
            dir="ltr"
            inputMode={decimals ? 'decimal' : 'numeric'}
            required
            value={values.price}
            onChange={(e) => set('price')(amountInput(e.target.value, decimals))}
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
