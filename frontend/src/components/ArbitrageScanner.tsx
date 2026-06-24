import { useState, useEffect, useRef } from 'react';
import { fetchArbitrage, fetchSports, fetchQuickScan } from '../api';
import type { ArbitrageResponse, ArbitrageEvent, SportItem } from '../types';
import './ArbitrageScanner.css';

interface ArbitrageScannerProps {
  active: boolean;
}

export function ArbitrageScanner({ active }: ArbitrageScannerProps) {
  const [data, setData] = useState<ArbitrageResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sport, setSport] = useState('soccer_fifa_world_cup');
  const [markets, setMarkets] = useState('h2h');
  const [budget, setBudget] = useState('100');
  const [watchMode, setWatchMode] = useState(false);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);
  const [newArbs, setNewArbs] = useState<Set<string>>(new Set());
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const prevArbIdsRef = useRef<Set<string>>(new Set());

  // Dynamic sports list
  const [activeSports, setActiveSports] = useState<SportItem[]>([]);
  const [inactiveSports, setInactiveSports] = useState<SportItem[]>([]);
  const [sportsTab, setSportsTab] = useState<'active' | 'inactive'>('active');
  const [sportsLoading, setSportsLoading] = useState(false);

  // Fetch sports list on mount
  useEffect(() => {
    const loadSports = async () => {
      setSportsLoading(true);
      try {
        const result = await fetchSports();
        setActiveSports(result.active);
        setInactiveSports(result.inactive);
      } catch {
        // Fallback to a minimal list if API fails
        setActiveSports([
          { key: 'soccer_fifa_world_cup', title: 'FIFA World Cup', group: 'Soccer', description: '', has_outrights: false },
        ]);
      } finally {
        setSportsLoading(false);
      }
    };
    loadSports();
  }, []);

  const MARKET_OPTIONS = [
    { key: 'h2h', label: 'Moneyline' },
    { key: 'h2h,spreads', label: 'Moneyline + Spreads' },
    { key: 'h2h,spreads,totals', label: 'All Markets' },
    { key: 'spreads', label: 'Spreads Only' },
    { key: 'totals', label: 'Totals (O/U) Only' },
  ];

  const currentSportsList = sportsTab === 'active' ? activeSports : inactiveSports;

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchArbitrage(sport, markets);
      // Detect new arb opportunities for watch mode alerts
      const currentArbIds = new Set(
        result.events.filter(e => e.is_arbitrage).map(e => e.event_id)
      );
      const freshArbs = new Set<string>();
      currentArbIds.forEach(id => {
        if (!prevArbIdsRef.current.has(id)) {
          freshArbs.add(id);
        }
      });
      if (freshArbs.size > 0 && watchMode) {
        setNewArbs(freshArbs);
        // Clear highlight after 10 seconds
        setTimeout(() => setNewArbs(new Set()), 10000);
      }
      prevArbIdsRef.current = currentArbIds;
      setData(result);
      setLastRefresh(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (active) {
      loadData();
    }
  }, [active, sport, markets]);

  // Watch mode: auto-refresh every 60 seconds
  useEffect(() => {
    if (watchMode && active) {
      intervalRef.current = setInterval(loadData, 60000);
      return () => {
        if (intervalRef.current) clearInterval(intervalRef.current);
      };
    } else {
      if (intervalRef.current) clearInterval(intervalRef.current);
    }
  }, [watchMode, active, sport, markets]);

  const budgetNum = parseFloat(budget) || 100;

  return (
    <div className="arb-scanner">
      <div className="arb-scanner__header">
        <h2 className="arb-scanner__title">Arbitrage Scanner</h2>
        <p className="arb-scanner__subtitle">
          Live odds comparison across bookmakers. Highlights opportunities where you can guarantee profit.
        </p>
      </div>

      <div className="arb-scanner__controls">
        <div className="arb-scanner__control-group arb-scanner__control-group--sport">
          <label className="arb-scanner__label">Sport</label>
          <div className="arb-scanner__sport-tabs">
            <button
              className={`arb-scanner__sport-tab ${sportsTab === 'active' ? 'arb-scanner__sport-tab--active' : ''}`}
              onClick={() => setSportsTab('active')}
            >
              Active ({activeSports.length})
            </button>
            <button
              className={`arb-scanner__sport-tab ${sportsTab === 'inactive' ? 'arb-scanner__sport-tab--active' : ''}`}
              onClick={() => setSportsTab('inactive')}
            >
              Inactive ({inactiveSports.length})
            </button>
          </div>
          <select
            id="arb-sport"
            className="arb-scanner__select"
            value={sport}
            onChange={(e) => setSport(e.target.value)}
          >
            {sportsLoading && <option>Loading sports...</option>}
            {currentSportsList.map((s) => (
              <option key={s.key} value={s.key}>{s.group} — {s.title}</option>
            ))}
          </select>
        </div>
        <div className="arb-scanner__control-group">
          <label className="arb-scanner__label" htmlFor="arb-markets">Markets</label>
          <select
            id="arb-markets"
            className="arb-scanner__select"
            value={markets}
            onChange={(e) => setMarkets(e.target.value)}
          >
            {MARKET_OPTIONS.map((m) => (
              <option key={m.key} value={m.key}>{m.label}</option>
            ))}
          </select>
        </div>
        <div className="arb-scanner__control-group">
          <label className="arb-scanner__label" htmlFor="arb-budget">Budget ($)</label>
          <input
            id="arb-budget"
            className="arb-scanner__input"
            type="number"
            min="1"
            step="1"
            value={budget}
            onChange={(e) => setBudget(e.target.value)}
          />
        </div>
        <div className="arb-scanner__control-group arb-scanner__control-group--row">
          <label className="arb-scanner__watch-label">
            <input
              type="checkbox"
              checked={watchMode}
              onChange={(e) => setWatchMode(e.target.checked)}
            />
            Watch Mode (auto-refresh 60s)
          </label>
          {watchMode && lastRefresh && (
            <span className="arb-scanner__last-refresh">
              Last: {lastRefresh.toLocaleTimeString()}
            </span>
          )}
        </div>
        <button
          className="arb-scanner__refresh-btn"
          onClick={loadData}
          disabled={loading}
          aria-label="Refresh arbitrage scan"
        >
          {loading ? 'Scanning...' : '↻ Scan Now'}
        </button>
        <button
          className="arb-scanner__refresh-btn arb-scanner__quick-scan-btn"
          onClick={async () => {
            setLoading(true);
            setError(null);
            try {
              const result = await fetchQuickScan(markets);
              setData(result);
              setLastRefresh(new Date());
            } catch (err) {
              setError(err instanceof Error ? err.message : 'Quick scan failed');
            } finally {
              setLoading(false);
            }
          }}
          disabled={loading}
          aria-label="Quick scan popular sports"
        >
          {loading ? 'Scanning...' : '⚡ Quick Scan All Popular'}
        </button>
      </div>

      {error && (
        <div className="arb-scanner__error">
          {error}. Make sure the backend server is running (uvicorn backend.main:app).
        </div>
      )}

      {data && !loading && (
        <>
          <div className="arb-scanner__summary">
            <div className="arb-scanner__stat">
              <span className="arb-scanner__stat-value">{data.total_events}</span>
              <span className="arb-scanner__stat-label">Events Scanned</span>
            </div>
            <div className={`arb-scanner__stat ${data.arbitrage_found > 0 ? 'arb-scanner__stat--highlight' : ''}`}>
              <span className="arb-scanner__stat-value">{data.arbitrage_found}</span>
              <span className="arb-scanner__stat-label">Arb Opportunities</span>
            </div>
            <div className="arb-scanner__stat">
              <span className="arb-scanner__stat-value">{data.quota_remaining}</span>
              <span className="arb-scanner__stat-label">API Quota Left</span>
            </div>
          </div>

          {data.events.length === 0 && (
            <div className="arb-scanner__empty">
              No events found for this sport. It may be out of season or no odds are currently available.
            </div>
          )}

          <div className="arb-scanner__events">
            {data.events.map((event) => (
              <EventCard key={event.event_id} event={event} budget={budgetNum} isNew={newArbs.has(event.event_id)} />
            ))}
          </div>
        </>
      )}

      {loading && (
        <div className="arb-scanner__loading">
          Scanning bookmakers for opportunities...
        </div>
      )}
    </div>
  );
}

function EventCard({ event, budget, isNew }: { event: ArbitrageEvent; budget: number; isNew: boolean }) {
  const [expanded, setExpanded] = useState(false);
  const date = new Date(event.commence_time).toLocaleDateString(undefined, {
    month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit',
  });

  // Scale stakes to custom budget
  const scaleFactor = budget / 100;

  return (
    <div className={`arb-event ${event.is_arbitrage ? 'arb-event--arb' : ''} ${isNew ? 'arb-event--new' : ''}`}>
      {isNew && <div className="arb-event__new-badge">🚨 NEW</div>}
      <div className="arb-event__header" onClick={() => setExpanded(!expanded)} role="button" tabIndex={0} aria-expanded={expanded}>
        <div className="arb-event__teams">
          <span className="arb-event__team">{event.home_team}</span>
          <span className="arb-event__vs">vs</span>
          <span className="arb-event__team">{event.away_team}</span>
          {event.market_label && (
            <span className="arb-event__market-tag">{event.market_label}</span>
          )}
        </div>
        <div className="arb-event__meta">
          <span className="arb-event__date">{date}</span>
          {event.is_arbitrage ? (
            <span className="arb-event__badge arb-event__badge--arb">
              +{event.profit_pct.toFixed(2)}% ARB
            </span>
          ) : (
            <span className="arb-event__badge arb-event__badge--margin">
              {event.implied_probability.toFixed(1)}% margin
            </span>
          )}
        </div>
      </div>

      <div className="arb-event__best-odds">
        <div className="arb-event__odd">
          <span className="arb-event__odd-label">{event.home_team}</span>
          <span className="arb-event__odd-value">{event.best_odds.home.price.toFixed(2)}</span>
          <span className="arb-event__odd-book">{event.best_odds.home.bookmaker}</span>
        </div>
        {event.best_odds.draw && (
          <div className="arb-event__odd">
            <span className="arb-event__odd-label">Draw</span>
            <span className="arb-event__odd-value">{event.best_odds.draw.price.toFixed(2)}</span>
            <span className="arb-event__odd-book">{event.best_odds.draw.bookmaker}</span>
          </div>
        )}
        <div className="arb-event__odd">
          <span className="arb-event__odd-label">{event.away_team}</span>
          <span className="arb-event__odd-value">{event.best_odds.away.price.toFixed(2)}</span>
          <span className="arb-event__odd-book">{event.best_odds.away.bookmaker}</span>
        </div>
      </div>

      {event.is_arbitrage && event.stakes && (
        <div className="arb-event__stakes">
          <div className="arb-event__stakes-title">Optimal Stakes (${budget.toFixed(0)} budget)</div>
          <div className="arb-event__stakes-grid">
            <div className="arb-event__stake-item">
              <span>{event.home_team}</span>
              <strong>${(event.stakes.home * scaleFactor).toFixed(2)}</strong>
              <span className="arb-event__stake-book">@ {event.best_odds.home.bookmaker}</span>
            </div>
            {event.stakes.draw !== undefined && (
              <div className="arb-event__stake-item">
                <span>Draw</span>
                <strong>${(event.stakes.draw * scaleFactor).toFixed(2)}</strong>
                <span className="arb-event__stake-book">@ {event.best_odds.draw?.bookmaker}</span>
              </div>
            )}
            <div className="arb-event__stake-item">
              <span>{event.away_team}</span>
              <strong>${(event.stakes.away * scaleFactor).toFixed(2)}</strong>
              <span className="arb-event__stake-book">@ {event.best_odds.away.bookmaker}</span>
            </div>
          </div>
          <div className="arb-event__profit">
            Guaranteed Profit: <strong>${(event.stakes.guaranteed_profit * scaleFactor).toFixed(2)}</strong>
          </div>
        </div>
      )}

      {expanded && (
        <div className="arb-event__details">
          <h4>All Bookmaker Odds ({event.bookmaker_count} books)</h4>
          <table className="arb-event__table">
            <thead>
              <tr>
                <th>Bookmaker</th>
                <th>{event.home_team}</th>
                {event.best_odds.draw && <th>Draw</th>}
                <th>{event.away_team}</th>
              </tr>
            </thead>
            <tbody>
              {event.all_bookmaker_odds.map((bk, i) => (
                <tr key={i}>
                  <td>{bk.bookmaker}</td>
                  <td className={bk.home === event.best_odds.home.price ? 'arb-event__best' : ''}>
                    {bk.home?.toFixed(2) ?? '-'}
                  </td>
                  {event.best_odds.draw && (
                    <td className={bk.draw === event.best_odds.draw?.price ? 'arb-event__best' : ''}>
                      {bk.draw?.toFixed(2) ?? '-'}
                    </td>
                  )}
                  <td className={bk.away === event.best_odds.away.price ? 'arb-event__best' : ''}>
                    {bk.away?.toFixed(2) ?? '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default ArbitrageScanner;
