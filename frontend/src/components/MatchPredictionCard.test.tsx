import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { MatchPredictionCard, formatProbability } from './MatchPredictionCard';

describe('formatProbability', () => {
  it('formats 0.653 as "65.3%"', () => {
    expect(formatProbability(0.653)).toBe('65.3%');
  });

  it('formats 0 as "0.0%"', () => {
    expect(formatProbability(0)).toBe('0.0%');
  });

  it('formats 1 as "100.0%"', () => {
    expect(formatProbability(1)).toBe('100.0%');
  });

  it('formats 0.5 as "50.0%"', () => {
    expect(formatProbability(0.5)).toBe('50.0%');
  });
});

describe('MatchPredictionCard', () => {
  const defaultProps = {
    homeTeam: 'Brazil',
    awayTeam: 'Germany',
    homeWinProb: 0.653,
    homeLossProb: 0.347,
    homeTeamCrest: 'https://example.com/brazil.svg',
    awayTeamCrest: 'https://example.com/germany.svg',
    matchDate: '2026-06-15T18:00:00Z',
  };

  it('renders home and away team names', () => {
    render(<MatchPredictionCard {...defaultProps} />);
    expect(screen.getByText('Brazil')).toBeInTheDocument();
    expect(screen.getByText('Germany')).toBeInTheDocument();
  });

  it('renders probabilities as percentages with 1 decimal place', () => {
    render(<MatchPredictionCard {...defaultProps} />);
    expect(screen.getByText('65.3%')).toBeInTheDocument();
    expect(screen.getByText('34.7%')).toBeInTheDocument();
  });

  it('applies favored class to home team when homeWinProb > homeLossProb', () => {
    render(<MatchPredictionCard {...defaultProps} />);
    const homeTeamEl = screen.getByText('Brazil').closest('.team');
    const awayTeamEl = screen.getByText('Germany').closest('.team');
    expect(homeTeamEl).toHaveClass('favored');
    expect(awayTeamEl).not.toHaveClass('favored');
  });

  it('applies favored class to away team when homeLossProb > homeWinProb', () => {
    render(
      <MatchPredictionCard
        {...defaultProps}
        homeWinProb={0.3}
        homeLossProb={0.7}
      />
    );
    const homeTeamEl = screen.getByText('Brazil').closest('.team');
    const awayTeamEl = screen.getByText('Germany').closest('.team');
    expect(homeTeamEl).not.toHaveClass('favored');
    expect(awayTeamEl).toHaveClass('favored');
  });

  it('displays match date in human-readable locale format', () => {
    render(<MatchPredictionCard {...defaultProps} />);
    const expectedDate = new Date('2026-06-15T18:00:00Z').toLocaleDateString();
    expect(screen.getByText(expectedDate)).toBeInTheDocument();
  });

  it('renders crest images with team name alt text', () => {
    render(<MatchPredictionCard {...defaultProps} />);
    const brazilImg = screen.getByAltText('Brazil');
    const germanyImg = screen.getByAltText('Germany');
    expect(brazilImg).toHaveAttribute('src', 'https://example.com/brazil.svg');
    expect(germanyImg).toHaveAttribute('src', 'https://example.com/germany.svg');
  });

  it('does not render crest image when crest URL is empty', () => {
    render(
      <MatchPredictionCard
        {...defaultProps}
        homeTeamCrest=""
        awayTeamCrest=""
      />
    );
    expect(screen.queryByAltText('Brazil')).not.toBeInTheDocument();
    expect(screen.queryByAltText('Germany')).not.toBeInTheDocument();
  });
});
