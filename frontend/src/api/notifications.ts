import { client } from './client'
import type { Notification, NotificationCategory, NotificationPreferences, Paginated } from '../types'

export interface NotificationFilters {
  is_read?: boolean
  category?: NotificationCategory
  page?: number
}

// FR-060: notification history.
export async function listNotifications(filters: NotificationFilters = {}): Promise<Paginated<Notification>> {
  const { data } = await client.get('/notifications/', { params: filters })
  return data
}

export async function getUnreadCount(): Promise<number> {
  const { data } = await client.get('/notifications/unread_count/')
  return data.count
}

export async function markNotificationRead(id: number): Promise<Notification> {
  const { data } = await client.post(`/notifications/${id}/mark_read/`)
  return data
}

export async function markAllNotificationsRead(): Promise<void> {
  await client.post('/notifications/mark-all-read/')
}

// FR-059: preferences.
export async function getNotificationPreferences(): Promise<NotificationPreferences> {
  const { data } = await client.get('/notifications/preferences/')
  return data
}

export async function updateNotificationPreferences(
  patch: Partial<NotificationPreferences>
): Promise<NotificationPreferences> {
  const { data } = await client.patch('/notifications/preferences/', patch)
  return data
}

// FR-095: system-wide notification settings - read by anyone, changed by administrators.
export interface NotificationSettings {
  due_soon_days: number
}

export async function getNotificationSettings(): Promise<NotificationSettings> {
  const { data } = await client.get('/notifications/settings/')
  return data
}

export async function updateNotificationSettings(due_soon_days: number): Promise<NotificationSettings> {
  const { data } = await client.patch('/notifications/settings/', { due_soon_days })
  return data
}
