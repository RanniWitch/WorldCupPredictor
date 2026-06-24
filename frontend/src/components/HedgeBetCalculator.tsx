import { useState, useCallback } from 'react';
import './HedgeBetCalculator.css';

type OddsFormat = 'decimal' | 'fractional' | 'american';
type HedgeMode = 'two-way' | 'three-way' | 'free-bet';

interface TwoWayResult {
  hedgeStake: number;
  profitIfOriginalWins: number;
  profitIfHedgeWins: number;
  guaranteedProfit: number;
  roi: number;
}

interface FreeBetResult {
  hedgeStake: number;
  profitIfFreeBetWins: number;
  profitIfHedgeWins: number;
  guaranteedProfit: number;
}

interface ThreeWayResult {
  stakeWin: number;
  stakeDraw: number;
  stakeLose: number;
  totalStake: number;
  profitIfWin: number;
  profitIfDraw: number;
  profitIfLose: number;
  guaranteedProfit: number;
  roi: number;
  isArbitrage: boolean;
}

// --- Odds Conversion Utilities ---

function decimalToFractional(decimal: number): string {
  if (decimal <= 1) return '0/1';
  const numerator = decimal - 1;
  // Find a reasonable fraction representation
  const precision = 100;
  const gcdVal = gcd(Math.round(numerator * precision), precision);
  const num = Math.round(numerator * precision) / gcdVal;
  const den = precision / gcdVal;
  return `${num}/${den}`;
}

function decimalToAmerican(decimal: number): string {
  if (decimal >= 2.0) {
    return `+${Math.round((decimal - 1) * 100)}`;
  } else {
    return `${Math.round(-100 / (decimal - 1))}`;
  }
}

function fractionalToDecimal(fractional: string): number | null {
  const parts = fractional.split('/');
  if (parts.length !== 2) return null;
  const num = parseFloat(parts[0]);
  const den = parseFloat(parts[1]);
  if (isNaN(num) || isNaN(den) || den === 0) return null;
  return num / den + 1;
}

function americanToDecimal(american: string): number | null {
  const val = parseFloat(american);
  if (isNaN(val)) return null;
  if (val > 0) {
    return val / 100 + 1;
  } else if (val < 0) {
    return 100 / Math.abs(val) + 1;
  }
  return null;
}

function parseOddsToDecimal(value: string, format: OddsFormat): number | null {
  if (!value.trim()) return null;
  switch (format) {
    case 'decimal': {
      const d = parseFloat(value);
      return isNaN(d) || d <= 1 ? null : d;
    }
    case 'fractional':
      return fractionalToDecimal(value);
    case 'american':
      return americanToDecimal(value);
  }
}

function gcd(a: number, b: number): number {
  a = Math.abs(Math.round(a));
  b = Math.abs(Math.round(b));
  while (b) {
    [a, b] = [b, a % b];
  }
  return a;
}

// --- Calculation Functions ---

function calculateTwoWayHedge(
  originalStake: number,
  originalOddsDecimal: number,
  hedgeOddsDecimal: number
): TwoWayResult | null {
  if (originalStake <= 0 || originalOddsDecimal <= 1 || hedgeOddsDecimal <= 1) {
    return null;
  }

  // Original bet total return if it wins (stake + profit)
  // To guarantee equal profit regardless of outcome:
  // If original wins: profit = originalReturn - originalStake - hedgeStake
  //                          = originalStake * (originalOdds - 1) - hedgeStake
  // If hedge wins:    profit = hedgeStake * (hedgeOdds - 1) - originalStake
  //
  // Set equal: originalStake*(originalOdds-1) - hedgeStake = hedgeStake*(hedgeOdds-1) - originalStake
  // Solve:     hedgeStake = originalStake * originalOdds / hedgeOdds
  const hedgeStake = (originalStake * originalOddsDecimal) / hedgeOddsDecimal;

  // Profit calculations
  const profitIfOriginalWins = originalStake * (originalOddsDecimal - 1) - hedgeStake;
  const profitIfHedgeWins = hedgeStake * (hedgeOddsDecimal - 1) - originalStake;
  const guaranteedProfit = Math.min(profitIfOriginalWins, profitIfHedgeWins);
  const totalInvested = originalStake + hedgeStake;
  const roi = (guaranteedProfit / totalInvested) * 100;

  return {
    hedgeStake: Math.round(hedgeStake * 100) / 100,
    profitIfOriginalWins: Math.round(profitIfOriginalWins * 100) / 100,
    profitIfHedgeWins: Math.round(profitIfHedgeWins * 100) / 100,
    guaranteedProfit: Math.round(guaranteedProfit * 100) / 100,
    roi: Math.round(roi * 100) / 100,
  };
}

function calculateThreeWayHedge(
  totalBudget: number,
  winOdds: number,
  drawOdds: number,
  loseOdds: number
): ThreeWayResult | null {
  if (totalBudget <= 0 || winOdds <= 1 || drawOdds <= 1 || loseOdds <= 1) {
    return null;
  }

  // For arbitrage/equal profit distribution:
  // stake_i = totalBudget / (odds_i * sum(1/odds_j for all j))
  const inverseSum = 1 / winOdds + 1 / drawOdds + 1 / loseOdds;

  const stakeWin = totalBudget * (1 / winOdds) / inverseSum;
  const stakeDraw = totalBudget * (1 / drawOdds) / inverseSum;
  const stakeLose = totalBudget * (1 / loseOdds) / inverseSum;

  const profitIfWin = stakeWin * winOdds - totalBudget;
  const profitIfDraw = stakeDraw * drawOdds - totalBudget;
  const profitIfLose = stakeLose * loseOdds - totalBudget;

  const guaranteedProfit = Math.min(profitIfWin, profitIfDraw, profitIfLose);
  const roi = (guaranteedProfit / totalBudget) * 100;
  const isArbitrage = inverseSum < 1;

  return {
    stakeWin: Math.round(stakeWin * 100) / 100,
    stakeDraw: Math.round(stakeDraw * 100) / 100,
    stakeLose: Math.round(stakeLose * 100) / 100,
    totalStake: Math.round(totalBudget * 100) / 100,
    profitIfWin: Math.round(profitIfWin * 100) / 100,
    profitIfDraw: Math.round(profitIfDraw * 100) / 100,
    profitIfLose: Math.round(profitIfLose * 100) / 100,
    guaranteedProfit: Math.round(guaranteedProfit * 100) / 100,
    roi: Math.round(roi * 100) / 100,
    isArbitrage,
  };
}

function calculateFreeBetHedge(
  freeBetAmount: number,
  freeBetOddsDecimal: number,
  hedgeOddsDecimal: number
): FreeBetResult | null {
  if (freeBetAmount <= 0 || freeBetOddsDecimal <= 1 || hedgeOddsDecimal <= 1) {
    return null;
  }
  // Free bet: if it wins, you get profit only (stake not returned)
  // freeBetPayout = freeBetAmount * (odds - 1)
  // To equalize: hedgeStake = freeBetAmount * (freeBetOdds - 1) / hedgeOdds
  const freeBetProfit = freeBetAmount * (freeBetOddsDecimal - 1);
  const hedgeStake = freeBetProfit / hedgeOddsDecimal;
  const profitIfFreeBetWins = freeBetProfit - hedgeStake;
  const profitIfHedgeWins = hedgeStake * (hedgeOddsDecimal - 1);
  const guaranteedProfit = Math.min(profitIfFreeBetWins, profitIfHedgeWins);
  return {
    hedgeStake: Math.round(hedgeStake * 100) / 100,
    profitIfFreeBetWins: Math.round(profitIfFreeBetWins * 100) / 100,
    profitIfHedgeWins: Math.round(profitIfHedgeWins * 100) / 100,
    guaranteedProfit: Math.round(guaranteedProfit * 100) / 100,
  };
}

// --- Component ---

export function HedgeBetCalculator() {
  const [mode, setMode] = useState<HedgeMode>('two-way');
  const [oddsFormat, setOddsFormat] = useState<OddsFormat>('decimal');

  // Two-way inputs
  const [originalStake, setOriginalStake] = useState('');
  const [originalOdds, setOriginalOdds] = useState('');
  const [hedgeOdds, setHedgeOdds] = useState('');

  // Three-way inputs
  const [totalBudget, setTotalBudget] = useState('');
  const [winOdds, setWinOdds] = useState('');
  const [drawOdds, setDrawOdds] = useState('');
  const [loseOdds, setLoseOdds] = useState('');

  // Free bet inputs
  const [freeBetAmount, setFreeBetAmount] = useState('');
  const [freeBetOdds, setFreeBetOdds] = useState('');
  const [freeBetHedgeOdds, setFreeBetHedgeOdds] = useState('');

  const getTwoWayResult = useCallback((): TwoWayResult | null => {
    const stake = parseFloat(originalStake);
    const origDec = parseOddsToDecimal(originalOdds, oddsFormat);
    const hedgeDec = parseOddsToDecimal(hedgeOdds, oddsFormat);

    if (isNaN(stake) || !origDec || !hedgeDec) return null;
    return calculateTwoWayHedge(stake, origDec, hedgeDec);
  }, [originalStake, originalOdds, hedgeOdds, oddsFormat]);

  const getThreeWayResult = useCallback((): ThreeWayResult | null => {
    const budget = parseFloat(totalBudget);
    const winDec = parseOddsToDecimal(winOdds, oddsFormat);
    const drawDec = parseOddsToDecimal(drawOdds, oddsFormat);
    const loseDec = parseOddsToDecimal(loseOdds, oddsFormat);

    if (isNaN(budget) || !winDec || !drawDec || !loseDec) return null;
    return calculateThreeWayHedge(budget, winDec, drawDec, loseDec);
  }, [totalBudget, winOdds, drawOdds, loseOdds, oddsFormat]);

  const twoWayResult = mode === 'two-way' ? getTwoWayResult() : null;
  const threeWayResult = mode === 'three-way' ? getThreeWayResult() : null;

  const getFreeBetResult = useCallback((): FreeBetResult | null => {
    const amount = parseFloat(freeBetAmount);
    const fbOdds = parseOddsToDecimal(freeBetOdds, oddsFormat);
    const hOdds = parseOddsToDecimal(freeBetHedgeOdds, oddsFormat);
    if (isNaN(amount) || !fbOdds || !hOdds) return null;
    return calculateFreeBetHedge(amount, fbOdds, hOdds);
  }, [freeBetAmount, freeBetOdds, freeBetHedgeOdds, oddsFormat]);

  const freeBetResult = mode === 'free-bet' ? getFreeBetResult() : null;

  const getOddsPlaceholder = (): string => {
    switch (oddsFormat) {
      case 'decimal': return 'e.g. 2.50';
      case 'fractional': return 'e.g. 3/2';
      case 'american': return 'e.g. +150';
    }
  };

  return (
    <div className="hedge-calculator">
      <div className="hedge-calculator__header">
        <h2 className="hedge-calculator__title">Hedge Betting Calculator</h2>
        <p className="hedge-calculator__subtitle">
          Calculate optimal hedge stakes to lock in guaranteed profit regardless of outcome.
        </p>
      </div>

      {/* Mode & Format Controls */}
      <div className="hedge-calculator__controls">
        <div className="hedge-calculator__control-group">
          <label className="hedge-calculator__label" htmlFor="hedge-mode">Mode</label>
          <select
            id="hedge-mode"
            className="hedge-calculator__select"
            value={mode}
            onChange={(e) => setMode(e.target.value as HedgeMode)}
          >
            <option value="two-way">Two-Way Hedge</option>
            <option value="three-way">Three-Way Hedge (Football)</option>
            <option value="free-bet">Free Bet Conversion</option>
          </select>
        </div>

        <div className="hedge-calculator__control-group">
          <label className="hedge-calculator__label" htmlFor="odds-format">Odds Format</label>
          <select
            id="odds-format"
            className="hedge-calculator__select"
            value={oddsFormat}
            onChange={(e) => setOddsFormat(e.target.value as OddsFormat)}
          >
            <option value="decimal">Decimal (e.g. 2.50)</option>
            <option value="fractional">Fractional (e.g. 3/2)</option>
            <option value="american">American (e.g. +150)</option>
          </select>
        </div>
      </div>

      {/* Two-Way Form */}
      {mode === 'two-way' && (
        <div className="hedge-calculator__form">
          <div className="hedge-calculator__info-box">
            <strong>Two-Way Hedge:</strong> You've already placed a bet and want to hedge the opposite outcome to guarantee profit.
            Enter your original bet details and the odds for the <em>opposite</em> outcome you want to hedge.
          </div>

          <div className="hedge-calculator__input-group">
            <label className="hedge-calculator__label" htmlFor="original-stake">
              Original Stake ($)
            </label>
            <input
              id="original-stake"
              className="hedge-calculator__input"
              type="number"
              min="0.01"
              step="0.01"
              placeholder="e.g. 100"
              value={originalStake}
              onChange={(e) => setOriginalStake(e.target.value)}
            />
          </div>

          <div className="hedge-calculator__input-group">
            <label className="hedge-calculator__label" htmlFor="original-odds">
              Original Bet Odds
            </label>
            <input
              id="original-odds"
              className="hedge-calculator__input"
              type="text"
              placeholder={getOddsPlaceholder()}
              value={originalOdds}
              onChange={(e) => setOriginalOdds(e.target.value)}
            />
          </div>

          <div className="hedge-calculator__input-group">
            <label className="hedge-calculator__label" htmlFor="hedge-odds">
              Hedge Bet Odds (opposite outcome)
            </label>
            <input
              id="hedge-odds"
              className="hedge-calculator__input"
              type="text"
              placeholder={getOddsPlaceholder()}
              value={hedgeOdds}
              onChange={(e) => setHedgeOdds(e.target.value)}
            />
          </div>

          {/* Two-Way Results */}
          {twoWayResult && (
            <div className="hedge-calculator__results">
              <h3 className="hedge-calculator__results-title">Results</h3>
              <div className="hedge-calculator__results-grid">
                <div className="hedge-calculator__result-card">
                  <span className="hedge-calculator__result-label">Hedge Stake Needed</span>
                  <span className="hedge-calculator__result-value hedge-calculator__result-value--primary">
                    ${twoWayResult.hedgeStake.toFixed(2)}
                  </span>
                </div>
                <div className="hedge-calculator__result-card">
                  <span className="hedge-calculator__result-label">Total Invested</span>
                  <span className="hedge-calculator__result-value">
                    ${(parseFloat(originalStake) + twoWayResult.hedgeStake).toFixed(2)}
                  </span>
                </div>
                <div className="hedge-calculator__result-card">
                  <span className="hedge-calculator__result-label">Profit if Original Wins</span>
                  <span className={`hedge-calculator__result-value ${twoWayResult.profitIfOriginalWins >= 0 ? 'hedge-calculator__result-value--profit' : 'hedge-calculator__result-value--loss'}`}>
                    ${twoWayResult.profitIfOriginalWins.toFixed(2)}
                  </span>
                </div>
                <div className="hedge-calculator__result-card">
                  <span className="hedge-calculator__result-label">Profit if Hedge Wins</span>
                  <span className={`hedge-calculator__result-value ${twoWayResult.profitIfHedgeWins >= 0 ? 'hedge-calculator__result-value--profit' : 'hedge-calculator__result-value--loss'}`}>
                    ${twoWayResult.profitIfHedgeWins.toFixed(2)}
                  </span>
                </div>
                <div className="hedge-calculator__result-card hedge-calculator__result-card--highlight">
                  <span className="hedge-calculator__result-label">Guaranteed Profit</span>
                  <span className={`hedge-calculator__result-value ${twoWayResult.guaranteedProfit >= 0 ? 'hedge-calculator__result-value--profit' : 'hedge-calculator__result-value--loss'}`}>
                    ${twoWayResult.guaranteedProfit.toFixed(2)}
                  </span>
                </div>
                <div className="hedge-calculator__result-card">
                  <span className="hedge-calculator__result-label">ROI</span>
                  <span className={`hedge-calculator__result-value ${twoWayResult.roi >= 0 ? 'hedge-calculator__result-value--profit' : 'hedge-calculator__result-value--loss'}`}>
                    {twoWayResult.roi.toFixed(2)}%
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Three-Way Form */}
      {mode === 'three-way' && (
        <div className="hedge-calculator__form">
          <div className="hedge-calculator__info-box">
            <strong>Three-Way Hedge (Football):</strong> Distribute your total budget across Win, Draw, and Lose to guarantee profit if arbitrage exists.
          </div>

          <div className="hedge-calculator__input-group">
            <label className="hedge-calculator__label" htmlFor="total-budget">
              Total Budget ($)
            </label>
            <input
              id="total-budget"
              className="hedge-calculator__input"
              type="number"
              min="0.01"
              step="0.01"
              placeholder="e.g. 100"
              value={totalBudget}
              onChange={(e) => setTotalBudget(e.target.value)}
            />
          </div>

          <div className="hedge-calculator__input-row">
            <div className="hedge-calculator__input-group">
              <label className="hedge-calculator__label" htmlFor="win-odds">
                Home Win Odds
              </label>
              <input
                id="win-odds"
                className="hedge-calculator__input"
                type="text"
                placeholder={getOddsPlaceholder()}
                value={winOdds}
                onChange={(e) => setWinOdds(e.target.value)}
              />
            </div>

            <div className="hedge-calculator__input-group">
              <label className="hedge-calculator__label" htmlFor="draw-odds">
                Draw Odds
              </label>
              <input
                id="draw-odds"
                className="hedge-calculator__input"
                type="text"
                placeholder={getOddsPlaceholder()}
                value={drawOdds}
                onChange={(e) => setDrawOdds(e.target.value)}
              />
            </div>

            <div className="hedge-calculator__input-group">
              <label className="hedge-calculator__label" htmlFor="lose-odds">
                Away Win Odds
              </label>
              <input
                id="lose-odds"
                className="hedge-calculator__input"
                type="text"
                placeholder={getOddsPlaceholder()}
                value={loseOdds}
                onChange={(e) => setLoseOdds(e.target.value)}
              />
            </div>
          </div>

          {/* Three-Way Results */}
          {threeWayResult && (
            <div className="hedge-calculator__results">
              <h3 className="hedge-calculator__results-title">Results</h3>

              {threeWayResult.isArbitrage && (
                <div className="hedge-calculator__arb-badge">
                  ✓ Arbitrage Opportunity Detected
                </div>
              )}
              {!threeWayResult.isArbitrage && (
                <div className="hedge-calculator__no-arb-badge">
                  ✗ No arbitrage — combined implied probability exceeds 100%
                </div>
              )}

              <div className="hedge-calculator__stakes-grid">
                <div className="hedge-calculator__stake-card">
                  <span className="hedge-calculator__stake-label">Stake on Win</span>
                  <span className="hedge-calculator__stake-value">${threeWayResult.stakeWin.toFixed(2)}</span>
                  <span className="hedge-calculator__stake-profit">
                    Profit: <span className={threeWayResult.profitIfWin >= 0 ? 'profit' : 'loss'}>
                      ${threeWayResult.profitIfWin.toFixed(2)}
                    </span>
                  </span>
                </div>
                <div className="hedge-calculator__stake-card">
                  <span className="hedge-calculator__stake-label">Stake on Draw</span>
                  <span className="hedge-calculator__stake-value">${threeWayResult.stakeDraw.toFixed(2)}</span>
                  <span className="hedge-calculator__stake-profit">
                    Profit: <span className={threeWayResult.profitIfDraw >= 0 ? 'profit' : 'loss'}>
                      ${threeWayResult.profitIfDraw.toFixed(2)}
                    </span>
                  </span>
                </div>
                <div className="hedge-calculator__stake-card">
                  <span className="hedge-calculator__stake-label">Stake on Lose</span>
                  <span className="hedge-calculator__stake-value">${threeWayResult.stakeLose.toFixed(2)}</span>
                  <span className="hedge-calculator__stake-profit">
                    Profit: <span className={threeWayResult.profitIfLose >= 0 ? 'profit' : 'loss'}>
                      ${threeWayResult.profitIfLose.toFixed(2)}
                    </span>
                  </span>
                </div>
              </div>

              <div className="hedge-calculator__results-grid">
                <div className="hedge-calculator__result-card hedge-calculator__result-card--highlight">
                  <span className="hedge-calculator__result-label">Guaranteed Profit</span>
                  <span className={`hedge-calculator__result-value ${threeWayResult.guaranteedProfit >= 0 ? 'hedge-calculator__result-value--profit' : 'hedge-calculator__result-value--loss'}`}>
                    ${threeWayResult.guaranteedProfit.toFixed(2)}
                  </span>
                </div>
                <div className="hedge-calculator__result-card">
                  <span className="hedge-calculator__result-label">ROI</span>
                  <span className={`hedge-calculator__result-value ${threeWayResult.roi >= 0 ? 'hedge-calculator__result-value--profit' : 'hedge-calculator__result-value--loss'}`}>
                    {threeWayResult.roi.toFixed(2)}%
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Odds Converter Section */}
      {mode === 'free-bet' && (
        <div className="hedge-calculator__form">
          <div className="hedge-calculator__info-box">
            <strong>Free Bet Conversion:</strong> Convert a free/risk-free bet into guaranteed cash.
            With a free bet, you don't lose your stake if it loses — only the profit is paid out if it wins.
            This changes the hedge math in your favor.
          </div>

          <div className="hedge-calculator__input-group">
            <label className="hedge-calculator__label" htmlFor="free-bet-amount">
              Free Bet Amount ($)
            </label>
            <input
              id="free-bet-amount"
              className="hedge-calculator__input"
              type="number"
              min="0.01"
              step="0.01"
              placeholder="e.g. 50"
              value={freeBetAmount}
              onChange={(e) => setFreeBetAmount(e.target.value)}
            />
          </div>

          <div className="hedge-calculator__input-group">
            <label className="hedge-calculator__label" htmlFor="free-bet-odds">
              Free Bet Odds (place the free bet on the underdog for best conversion)
            </label>
            <input
              id="free-bet-odds"
              className="hedge-calculator__input"
              type="text"
              placeholder={getOddsPlaceholder()}
              value={freeBetOdds}
              onChange={(e) => setFreeBetOdds(e.target.value)}
            />
          </div>

          <div className="hedge-calculator__input-group">
            <label className="hedge-calculator__label" htmlFor="free-bet-hedge-odds">
              Hedge Odds (opposite outcome, use your own money)
            </label>
            <input
              id="free-bet-hedge-odds"
              className="hedge-calculator__input"
              type="text"
              placeholder={getOddsPlaceholder()}
              value={freeBetHedgeOdds}
              onChange={(e) => setFreeBetHedgeOdds(e.target.value)}
            />
          </div>

          {freeBetResult && (
            <div className="hedge-calculator__results">
              <h3 className="hedge-calculator__results-title">Results</h3>
              <div className="hedge-calculator__results-grid">
                <div className="hedge-calculator__result-card">
                  <span className="hedge-calculator__result-label">Hedge Stake (Real $)</span>
                  <span className="hedge-calculator__result-value hedge-calculator__result-value--primary">
                    ${freeBetResult.hedgeStake.toFixed(2)}
                  </span>
                </div>
                <div className="hedge-calculator__result-card">
                  <span className="hedge-calculator__result-label">If Free Bet Wins</span>
                  <span className="hedge-calculator__result-value hedge-calculator__result-value--profit">
                    ${freeBetResult.profitIfFreeBetWins.toFixed(2)}
                  </span>
                </div>
                <div className="hedge-calculator__result-card">
                  <span className="hedge-calculator__result-label">If Hedge Wins</span>
                  <span className="hedge-calculator__result-value hedge-calculator__result-value--profit">
                    ${freeBetResult.profitIfHedgeWins.toFixed(2)}
                  </span>
                </div>
                <div className="hedge-calculator__result-card hedge-calculator__result-card--highlight">
                  <span className="hedge-calculator__result-label">Guaranteed Cash</span>
                  <span className="hedge-calculator__result-value hedge-calculator__result-value--profit">
                    ${freeBetResult.guaranteedProfit.toFixed(2)}
                  </span>
                </div>
                <div className="hedge-calculator__result-card">
                  <span className="hedge-calculator__result-label">Conversion Rate</span>
                  <span className="hedge-calculator__result-value hedge-calculator__result-value--profit">
                    {((freeBetResult.guaranteedProfit / parseFloat(freeBetAmount)) * 100).toFixed(1)}%
                  </span>
                </div>
              </div>
              <div className="hedge-calculator__info-box" style={{ marginTop: '12px' }}>
                <strong>Tip:</strong> Higher free bet odds = better conversion rate.
                Aim for odds of +300 or higher (decimal 4.0+) on the free bet for 70%+ conversion.
              </div>
            </div>
          )}
        </div>
      )}

      <OddsConverter />
    </div>
  );
}

// --- Odds Converter Sub-Component ---

function OddsConverter() {
  const [input, setInput] = useState('');
  const [inputFormat, setInputFormat] = useState<OddsFormat>('decimal');

  const decimalValue = parseOddsToDecimal(input, inputFormat);

  return (
    <div className="odds-converter">
      <h3 className="odds-converter__title">Odds Converter</h3>
      <div className="odds-converter__row">
        <div className="odds-converter__input-group">
          <label className="hedge-calculator__label" htmlFor="converter-input">
            Enter Odds
          </label>
          <input
            id="converter-input"
            className="hedge-calculator__input"
            type="text"
            placeholder="Enter odds value"
            value={input}
            onChange={(e) => setInput(e.target.value)}
          />
        </div>
        <div className="odds-converter__input-group">
          <label className="hedge-calculator__label" htmlFor="converter-format">
            Format
          </label>
          <select
            id="converter-format"
            className="hedge-calculator__select"
            value={inputFormat}
            onChange={(e) => setInputFormat(e.target.value as OddsFormat)}
          >
            <option value="decimal">Decimal</option>
            <option value="fractional">Fractional</option>
            <option value="american">American</option>
          </select>
        </div>
      </div>

      {decimalValue && (
        <div className="odds-converter__results">
          <div className="odds-converter__result">
            <span className="odds-converter__format-label">Decimal:</span>
            <span className="odds-converter__format-value">{decimalValue.toFixed(2)}</span>
          </div>
          <div className="odds-converter__result">
            <span className="odds-converter__format-label">Fractional:</span>
            <span className="odds-converter__format-value">{decimalToFractional(decimalValue)}</span>
          </div>
          <div className="odds-converter__result">
            <span className="odds-converter__format-label">American:</span>
            <span className="odds-converter__format-value">{decimalToAmerican(decimalValue)}</span>
          </div>
          <div className="odds-converter__result">
            <span className="odds-converter__format-label">Implied Probability:</span>
            <span className="odds-converter__format-value">{((1 / decimalValue) * 100).toFixed(1)}%</span>
          </div>
        </div>
      )}
    </div>
  );
}

export default HedgeBetCalculator;
