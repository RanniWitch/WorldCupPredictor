import type { GroupsResponse, PredictionsResponse, KnockoutResponse } from "./types";

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
