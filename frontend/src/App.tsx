import { useState } from 'react';
import { GroupStageView } from './components/GroupStageView';
import { KnockoutBracketView } from './components/KnockoutBracketView';
import { HedgeBetCalculator } from './components/HedgeBetCalculator';
import { ArbitrageScanner } from './components/ArbitrageScanner';
import './App.css';

type Tab = 'groups' | 'knockout' | 'hedge' | 'arbitrage';

function App() {
  const [activeTab, setActiveTab] = useState<Tab>('groups');
  const [refreshKey, setRefreshKey] = useState(0);

  const handleRefresh = () => {
    setRefreshKey((prev) => prev + 1);
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1 className="app-title">World Cup 2026 Predictor</h1>
        <button className="app-refresh-btn" onClick={handleRefresh} aria-label="Refresh data">
          ↻ Refresh
        </button>
      </header>

      <nav className="app-tabs" role="tablist" aria-label="Dashboard views">
        <button
          className={`app-tab${activeTab === 'groups' ? ' app-tab--active' : ''}`}
          role="tab"
          aria-selected={activeTab === 'groups'}
          aria-controls="panel-groups"
          id="tab-groups"
          onClick={() => setActiveTab('groups')}
        >
          Group Stage
        </button>
        <button
          className={`app-tab${activeTab === 'knockout' ? ' app-tab--active' : ''}`}
          role="tab"
          aria-selected={activeTab === 'knockout'}
          aria-controls="panel-knockout"
          id="tab-knockout"
          onClick={() => setActiveTab('knockout')}
        >
          Knockout Bracket
        </button>
        <button
          className={`app-tab${activeTab === 'hedge' ? ' app-tab--active' : ''}`}
          role="tab"
          aria-selected={activeTab === 'hedge'}
          aria-controls="panel-hedge"
          id="tab-hedge"
          onClick={() => setActiveTab('hedge')}
        >
          Hedge Calculator
        </button>
        <button
          className={`app-tab${activeTab === 'arbitrage' ? ' app-tab--active' : ''}`}
          role="tab"
          aria-selected={activeTab === 'arbitrage'}
          aria-controls="panel-arbitrage"
          id="tab-arbitrage"
          onClick={() => setActiveTab('arbitrage')}
        >
          Arb Scanner
        </button>
      </nav>

      <main className="app-content">
        <div
          id="panel-groups"
          role="tabpanel"
          aria-labelledby="tab-groups"
          hidden={activeTab !== 'groups'}
        >
          {activeTab === 'groups' && (
            <GroupStageView key={`groups-${refreshKey}`} active={true} />
          )}
        </div>
        <div
          id="panel-knockout"
          role="tabpanel"
          aria-labelledby="tab-knockout"
          hidden={activeTab !== 'knockout'}
        >
          {activeTab === 'knockout' && (
            <KnockoutBracketView key={`knockout-${refreshKey}`} active={true} />
          )}
        </div>
        <div
          id="panel-hedge"
          role="tabpanel"
          aria-labelledby="tab-hedge"
          hidden={activeTab !== 'hedge'}
        >
          {activeTab === 'hedge' && <HedgeBetCalculator />}
        </div>
        <div
          id="panel-arbitrage"
          role="tabpanel"
          aria-labelledby="tab-arbitrage"
          hidden={activeTab !== 'arbitrage'}
        >
          {activeTab === 'arbitrage' && <ArbitrageScanner active={true} />}
        </div>
      </main>
    </div>
  );
}

export default App;
