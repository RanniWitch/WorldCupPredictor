import type { GroupsResponse, PredictionsResponse, KnockoutResponse, ArbitrageResponse, SportsResponse } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export async function fetchGroups(): Promise<GroupsResponse> {
  const response = await fetch(`${API_BASE}/api/groups`);
  if (!response.ok) {
    throw new Error(`Failed to fetch groups: ${response.status}`);
  }
  return response.json();
}

export async function fetchPredictions(): Promise<PredictionsResponse> {
  const response = await fetch(`${API_BASE}/api/predictions`);
  if (!response.ok) {
    throw new Error(`Failed to fetch predictions: ${response.status}`);
  }
  return response.json();
}

export async function fetchKnockout(): Promise<KnockoutResponse> {
  const response = await fetch(`${API_BASE}/api/knockout`);
  if (!response.ok) {
    throw new Error(`Failed to fetch knockout: ${response.status}`);
  }
  return response.json();
}

export async function fetchArbitrage(sport: string = "soccer_fifa_world_cup", markets: string = "h2h"): Promise<ArbitrageResponse> {
  const response = await fetch(`${API_BASE}/api/arbitrage?sport=${encodeURIComponent(sport)}&markets=${encodeURIComponent(markets)}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch arbitrage data: ${response.status}`);
  }
  return response.json();
}


export async function fetchSports(): Promise<SportsResponse> {
  const response = await fetch(`${API_BASE}/api/sports`);
  if (!response.ok) {
    throw new Error(`Failed to fetch sports: ${response.status}`);
  }
  return response.json();
}

export async function fetchQuickScan(markets: string = "h2h"): Promise<ArbitrageResponse & { sports_scanned: string[] }> {
  const response = await fetch(`${API_BASE}/api/arbitrage/quick-scan?markets=${encodeURIComponent(markets)}`);
  if (!response.ok) {
    throw new Error(`Failed to run quick scan: ${response.status}`);
  }
  return response.json();
}
