import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { TeamCard } from './TeamCard';

describe('TeamCard', () => {
  it('renders team crest image with alt text set to team name', () => {
    render(<TeamCard teamName="Brazil" crestUrl="https://example.com/brazil.svg" />);

    const img = screen.getByRole('img', { name: 'Brazil' });
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute('src', 'https://example.com/brazil.svg');
    expect(img).toHaveAttribute('alt', 'Brazil');
  });

  it('renders team name adjacent to crest', () => {
    render(<TeamCard teamName="Germany" crestUrl="https://example.com/germany.svg" />);

    expect(screen.getByText('Germany')).toBeInTheDocument();
  });

  it('shows placeholder when crestUrl is empty string', () => {
    render(<TeamCard teamName="Argentina" crestUrl="" />);

    // Should not render an img element
    expect(screen.queryByRole('img')).not.toBeInTheDocument();
    // Should show the placeholder SVG with first letter
    expect(screen.getByText('A')).toBeInTheDocument();
    // Team name should still be displayed
    expect(screen.getByText('Argentina')).toBeInTheDocument();
  });

  it('shows placeholder when image fails to load', () => {
    render(<TeamCard teamName="France" crestUrl="https://example.com/broken.svg" />);

    const img = screen.getByRole('img', { name: 'France' });
    fireEvent.error(img);

    // After error, placeholder should appear
    expect(screen.queryByRole('img', { name: 'France' })).not.toBeInTheDocument();
    expect(screen.getByText('F')).toBeInTheDocument();
    // Team name should still be displayed
    expect(screen.getByText('France')).toBeInTheDocument();
  });

  it('placeholder shows first letter of team name uppercased', () => {
    render(<TeamCard teamName="spain" crestUrl="" />);

    expect(screen.getByText('S')).toBeInTheDocument();
  });
});
