import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { KnockoutBracketView } from './KnockoutBracketView';
import type { KnockoutResponse } from '../types';

vi.mock('../api', () => ({
  fetchKnockout: vi.fn(),
}));

import { fetchKnockout } from '../api';
const mockFetchKnockout = vi.mocked(fetchKnockout);

const mockData: KnockoutResponse = {
  rounds: [
    {
      round_name: 'Round_of_32',
      matches: [
        {
          home_team: { team_name: 'Brazil', crest: 'https://example.com/brazil.svg' },
          away_team: { team_name: 'Germany', crest: 'https://example.com/germany.svg' },
          status: 'FINISHED',
          home_score: 2,
          away_score: 1,
        },
        {
          home_team: { team_name: 'TBD', crest: '' },
          away_team: { team_name: 'TBD', crest: '' },
          status: 'SCHEDULED',
          home_score: null,
          away_score: null,
        },
      ],
    },
    {
      round_name: 'Quarter_Finals',
      matches: [
        {
          home_team: { team_name: 'Brazil', crest: 'https://example.com/brazil.svg' },
          away_team: { team_name: 'TBD', crest: '' },
          status: 'TIMED',
          home_score: null,
          away_score: null,
        },
      ],
    },
  ],
};

describe('KnockoutBracketView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows loading state while fetching', () => {
    mockFetchKnockout.mockReturnValue(new Promise(() => {})); // never resolves
    render(<KnockoutBracketView active={true} />);

    expect(screen.getByRole('status')).toHaveTextContent('Loading knockout bracket');
  });

  it('renders rounds with formatted headers after data loads', async () => {
    mockFetchKnockout.mockResolvedValue(mockData);
    render(<KnockoutBracketView active={true} />);

    await waitFor(() => {
      expect(screen.getByText('Round of 32')).toBeInTheDocument();
    });
    expect(screen.getByText('Quarter Finals')).toBeInTheDocument();
  });

  it('displays team names and crests for determined teams', async () => {
    mockFetchKnockout.mockResolvedValue(mockData);
    render(<KnockoutBracketView active={true} />);

    await waitFor(() => {
      expect(screen.getAllByText('Brazil')).toHaveLength(2);
    });
    expect(screen.getByText('Germany')).toBeInTheDocument();

    const brazilImgs = screen.getAllByRole('img', { name: 'Brazil' });
    expect(brazilImgs[0]).toHaveAttribute('src', 'https://example.com/brazil.svg');
  });

  it('displays TBD for undetermined teams', async () => {
    mockFetchKnockout.mockResolvedValue(mockData);
    render(<KnockoutBracketView active={true} />);

    await waitFor(() => {
      const tbdElements = screen.getAllByText('TBD');
      expect(tbdElements.length).toBeGreaterThanOrEqual(3);
    });
  });

  it('displays scores for FINISHED matches', async () => {
    mockFetchKnockout.mockResolvedValue(mockData);
    render(<KnockoutBracketView active={true} />);

    await waitFor(() => {
      expect(screen.getByText('2')).toBeInTheDocument();
    });
    expect(screen.getByText('1')).toBeInTheDocument();
  });

  it('does not display scores for non-FINISHED matches', async () => {
    const data: KnockoutResponse = {
      rounds: [
        {
          round_name: 'Semi_Finals',
          matches: [
            {
              home_team: { team_name: 'Spain', crest: 'https://example.com/spain.svg' },
              away_team: { team_name: 'France', crest: 'https://example.com/france.svg' },
              status: 'SCHEDULED',
              home_score: null,
              away_score: null,
            },
          ],
        },
      ],
    };
    mockFetchKnockout.mockResolvedValue(data);
    render(<KnockoutBracketView active={true} />);

    await waitFor(() => {
      expect(screen.getByText('Spain')).toBeInTheDocument();
    });
    expect(screen.getByText('SCHEDULED')).toBeInTheDocument();
  });

  it('shows error state on fetch failure with retry button', async () => {
    mockFetchKnockout.mockRejectedValue(new Error('Network error'));
    render(<KnockoutBracketView active={true} />);

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
    });
    expect(screen.getByText('Network error')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument();
  });

  it('does not fetch when active is false', () => {
    mockFetchKnockout.mockResolvedValue(mockData);
    render(<KnockoutBracketView active={false} />);

    expect(mockFetchKnockout).not.toHaveBeenCalled();
  });

  it('re-fetches when active changes from false to true', async () => {
    mockFetchKnockout.mockResolvedValue(mockData);
    const { rerender } = render(<KnockoutBracketView active={false} />);

    expect(mockFetchKnockout).not.toHaveBeenCalled();

    rerender(<KnockoutBracketView active={true} />);

    await waitFor(() => {
      expect(mockFetchKnockout).toHaveBeenCalledTimes(1);
    });
  });
});
