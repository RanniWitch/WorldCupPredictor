import { describe, it, expect } from 'vitest';
import fc from 'fast-check';
import { render, cleanup } from '@testing-library/react';
import { formatProbability, MatchPredictionCard } from '../components/MatchPredictionCard';

/**
 * Property 7: Probability percentage formatting
 * **Validates: Requirements 9.1**
 */
describe('Property 7: Probability percentage formatting', () => {
  it('formatProbability produces "X.X%" for any probability in [0.0, 1.0]', () => {
    fc.assert(
      fc.property(
        fc.double({ min: 0, max: 1, noNaN: true }),
        (prob) => {
          const result = formatProbability(prob);
          const expected = (prob * 100).toFixed(1) + '%';
          expect(result).toBe(expected);
        }
      ),
      { numRuns: 100 }
    );
  });
});

/**
 * Property 8: Favored team identification
 * **Validates: Requirements 9.3**
 */
describe('Property 8: Favored team identification', () => {
  it('the team with higher probability receives the favored class', () => {
    fc.assert(
      fc.property(
        fc.double({ min: 0, max: 1, noNaN: true }),
        fc.double({ min: 0, max: 1, noNaN: true }),
        (homeWinProb, homeLossProb) => {
          fc.pre(homeWinProb !== homeLossProb);

          const { container } = render(
            <MatchPredictionCard
              homeTeam="TeamA"
              awayTeam="TeamB"
              homeWinProb={homeWinProb}
              homeLossProb={homeLossProb}
              homeTeamCrest=""
              awayTeamCrest=""
              matchDate="2026-06-15T18:00:00Z"
            />
          );

          const homeTeamEl = container.querySelector('.home-team');
          const awayTeamEl = container.querySelector('.away-team');

          if (homeWinProb > homeLossProb) {
            expect(homeTeamEl).toHaveClass('favored');
            expect(awayTeamEl).not.toHaveClass('favored');
          } else {
            expect(awayTeamEl).toHaveClass('favored');
            expect(homeTeamEl).not.toHaveClass('favored');
          }

          cleanup();
        }
      ),
      { numRuns: 100 }
    );
  });
});
