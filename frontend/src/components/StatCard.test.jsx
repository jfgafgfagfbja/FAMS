import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { GraduationCap } from '@phosphor-icons/react'
import StatCard from './StatCard'

describe('StatCard', () => {
  it('renders the label and value', () => {
    render(<StatCard icon={GraduationCap} label="Lớp học phần" value={5} tint="accent" />)
    expect(screen.getByText('Lớp học phần')).toBeInTheDocument()
    expect(screen.getByText('5')).toBeInTheDocument()
  })

  it('shows a placeholder value as-is (e.g. when data is unavailable)', () => {
    render(<StatCard icon={GraduationCap} label="Tổng sinh viên" value="—" tint="accent" />)
    expect(screen.getByText('—')).toBeInTheDocument()
  })
})
