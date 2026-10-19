import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'

import { InviteList } from '../components/Invites'
import { WaitingStep } from '../components/Onboarding'
import { StoreForm } from '../components/StoreForm'
import { StoresView } from '../components/StoresView'
import type { Invite, StoreApplication, User } from '../lib/api'
import { LangContext } from '../lib/i18n'
import { nextStep } from '../lib/onboarding'
import { fakeApi, store } from './fixtures'

// jsdom has no WebGL, like an old tablet: the picker falls back to typing coordinates.
vi.mock('maplibre-gl', () => ({
  default: {
    Map: class {
      constructor() {
        throw new Error('Failed to initialize WebGL')
      }
    },
  },
}))
vi.mock('maplibre-gl/dist/maplibre-gl.css', () => ({}))

const inEnglish = (ui: ReactNode) => render(<LangContext.Provider value="en">{ui}</LangContext.Provider>)

const owner: User = { id: 1, phone: '+9647800000501', name: 'Hassan', role: 'vendor' }

const application = (overrides: Partial<StoreApplication> = {}): StoreApplication => ({
  id: 9,
  name: "Hassan's Grill",
  type: 'restaurant',
  cuisine: 'eastern',
  address: 'Karrada, street 62',
  latitude: 33.3045,
  longitude: 44.4214,
  delivery_radius_km: '6',
  status: 'pending',
  rejection_reason: '',
  created_at: '2026-10-18T10:00:00Z',
  reviewed_at: null,
  ...overrides,
})

describe('Where a signed-in person goes', () => {
  const invite: Invite = { id: 4, store: { id: 1, name: 'Tigris Grill', type: 'restaurant' }, role: 'cashier', invited_by: 'Ali', created_at: '' }
  const apiWith = (invites: Invite[], stores: unknown[], apps: unknown) =>
    fakeApi({
      myInvites: vi.fn(async () => invites),
      myStores: vi.fn(async () => stores),
      applications: vi.fn(async () => apps),
    })
  const none = { can_apply: true, reason: null, applications: [] }

  it('answers invites first, then runs approved stores', async () => {
    expect(await nextStep(apiWith([invite], [store], none), owner, false)).toEqual({ kind: 'invites', invites: [invite] })
    expect(await nextStep(apiWith([], [store], none), owner, false)).toEqual({ kind: 'portal' })
  })

  it('waits while the only store is under review', async () => {
    const apps = { can_apply: false, reason: 'application_pending', applications: [application()] }
    expect(await nextStep(apiWith([], [], apps), owner, false)).toEqual({
      kind: 'waiting',
      applications: [application()],
      canApply: false,
    })
  })

  it('lets customers in only through joining', async () => {
    const customer = { ...owner, role: 'customer' as const }
    expect(await nextStep(apiWith([], [], none), customer, false)).toEqual({ kind: 'refused', code: 'not_vendor' })
    expect(await nextStep(apiWith([], [], none), customer, true)).toEqual({ kind: 'apply' })
  })
})

describe('Store form', () => {
  it('needs a map spot, then sends the store for approval', async () => {
    const onSubmit = vi.fn(async () => ({}))
    inEnglish(<StoreForm mode="first" onSubmit={onSubmit} />)

    await userEvent.type(screen.getByLabelText('Your name'), 'Hassan Ali')
    await userEvent.type(screen.getByLabelText('Store name'), "Hassan's Grill")
    await userEvent.selectOptions(screen.getByLabelText('Cuisine'), 'eastern')
    await userEvent.type(screen.getByLabelText('Address'), 'Karrada, street 62')
    await userEvent.click(screen.getByRole('button', { name: 'Send for approval' }))
    expect(await screen.findByRole('alert')).toHaveTextContent("Set the store's location on the map.")
    expect(onSubmit).not.toHaveBeenCalled()

    // No WebGL here, so the picker offers typing the spot instead.
    await userEvent.type(await screen.findByLabelText('Latitude'), '33.3045')
    await userEvent.type(screen.getByLabelText('Longitude'), '44.4214')
    await userEvent.click(screen.getByRole('button', { name: 'Send for approval' }))
    expect(onSubmit).toHaveBeenCalledWith({
      owner_name: 'Hassan Ali',
      name: "Hassan's Grill",
      type: 'restaurant',
      cuisine: 'eastern',
      address: 'Karrada, street 62',
      latitude: 33.3045,
      longitude: 44.4214,
      delivery_radius_km: '5',
    })
  })

  it('has no cuisine for supermarkets and starts from a rejected application', async () => {
    const onSubmit = vi.fn(async () => ({}))
    inEnglish(<StoreForm mode="branch" from={application({ status: 'rejected' })} onSubmit={onSubmit} />)
    expect(screen.queryByLabelText('Your name')).toBeNull()
    expect(screen.getByLabelText('Store name')).toHaveValue("Hassan's Grill")
    await userEvent.click(screen.getByRole('radio', { name: 'Supermarket' }))
    expect(screen.queryByLabelText('Cuisine')).toBeNull()
    await userEvent.click(screen.getByRole('button', { name: 'Send branch for approval' }))
    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ type: 'supermarket', cuisine: '', delivery_radius_km: '6' }))
  })
})

describe('Waiting for approval', () => {
  const props = { api: fakeApi(), user: owner, setLang: vi.fn(), onLogout: vi.fn(), onDone: vi.fn() }

  it('tells the owner their store is being reviewed', () => {
    inEnglish(<WaitingStep {...props} applications={[application()]} canApply={false} />)
    expect(screen.getByRole('heading', { name: 'Waiting for approval' })).toBeInTheDocument()
    expect(screen.getByText(/\+9647800000501/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Fix and send again' })).toBeNull()
  })

  it('shows why a store was rejected and lets the owner fix it', async () => {
    const rejected = application({ status: 'rejected', rejection_reason: 'We could not find the address.' })
    inEnglish(<WaitingStep {...props} applications={[rejected]} canApply />)
    expect(screen.getByRole('heading', { name: "Your store wasn't approved" })).toBeInTheDocument()
    expect(screen.getByText('Reason: We could not find the address.')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Fix and send again' }))
    expect(screen.getByLabelText('Store name')).toHaveValue("Hassan's Grill")
  })
})

describe('Invites', () => {
  it('accepts or declines each invite', async () => {
    const invites: Invite[] = [
      { id: 4, store: { id: 1, name: 'Tigris Grill', type: 'restaurant' }, role: 'manager', invited_by: 'Ali', created_at: '' },
      { id: 5, store: { id: 2, name: 'Karrada Market', type: 'supermarket' }, role: 'cashier', invited_by: '', created_at: '' },
    ]
    const api = fakeApi({ answerInvite: vi.fn(async () => ({})) })
    const onAnswered = vi.fn()
    inEnglish(<InviteList api={api} invites={invites} onAnswered={onAnswered} />)
    expect(screen.getByText('Ali invited you to join as Manager')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Accept Tigris Grill' }))
    await userEvent.click(screen.getByRole('button', { name: 'Decline Karrada Market' }))
    expect(api.answerInvite).toHaveBeenNthCalledWith(1, 4, 'accept')
    expect(api.answerInvite).toHaveBeenNthCalledWith(2, 5, 'decline')
    expect(onAnswered).toHaveBeenCalledWith(invites[0], 'accept')
  })
})

describe('Store settings', () => {
  it('lists every branch with its state and applies for another', async () => {
    const applications = vi.fn(async () => ({
      can_apply: true,
      reason: null,
      applications: [
        application({ id: 1, name: 'Main', status: 'approved' }),
        application({ id: 2, name: 'Mansour', status: 'rejected', rejection_reason: 'Outside our area.' }),
      ],
    }))
    const api = fakeApi({ applications, apply: vi.fn(async () => application()) })
    inEnglish(<StoresView api={api} onError={vi.fn()} />)

    const main = (await screen.findByText('Main')).closest('li')!
    expect(within(main).getByText('Live')).toBeInTheDocument()
    expect(screen.getByText('Reason: Outside our area.')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Add a branch' }))
    await userEvent.type(screen.getByLabelText('Store name'), 'Zayouna')
    await userEvent.type(screen.getByLabelText('Address'), 'Zayouna, street 12')
    await userEvent.type(await screen.findByLabelText('Latitude'), '33.32')
    await userEvent.type(screen.getByLabelText('Longitude'), '44.45')
    await userEvent.click(screen.getByRole('button', { name: 'Send branch for approval' }))
    expect(api.apply).toHaveBeenCalledWith(expect.objectContaining({ name: 'Zayouna', latitude: 33.32 }))
    expect(api.apply).toHaveBeenCalledWith(expect.not.objectContaining({ owner_name: expect.anything() }))
    expect(await screen.findByRole('status')).toHaveTextContent("Branch sent. We'll let you know once it's approved.")
  })

  it('hides adding while too many branches wait', async () => {
    const api = fakeApi({
      applications: vi.fn(async () => ({ can_apply: false, reason: 'too_many_applications', applications: [] })),
    })
    inEnglish(<StoresView api={api} onError={vi.fn()} />)
    expect(await screen.findByText(/Wait until they are approved first/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Add a branch' })).toBeNull()
  })
})
