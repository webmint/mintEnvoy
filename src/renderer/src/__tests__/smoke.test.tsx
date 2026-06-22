import { render, screen } from '@testing-library/react'
import App from '@renderer/App'

describe('renderer test harness', () => {
  it('arithmetic works', () => {
    expect(1 + 1).toBe(2)
  })

  it('jsdom renders and jest-dom matchers work', () => {
    render(<div>hello</div>)
    expect(screen.getByText('hello')).toBeInTheDocument()
  })

  it('@renderer alias resolves and App is a function component', () => {
    expect(App).toBeTypeOf('function')
  })
})
