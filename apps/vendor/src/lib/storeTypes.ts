import { Basket, Coffee, Flower, ForkKnife, Pill, ShoppingCart, type Icon } from '@phosphor-icons/react'

import type { StoreType } from './api'

/** Every kind of store, in the order sign-up offers them, with its icon. */
export const STORE_TYPES: [StoreType, Icon][] = [
  ['restaurant', ForkKnife],
  ['supermarket', Basket],
  ['cafe', Coffee],
  ['pharmacy', Pill],
  ['convenience', ShoppingCart],
  ['flowers', Flower],
]

export const storeTypeIcon = (type: string): Icon => STORE_TYPES.find(([t]) => t === type)?.[1] ?? ForkKnife
