import axios from 'axios'
import MockAdapter from 'axios-mock-adapter'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { client, tokenStore } from '../client'

let clientMock: MockAdapter
let rawMock: MockAdapter // the interceptor refreshes with the global axios, not `client`

beforeEach(() => {
  localStorage.clear()
  tokenStore.set('old-access', 'old-refresh')
  clientMock = new MockAdapter(client, { onNoMatch: 'throwException' })
  rawMock = new MockAdapter(axios, { onNoMatch: 'throwException' })
})
afterEach(() => { clientMock.restore(); rawMock.restore() })

describe('auth interceptors', () => {
  it('attaches the bearer token to requests', async () => {
    clientMock.onGet('/ping').reply((config) => [200, { auth: config.headers?.Authorization }])
    const { data } = await client.get('/ping')
    expect(data.auth).toBe('Bearer old-access')
  })

  it('on a 401, refreshes once, stores the ROTATED refresh token, and retries the request', async () => {
    clientMock.onGet('/data').replyOnce(401).onGet('/data').reply((config) => [200, { auth: config.headers?.Authorization }])
    rawMock.onPost(/\/auth\/refresh\//).reply(200, { access: 'new-access', refresh: 'new-refresh' })

    const { data } = await client.get('/data')

    expect(data.auth).toBe('Bearer new-access')
    expect(tokenStore.getAccess()).toBe('new-access')
    expect(tokenStore.getRefresh()).toBe('new-refresh') // backend rotates refresh tokens
  })

  it('shares a single refresh between simultaneous 401s', async () => {
    clientMock.onGet('/a').replyOnce(401).onGet('/a').reply(200, 'a')
    clientMock.onGet('/b').replyOnce(401).onGet('/b').reply(200, 'b')
    rawMock.onPost(/\/auth\/refresh\//).reply(200, { access: 'new-access', refresh: 'new-refresh' })

    const [a, b] = await Promise.all([client.get('/a'), client.get('/b')])

    expect([a.data, b.data]).toEqual(['a', 'b'])
    expect(rawMock.history.post).toHaveLength(1)
  })

  it('when the refresh itself fails, clears the session and sends the user to /login', async () => {
    const original = window.location
    Object.defineProperty(window, 'location', { configurable: true, value: { href: '/tasks' } })
    clientMock.onGet('/data').reply(401)
    rawMock.onPost(/\/auth\/refresh\//).reply(401)

    await expect(client.get('/data')).rejects.toBeTruthy()

    expect(tokenStore.getAccess()).toBeNull()
    expect(window.location.href).toBe('/login')
    Object.defineProperty(window, 'location', { configurable: true, value: original })
  })

  it('does not treat a wrong-password 401 on login as an expired session', async () => {
    clientMock.onPost('/auth/login/').reply(401, { detail: 'Invalid credentials.' })
    await expect(client.post('/auth/login/', {})).rejects.toBeTruthy()
    expect(rawMock.history.post).toHaveLength(0) // no refresh attempted
    expect(tokenStore.getAccess()).toBe('old-access') // session untouched
  })
})
