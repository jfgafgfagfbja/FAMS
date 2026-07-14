import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Login from './Login'
import api from '../api'

vi.mock('../api', () => ({
  default: { post: vi.fn() },
}))

describe('Login', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    sessionStorage.clear()
  })

  it('shows an error message when login fails', async () => {
    api.post.mockRejectedValueOnce(new Error('401'))
    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>,
    )

    fireEvent.change(screen.getByPlaceholderText('ten@fams.edu.vn'), { target: { value: 'a@b.com' } })
    fireEvent.change(screen.getByPlaceholderText('••••••••'), { target: { value: 'wrong' } })
    fireEvent.click(screen.getByRole('button', { name: /đăng nhập/i }))

    await waitFor(() => expect(screen.getByText(/sai email hoặc mật khẩu/i)).toBeInTheDocument())
    expect(sessionStorage.getItem('token')).toBeNull()
  })

  it('stores the token, role, and email on success', async () => {
    api.post.mockResolvedValueOnce({ data: { access_token: 'tok123', role: 'admin' } })
    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>,
    )

    fireEvent.change(screen.getByPlaceholderText('ten@fams.edu.vn'), { target: { value: 'admin@fams.edu.vn' } })
    fireEvent.change(screen.getByPlaceholderText('••••••••'), { target: { value: 'admin123' } })

    // window.location.reload() is called on success; jsdom doesn't implement it, so stub it out.
    const reload = vi.fn()
    Object.defineProperty(window, 'location', { value: { ...window.location, reload }, writable: true })

    fireEvent.click(screen.getByRole('button', { name: /đăng nhập/i }))

    await waitFor(() => expect(sessionStorage.getItem('token')).toBe('tok123'))
    expect(sessionStorage.getItem('role')).toBe('admin')
    expect(sessionStorage.getItem('email')).toBe('admin@fams.edu.vn')
  })
})
