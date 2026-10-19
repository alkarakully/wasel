import type { Api, Invite, StoreApplication, User } from './api'

/**
 * Where a signed-in person goes next:
 *   invites  someone invited them to a store's team; they accept or decline first
 *   portal   they own or work at an approved store
 *   waiting  their store is waiting for Wasel's approval, or was rejected
 *   apply    they're joining Wasel and fill in their first store
 *   refused  this number can't use the portal (error code to show)
 */
export type Step =
  | { kind: 'invites'; invites: Invite[] }
  | { kind: 'portal' }
  | { kind: 'waiting'; applications: StoreApplication[]; canApply: boolean }
  | { kind: 'apply' }
  | { kind: 'refused'; code: string }

/** `joining`: they came through "Join Wasel as a store", so a customer number may apply. */
export async function nextStep(api: Api, user: User, joining: boolean): Promise<Step> {
  const invites = await api.myInvites()
  if (invites.length) return { kind: 'invites', invites }

  if (user.role === 'vendor' && (await api.myStores()).length) return { kind: 'portal' }
  if (user.role !== 'vendor' && !joining) return { kind: 'refused', code: 'not_vendor' }

  const { can_apply, reason, applications } = await api.applications()
  if (applications.length) return { kind: 'waiting', applications, canApply: can_apply }
  if (!can_apply) return { kind: 'refused', code: reason === 'phone_in_use' ? 'join_phone_in_use' : (reason ?? 'generic') }
  return { kind: 'apply' }
}
