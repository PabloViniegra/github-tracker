# GitHub Activity Tracker API - Frontend Integration Guide

**Version:** 1.0.0
**Base URL:** `http://localhost:8000/api/v1`
**Authentication:** JWT Bearer Token

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication Flow](#authentication-flow)
3. [API Endpoints Reference](#api-endpoints-reference)
4. [Error Handling](#error-handling)
5. [Rate Limiting](#rate-limiting)
6. [Common Workflows](#common-workflows)
7. [Code Examples](#code-examples)

---

## Overview

The GitHub Activity Tracker API provides endpoints for:
- **OAuth Authentication** with GitHub
- **User Profile Management**
- **Repository and Activity Tracking**
- **Real-time Webhook Notifications**

### Key Features

- GitHub OAuth 2.0 authentication
- JWT-based access and refresh tokens
- Per-user rate limiting
- Real-time webhook event notifications
- Comprehensive activity tracking

---

## Authentication Flow

### Step 1: Initiate GitHub OAuth Login

**Endpoint:** `GET /api/v1/auth/github/login`

```javascript
// Client-side code
const response = await fetch('http://localhost:8000/api/v1/auth/github/login');
const data = await response.json();

// Redirect user to GitHub
window.location.href = data.authorization_url;
// Store state token for validation (optional)
sessionStorage.setItem('oauth_state', data.state);
```

**Response:**
```json
{
  "authorization_url": "https://github.com/login/oauth/authorize?client_id=...",
  "state": "secure-random-token"
}
```

### Step 2: Handle OAuth Callback

After user authorizes on GitHub, they will be redirected to:
```
http://localhost:8000/api/v1/auth/github/callback?code=ABC123&state=xyz
```

**The API automatically processes this callback and returns tokens.**

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 900
}
```

### Step 3: Store Tokens

```javascript
// Store tokens securely
localStorage.setItem('access_token', data.access_token);
localStorage.setItem('refresh_token', data.refresh_token);
```

### Step 4: Use Access Token for API Requests

```javascript
const headers = {
  'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
  'Content-Type': 'application/json'
};

const response = await fetch('http://localhost:8000/api/v1/auth/me', { headers });
```

### Step 5: Refresh Expired Access Token

**Endpoint:** `POST /api/v1/auth/refresh`

```javascript
const headers = {
  'Authorization': `Bearer ${localStorage.getItem('refresh_token')}`
};

const response = await fetch('http://localhost:8000/api/v1/auth/refresh', {
  method: 'POST',
  headers
});

const data = await response.json();
localStorage.setItem('access_token', data.access_token);
```

---

## API Endpoints Reference

### Authentication Endpoints

#### 1. **Initiate GitHub OAuth**
```
GET /api/v1/auth/github/login
```
- **Auth Required:** No
- **Rate Limit:** 5/minute
- **Response:** Authorization URL and state token

#### 2. **OAuth Callback** (Handled automatically by API)
```
GET /api/v1/auth/github/callback?code={code}&state={state}
```
- **Auth Required:** No
- **Rate Limit:** 5/minute
- **Response:** JWT tokens

#### 3. **Refresh Access Token**
```
POST /api/v1/auth/refresh
```
- **Auth Required:** Yes (Refresh Token)
- **Rate Limit:** 10/minute
- **Headers:** `Authorization: Bearer {refresh_token}`
- **Response:**
  ```json
  {
    "access_token": "new_token",
    "token_type": "bearer"
  }
  ```

#### 4. **Get Current User**
```
GET /api/v1/auth/me
```
- **Auth Required:** Yes
- **Rate Limit:** 30/minute
- **Headers:** `Authorization: Bearer {access_token}`
- **Response:**
  ```json
  {
    "id": "507f1f77bcf86cd799439011",
    "github_id": 12345,
    "username": "octocat",
    "name": "The Octocat",
    "avatar_url": "https://avatars.githubusercontent.com/u/583231",
    "email": "octocat@github.com",
    "profile_url": "https://github.com/octocat",
    "created_at": "2025-10-20T00:00:00Z",
    "webhook_configured": false
  }
  ```

#### 5. **Logout**
```
POST /api/v1/auth/logout
```
- **Auth Required:** Yes
- **Rate Limit:** 10/minute
- **Response:**
  ```json
  {
    "message": "Logged out successfully"
  }
  ```
- **Note:** Delete tokens from client storage after logout

---

### Activity Endpoints

#### 6. **Get User Repositories**
```
GET /api/v1/activity/repositories
```
- **Auth Required:** Yes
- **Rate Limit:** 50/minute
- **Headers:** `Authorization: Bearer {access_token}`
- **Response:**
  ```json
  {
    "repositories": [
      {
        "id": 123456,
        "name": "my-repo",
        "full_name": "octocat/my-repo",
        "description": "My awesome repository",
        "private": false,
        "html_url": "https://github.com/octocat/my-repo",
        "stargazers_count": 42,
        "language": "JavaScript",
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-10-20T00:00:00Z"
      }
    ]
  }
  ```

#### 7. **Get User Activity Events**
```
GET /api/v1/activity/events
```
- **Auth Required:** Yes
- **Rate Limit:** 50/minute
- **Headers:** `Authorization: Bearer {access_token}`
- **Response:**
  ```json
  {
    "events": [
      {
        "id": "12345",
        "type": "PushEvent",
        "actor": {
          "login": "octocat",
          "avatar_url": "https://avatars.githubusercontent.com/u/583231"
        },
        "repo": {
          "name": "octocat/Hello-World"
        },
        "created_at": "2025-10-20T12:00:00Z"
      }
    ]
  }
  ```

---

### Webhook Endpoints

#### 8. **Setup Webhook on Repository**
```
POST /api/v1/webhooks/setup/{owner}/{repo}
```
- **Auth Required:** Yes
- **Rate Limit:** 5/minute
- **Headers:** `Authorization: Bearer {access_token}`
- **Path Parameters:**
  - `owner`: Repository owner username
  - `repo`: Repository name
- **Example:**
  ```javascript
  const response = await fetch(
    'http://localhost:8000/api/v1/webhooks/setup/octocat/Hello-World',
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    }
  );
  ```
- **Response:**
  ```json
  {
    "message": "Webhook configured successfully",
    "webhook_id": 123456,
    "repository": "octocat/Hello-World",
    "events": ["push", "pull_request", "issues"]
  }
  ```

#### 9. **List Repository Webhooks**
```
GET /api/v1/webhooks/list/{owner}/{repo}
```
- **Auth Required:** Yes
- **Rate Limit:** 10/minute
- **Response:**
  ```json
  {
    "webhooks": [
      {
        "id": 123456,
        "name": "web",
        "active": true,
        "events": ["push", "pull_request"],
        "config": {
          "url": "http://localhost:8000/api/v1/webhooks/github",
          "content_type": "json"
        }
      }
    ]
  }
  ```

#### 10. **Remove Webhook**
```
DELETE /api/v1/webhooks/remove/{owner}/{repo}/{hook_id}
```
- **Auth Required:** Yes
- **Rate Limit:** 5/minute
- **Path Parameters:**
  - `owner`: Repository owner
  - `repo`: Repository name
  - `hook_id`: Webhook ID to delete
- **Response:**
  ```json
  {
    "message": "Webhook deleted successfully"
  }
  ```

#### 11. **Get Webhook Notifications**
```
GET /api/v1/webhooks/notifications?processed=false&limit=50
```
- **Auth Required:** Yes
- **Rate Limit:** 30/minute
- **Query Parameters:**
  - `processed` (optional): `true` | `false` | omit for all
  - `limit` (optional): 1-100, default 50
- **Response:**
  ```json
  {
    "notifications": [
      {
        "id": "507f1f77bcf86cd799439011",
        "repository": "octocat/Hello-World",
        "event_type": "push",
        "action": "created",
        "created_at": "2025-10-20T12:00:00Z",
        "processed": false
      }
    ]
  }
  ```

#### 12. **Mark Notification as Processed**
```
POST /api/v1/webhooks/notifications/{notification_id}/mark-processed
```
- **Auth Required:** Yes
- **Rate Limit:** 30/minute
- **Response:**
  ```json
  {
    "message": "Notification marked as processed"
  }
  ```

#### 13. **Mark All Notifications as Processed**
```
POST /api/v1/webhooks/notifications/mark-all-processed
```
- **Auth Required:** Yes
- **Rate Limit:** 10/minute
- **Response:**
  ```json
  {
    "message": "All notifications marked as processed"
  }
  ```

---

## Error Handling

### Standard Error Response Format

```json
{
  "detail": "Error message description"
}
```

### Common HTTP Status Codes

| Status Code | Meaning | Common Causes |
|-------------|---------|---------------|
| `400` | Bad Request | Invalid parameters, malformed request |
| `401` | Unauthorized | Missing/invalid token, expired token |
| `403` | Forbidden | Insufficient permissions |
| `404` | Not Found | Resource doesn't exist |
| `422` | Unprocessable Entity | Validation error, duplicate resource |
| `429` | Too Many Requests | Rate limit exceeded |
| `500` | Internal Server Error | Server-side error |

### Error Handling Example

```javascript
async function apiRequest(url, options) {
  try {
    const response = await fetch(url, options);

    if (!response.ok) {
      const error = await response.json();

      switch (response.status) {
        case 401:
          // Token expired, try to refresh
          await refreshAccessToken();
          // Retry request
          return apiRequest(url, options);

        case 429:
          console.error('Rate limit exceeded');
          throw new Error('Too many requests. Please wait.');

        case 500:
          console.error('Server error:', error.detail);
          throw new Error('Server error. Please try again later.');

        default:
          throw new Error(error.detail || 'Unknown error');
      }
    }

    return await response.json();
  } catch (error) {
    console.error('API request failed:', error);
    throw error;
  }
}
```

---

## Rate Limiting

The API implements per-user rate limiting with the following limits:

| Endpoint Category | Rate Limit |
|-------------------|------------|
| Authentication | 5 requests/minute |
| Activity | 50 requests/minute |
| Webhooks (read) | 30 requests/minute |
| Webhooks (write) | 5 requests/minute |
| General | 100 requests/minute |

### Rate Limit Headers

Every response includes rate limit information:

```
X-RateLimit-Limit: 50
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1634567890
```

### Handling Rate Limits

```javascript
function checkRateLimit(response) {
  const limit = response.headers.get('X-RateLimit-Limit');
  const remaining = response.headers.get('X-RateLimit-Remaining');
  const reset = response.headers.get('X-RateLimit-Reset');

  console.log(`Rate limit: ${remaining}/${limit}`);

  if (remaining < 10) {
    console.warn('Approaching rate limit!');
  }

  if (response.status === 429) {
    const waitTime = (parseInt(reset) * 1000) - Date.now();
    console.error(`Rate limited. Retry after ${waitTime}ms`);
  }
}
```

---

## Common Workflows

### Complete Authentication Flow

```javascript
// 1. Start OAuth flow
async function login() {
  const response = await fetch('http://localhost:8000/api/v1/auth/github/login');
  const { authorization_url } = await response.json();
  window.location.href = authorization_url;
}

// 2. After redirect, handle callback (URL will have tokens in query params)
// Your backend should handle the callback and redirect to your app with tokens

// 3. Store tokens
function storeTokens(accessToken, refreshToken) {
  localStorage.setItem('access_token', accessToken);
  localStorage.setItem('refresh_token', refreshToken);
}

// 4. Get user profile
async function getUserProfile() {
  const response = await fetch('http://localhost:8000/api/v1/auth/me', {
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('access_token')}`
    }
  });
  return await response.json();
}
```

### Setup and Monitor Webhooks

```javascript
// 1. Setup webhook on a repository
async function setupWebhook(owner, repo) {
  const response = await fetch(
    `http://localhost:8000/api/v1/webhooks/setup/${owner}/${repo}`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('access_token')}`
      }
    }
  );
  return await response.json();
}

// 2. Poll for new notifications (or use WebSocket for real-time)
async function getUnprocessedNotifications() {
  const response = await fetch(
    'http://localhost:8000/api/v1/webhooks/notifications?processed=false&limit=20',
    {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('access_token')}`
      }
    }
  );
  return await response.json();
}

// 3. Mark notification as seen
async function markNotificationProcessed(notificationId) {
  await fetch(
    `http://localhost:8000/api/v1/webhooks/notifications/${notificationId}/mark-processed`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('access_token')}`
      }
    }
  );
}
```

### Fetch User Activity

```javascript
async function getUserActivity() {
  const [repos, events] = await Promise.all([
    fetch('http://localhost:8000/api/v1/activity/repositories', {
      headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` }
    }).then(r => r.json()),

    fetch('http://localhost:8000/api/v1/activity/events', {
      headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` }
    }).then(r => r.json())
  ]);

  return { repositories: repos.repositories, events: events.events };
}
```

---

## Code Examples

### React Hook for API Calls

```javascript
import { useState, useEffect } from 'react';

function useApi(endpoint, options = {}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchData() {
      try {
        const token = localStorage.getItem('access_token');
        const response = await fetch(`http://localhost:8000/api/v1${endpoint}`, {
          ...options,
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
            ...options.headers
          }
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        setData(result);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [endpoint]);

  return { data, loading, error };
}

// Usage
function UserProfile() {
  const { data, loading, error } = useApi('/auth/me');

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div>
      <h1>{data.name}</h1>
      <p>@{data.username}</p>
    </div>
  );
}
```

### API Client Class

```javascript
class GitHubTrackerAPI {
  constructor(baseURL = 'http://localhost:8000/api/v1') {
    this.baseURL = baseURL;
  }

  async request(endpoint, options = {}) {
    const token = localStorage.getItem('access_token');

    const response = await fetch(`${this.baseURL}${endpoint}`, {
      ...options,
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
        ...options.headers
      }
    });

    if (response.status === 401) {
      // Try to refresh token
      await this.refreshToken();
      // Retry request
      return this.request(endpoint, options);
    }

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'API request failed');
    }

    return await response.json();
  }

  async refreshToken() {
    const refreshToken = localStorage.getItem('refresh_token');
    const response = await fetch(`${this.baseURL}/auth/refresh`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${refreshToken}`
      }
    });

    const { access_token } = await response.json();
    localStorage.setItem('access_token', access_token);
  }

  // Auth methods
  async login() {
    return this.request('/auth/github/login');
  }

  async getMe() {
    return this.request('/auth/me');
  }

  async logout() {
    const result = await this.request('/auth/logout', { method: 'POST' });
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    return result;
  }

  // Activity methods
  async getRepositories() {
    return this.request('/activity/repositories');
  }

  async getEvents() {
    return this.request('/activity/events');
  }

  // Webhook methods
  async setupWebhook(owner, repo) {
    return this.request(`/webhooks/setup/${owner}/${repo}`, { method: 'POST' });
  }

  async getNotifications(processed = null, limit = 50) {
    const params = new URLSearchParams();
    if (processed !== null) params.append('processed', processed);
    params.append('limit', limit);
    return this.request(`/webhooks/notifications?${params}`);
  }

  async markNotificationProcessed(notificationId) {
    return this.request(
      `/webhooks/notifications/${notificationId}/mark-processed`,
      { method: 'POST' }
    );
  }
}

// Usage
const api = new GitHubTrackerAPI();

// Get user profile
const user = await api.getMe();

// Get repositories
const repos = await api.getRepositories();

// Setup webhook
await api.setupWebhook('octocat', 'Hello-World');
```

---

## Additional Notes

### CORS Configuration

The API is configured to accept requests from `http://localhost:8002` (configurable via `FRONTEND_URL` env variable).

Allowed methods: `GET`, `POST`, `PUT`, `DELETE`, `OPTIONS`

### Token Expiration

- **Access Token:** Expires in 15 minutes
- **Refresh Token:** Expires in 7 days

Always implement token refresh logic to maintain user sessions.

### Webhook Events Tracked

The following GitHub events are monitored:
- `push`
- `pull_request`
- `issues`
- `issue_comment`
- `commit_comment`
- `create`
- `delete`
- `fork`
- `star`
- `watch`
- `release`

---

## Support

For API documentation, visit: `http://localhost:8000/docs` (Swagger UI)

For alternative documentation: `http://localhost:8000/redoc` (ReDoc)

Health check endpoint: `GET /health`

---

**Last Updated:** 2025-10-20
**API Version:** 1.0.0
