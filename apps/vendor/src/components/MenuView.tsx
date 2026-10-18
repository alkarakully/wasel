import { Api, type Product, type Store } from '../lib/api'
import { useI18n } from '../lib/i18n'

interface Props {
  api: Api
  store: Store
  onChanged: (product: Pick<Product, 'id' | 'is_available'>) => void
  onError: (error: unknown) => void
}

/** Every item with an in-stock switch. Out-of-stock items can't be ordered. */
export function MenuView({ api, store, onChanged, onError }: Props) {
  const { t, lang, money } = useI18n()

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

  return (
    <div className="menu">
      {[...sections.entries()].map(([section, products]) => (
        <section key={section}>
          {section && <h2>{section}</h2>}
          <ul>
            {products.map((product) => {
              const label = (lang !== 'ar' && product[`name_${lang}`]) || product.name_ar
              return (
                <li key={product.id} className={product.is_available ? '' : 'unavailable'}>
                  <span className="product-name">{label}</span>
                  <span className="price">{money(product.price)}</span>
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
                </li>
              )
            })}
          </ul>
        </section>
      ))}
    </div>
  )
}
