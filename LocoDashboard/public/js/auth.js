'use strict';

const DASHBOARD_API = (window.__LOCO_CONFIG__ && window.__LOCO_CONFIG__.dashboardApiBaseUrl)
  || 'http://127.0.0.1:9000';
const AUTH_TOKEN_KEY = 'loco_token';

function getToken() {
  return localStorage.getItem(AUTH_TOKEN_KEY);
}

function checkAuth() {
  if (!getToken()) {
    location.href = '/login.html';
    return false;
  }
  return true;
}

function logout() {
  localStorage.removeItem(AUTH_TOKEN_KEY);
  location.href = '/login.html';
}

function authHeaders() {
  return { 'Authorization': 'Bearer ' + getToken() };
}
