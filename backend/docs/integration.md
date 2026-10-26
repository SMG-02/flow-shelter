# FlowShelter API — Integration Guide

Everything a frontend (React web or Flet mobile) needs to register a user,
walk them through onboarding, and render their financial dashboard.

- **Base URL (local):** `http://127.0.0.1:8000`
- **Base URL (deployed):** your Azure / Vercel URL, e.g. `https://app-flowshelter-dev.azurewebsites.net`
- **Content type:** `application/json` on every request with a body
- **Auth:** `Authorization: Bearer <access_token>` on every endpoint except register and login
- **Interactive docs:** `${BASE_URL}/docs`

> **Money is a string.** Every amount (`"18450.00"`) is returned as a decimal
> string so no precision is lost. Send amounts as a string or a number; render
> them with the user's `currency` (e.g. `R 18 450,00`).
>
> **Dates are ISO `YYYY-MM-DD`.** Timestamps (`updated_at`) are ISO 8601 UTC.

## Quick start

| # | Method | Path | Auth | Purpose |
|---|---|---|---|---|
| 1 | `POST` | `/auth/register` | — | Create an account |
| 2 | `POST` | `/auth/login` | — | Get an access token |
| 3 | `GET` | `/auth/me` | ✓ | Current user (use to validate a stored token) |
| 4 | `GET` | `/api/onboarding` | ✓ | Load the saved draft (resume onboarding) |
| 5 | `PATCH` | `/api/onboarding` | ✓ | Save progress (any subset of sections) |
| 6 | `PUT` | `/api/onboarding/step` | ✓ | Record which step the user is on |
| 7 | `POST` | `/api/onboarding/complete` | ✓ | Validate and finalise onboarding |
| 8 | `GET` | `/api/onboarding/commitments` | ✓ | Load the user's commitments |
| 9 | `PUT` | `/api/onboarding/commitments` | ✓ | Replace the commitment list |
| 10 | `GET` | `/api/dashboard/overview` | ✓ | Dashboard data |
| 11 | `GET` | `/api/dashboard/upcoming` | ✓ | Unpaid commitments inside the horizon |
| 12 | `GET` | `/api/dashboard/alerts` | ✓ | Alerts only |
| 13 | `GET` | `/api/cashflow/timeline` | ✓ | Cash-flow timeline with running balance |
| 14 | `GET`/`POST` | `/api/transactions` | ✓ | List a month / add a transaction |
| 15 | `GET` | `/api/transactions/options` | ✓ | Dropdown values for the form |
| 16 | `GET`/`PATCH`/`DELETE` | `/api/transactions/{id}` | ✓ | Load / edit / delete one |
| 17 | `POST` | `/api/transactions/{id}/confirm` | ✓ | Mark received / mark paid |
| 18 | `POST` | `/api/transactions/incomes/{id}/mark-received` | ✓ | Confirm an onboarding income |
| 19 | `POST` | `/api/transactions/commitments/{id}/mark-paid` | ✓ | Confirm an onboarding commitment |
| 20 | `GET`/`POST` | `/api/goals` | ✓ | List / create savings goals |
| 21 | `GET`/`PATCH`/`DELETE` | `/api/goals/{id}` | ✓ | Load / edit / delete a goal |
| 22 | `POST` | `/api/goals/{id}/contributions` | ✓ | Record money put aside |

Health checks (no auth): `GET /`, `GET /health`, `GET /health/database`.

### Suggested client flow

```text
register ──▶ login (store token) ──▶ GET /api/onboarding
                                        │
                     is_complete? ──yes──┼──▶ GET /api/dashboard/overview
                                        │no
                                        ▼
             show step current_step ──▶ PATCH /api/onboarding + PUT /step
                                        │  (repeat until step 5)
                                        ▼
                       POST /api/onboarding/complete
                                        │
                                        ▼
                       GET /api/dashboard/overview
```

## Common errors

| Status | Meaning | Response shape |
|---|---|---|
| `401` | Token missing, invalid, expired, or user deleted/disabled | `{"detail": "Invalid or expired token"}` |
| `403` | `Authorization` header missing or not `Bearer <token>` | `{"detail": "Not authenticated"}` |
| `409` | Register: email already used | `{"detail": "Email already registered"}` |
| `422` | Body failed validation, or onboarding incomplete | `{"detail": [...]}` or `{"detail": {"message": ..., "missing": [...]}}` |
| `503` | Database unreachable (health endpoint) | `{"detail": "Database unavailable"}` |

---

## 1. Register

`POST /auth/register` → **201**

Request:

```json
{
  "name": "Thandi Dlamini",
  "email": "thandi@example.com",
  "password": "correct-horse-battery"
}
```

| Field | Type | Rules |
|---|---|---|
| `name` | string | 2–100 characters |
| `email` | string | Valid email; stored lowercased (case-insensitive) |
| `password` | string | 12–128 characters |

Response `201`:

```json
{
  "id": 1,
  "name": "Thandi Dlamini",
  "email": "thandi@example.com",
  "is_active": true
}
```

Errors:

- `409` — `{"detail": "Email already registered"}`
- `422` — e.g. `{"detail": [{"loc": ["body", "password"], "msg": "String should have at least 12 characters", "type": "string_too_short"}]}`

## 2. Login

`POST /auth/login` → **200**

Request:

```json
{
  "email": "thandi@example.com",
  "password": "correct-horse-battery"
}
```

Response `200`:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

- Tokens expire after 30 minutes (`ACCESS_TOKEN_EXPIRE_MINUTES`). On `401`, send the user back to login.
- `401` — `{"detail": "Invalid email or password"}` (same message for unknown email and wrong password)
- `403` — `{"detail": "Account is disabled"}`

From here on, every request includes:

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## 3. Current user

`GET /auth/me` → **200**

Use this on app start to check whether a stored token is still valid.

```json
{
  "id": 1,
  "name": "Thandi Dlamini",
  "email": "thandi@example.com",
  "is_active": true
}
```

---

## 4. Load onboarding draft

`GET /api/onboarding` → **200**

Call this immediately after login. It is always safe to call: on first use the
server creates an empty draft, so a new user gets `current_step: 1` rather than
a `404`. `current_step` tells you which screen to open.

Response `200` — new user:

```json
{
  "current_step": 1,
  "is_complete": false,
  "financial_profile": null,
  "financial_balance": null,
  "expected_incomes": [],
  "savings_goals": [],
  "updated_at": "2026-10-25T09:12:41.123456Z"
}
```

Response `200` — user who saved some progress:

```json
{
  "current_step": 3,
  "is_complete": false,
  "financial_profile": {
    "work_type": "Graphic designer",
    "income_pattern": "irregular",
    "typical_income": null,
    "currency": "ZAR"
  },
  "financial_balance": {
    "available_balance": "18450.00",
    "existing_savings": "0.00"
  },
  "expected_incomes": [
    {
      "id": 7,
      "source": "Mokoena Studio project",
      "amount": "12000.00",
      "expected_date": "2026-11-05",
      "status": "expected"
    }
  ],
  "savings_goals": [
    {
      "id": 3,
      "name": "Emergency buffer",
      "target_amount": "30000.00",
      "saved_amount": "4500.00",
      "target_date": null,
      "priority": "medium"
    }
  ],
  "updated_at": "2026-10-25T09:12:41.123456Z"
}
```

`id` values on `expected_incomes` and `savings_goals` are assigned by the server
and change when a collection is replaced — keep them for display only.

## 5. Save onboarding progress

`PATCH /api/onboarding` → **200** (returns the full draft, same shape as §4)

Send **only the sections the user has filled in**. Any section you omit is left
untouched. Every response is the complete draft, so you can replace your local
state with it.

### Section reference

**Step 1 — `financial_profile`** (one per user; fields merge with what is stored)

```json
{
  "financial_profile": {
    "work_type": "Graphic designer",
    "income_pattern": "irregular",
    "typical_income": "15000.00",
    "currency": "ZAR"
  }
}
```

| Field | Type | Rules |
|---|---|---|
| `work_type` | string \| null | max 100 chars |
| `income_pattern` | `"fixed"` \| `"irregular"` \| `"mixed"` \| null | |
| `typical_income` | money \| null | ≥ 0 |
| `currency` | string \| null | exactly 3 letters (ISO 4217, e.g. `ZAR`) |

**Step 2 — `financial_balance`** (one per user; fields merge)

```json
{
  "financial_balance": {
    "available_balance": "18450.00",
    "existing_savings": "0.00"
  }
}
```

| Field | Type | Rules |
|---|---|---|
| `available_balance` | money \| null | ≥ 0 — money the user can spend now |
| `existing_savings` | money \| null | ≥ 0 — kept separate so it is not double counted |

**Step 3 — `expected_incomes`** (list; **replaces** the whole list)

```json
{
  "expected_incomes": [
    { "source": "Mokoena Studio project", "amount": "12000.00", "expected_date": "2026-11-05" }
  ]
}
```

| Field | Type | Rules |
|---|---|---|
| `source` | string | 1–150 chars |
| `amount` | money | > 0 |
| `expected_date` | date | `YYYY-MM-DD` |

Status always starts as `"expected"` — clients cannot set it here.

**Step 4 — `savings_goals`** (list; **replaces** the whole list)

```json
{
  "savings_goals": [
    {
      "name": "Emergency buffer",
      "target_amount": "30000.00",
      "saved_amount": "4500.00",
      "target_date": "2027-03-31",
      "priority": "medium"
    }
  ]
}
```

| Field | Type | Rules |
|---|---|---|
| `name` | string | 1–100 chars |
| `target_amount` | money | > 0 |
| `saved_amount` | money | ≥ 0, default `"0.00"` |
| `target_date` | date \| null | `YYYY-MM-DD` |
| `priority` | `"low"` \| `"medium"` \| `"high"` | default `"medium"` |

### Replace semantics — read this

`expected_incomes` and `savings_goals` are **not merged**. Sending the key
replaces every stored item for that user in the same request.

- To **add** an item: send the existing list plus the new item.
- To **remove** an item: send the list without it.
- To **leave the collection alone**: omit the key entirely.
- Retrying the same `PATCH` is safe — it cannot create duplicates.

An empty list clears the collection:

```json
{ "expected_incomes": [] }
```

### Full example (all sections at once)

```json
{
  "financial_profile": {
    "work_type": "Graphic designer",
    "income_pattern": "irregular",
    "typical_income": null,
    "currency": "ZAR"
  },
  "financial_balance": {
    "available_balance": "18450.00",
    "existing_savings": "0.00"
  },
  "expected_incomes": [
    {
      "source": "Mokoena Studio project",
      "amount": "12000.00",
      "expected_date": "2026-11-05"
    }
  ],
  "savings_goals": [
    {
      "name": "Emergency buffer",
      "target_amount": "30000.00",
      "saved_amount": "4500.00",
      "priority": "medium"
    }
  ]
}
```

`422` example (negative amount):

```json
{
  "detail": [
    {
      "loc": ["body", "financial_balance", "available_balance"],
      "msg": "Input should be greater than or equal to 0",
      "type": "greater_than_equal"
    }
  ]
}
```

## 6. Record the current step

`PUT /api/onboarding/step` → **200** (full draft)

Call this when the user taps **Next**, **Back**, or **Save & exit**. It only
updates the step — it never touches financial data.

```json
{ "current_step": 3 }
```

`current_step` must be `1`–`5`; anything else returns `422`.

> Rule of thumb: `PATCH` first to save what the user typed on that step, then
> `PUT /step` with the step they should land on when they return.

## 7. Complete onboarding

`POST /api/onboarding/complete` → **200** (full draft with `is_complete: true`)

No request body. Server-side checks:

| Requirement | Missing → `422` entry |
|---|---|
| `financial_profile.currency` is set | `"financial_profile.currency"` |
| `financial_balance.available_balance` is set | `"financial_balance.available_balance"` |

Steps 3 and 4 are optional — a user may have no expected income or goal yet.

Failure `422`:

```json
{
  "detail": {
    "message": "Onboarding is incomplete",
    "missing": ["financial_balance.available_balance"]
  }
}
```

Send the user back to step `1` or `2` for each missing field, then retry.

Success `200`:

```json
{
  "current_step": 5,
  "is_complete": true,
  "financial_profile": { "...": "as saved" },
  "financial_balance": { "...": "as saved" },
  "expected_incomes": [ "..." ],
  "savings_goals": [ "..." ],
  "updated_at": "2026-10-25T10:02:17.445Z"
}
```

## 8. Commitments

Essential bills ("What must you pay?"). Independent of the onboarding draft.

### Load

`GET /api/onboarding/commitments` → **200**

```json
{
  "commitments": [
    {
      "id": 12,
      "name": "Apartment rent",
      "amount": "4500.00",
      "due_date": "2026-11-01",
      "is_paid": false
    }
  ]
}
```

### Replace

`PUT /api/onboarding/commitments` → **200** (`{"commitments": [...]}`)

The body replaces the **entire** list — send everything that should remain.
Send `{"commitments": []}` to clear it. Rows in the body must not include `id`.

```json
{
  "commitments": [
    { "name": "Apartment rent", "amount": "4500.00", "due_date": "2026-11-01" },
    { "name": "Phone contract", "amount": "650.00", "is_paid": false }
  ]
}
```

| Field | Type | Rules |
|---|---|---|
| `name` | string | 1–100 characters |
| `amount` | money | Greater than 0 |
| `due_date` | date | Optional |
| `is_paid` | bool | Default `false` |

Every row is validated before anything is written: one bad row returns `422`
and the saved list is left untouched.

---

## 9. Dashboard overview

`GET /api/dashboard/overview` → **200**

Response `200`:

```json
{
  "user": { "name": "Thandi" },
  "currency": "ZAR",
  "available_now": "18450.00",
  "projected_balance": "22550.00",
  "essential_commitments": "7900.00",
  "next_expected_payment": {
    "source": "Mokoena Studio project",
    "amount": "12000.00",
    "expected_date": "2026-11-05",
    "status": "expected"
  },
  "savings_goals": [
    {
      "id": 3,
      "name": "Emergency buffer",
      "target_amount": "30000.00",
      "saved_amount": "4500.00",
      "progress_percentage": 15
    }
  ],
  "alerts": [
    {
      "type": "payment_expected",
      "severity": "info",
      "message": "Mokoena Studio project payment is still expected on 05 Nov 2026."
    }
  ],
  "forecast_is_estimate": true
}
```

| Field | Type | Notes |
|---|---|---|
| `user.name` | string | First name only |
| `currency` | string | From the profile; `"ZAR"` if not set |
| `available_now` | money | `financial_balance.available_balance`, `"0.00"` if unset |
| `projected_balance` | money | `available_now + expected income in horizon − unpaid commitments in horizon` |
| `essential_commitments` | money | Unpaid commitments due within the horizon; `"0.00"` when there are none |
| `next_expected_payment` | object \| null | Earliest `expected` income inside the horizon; `null` if none |
| `savings_goals[].progress_percentage` | int | `saved / target × 100`, capped at `100` |
| `alerts` | array | Same content as §9 |
| `forecast_is_estimate` | bool | Always `true` — label the projection as an estimate in the UI |

**Horizon:** 30 days from today (`FORECAST_HORIZON_DAYS`). Expected income and
commitments use the same cutoff, so the projection compares like with like.
`projected_balance` is only as accurate as the data the user entered.

Response when nothing is set up yet:

```json
{
  "user": { "name": "Thandi" },
  "currency": "ZAR",
  "available_now": "0.00",
  "projected_balance": "0.00",
  "essential_commitments": "0.00",
  "next_expected_payment": null,
  "savings_goals": [],
  "alerts": [
    { "type": "profile_incomplete", "severity": "info", "message": "Finish onboarding to get accurate forecasts." },
    { "type": "no_available_balance", "severity": "info", "message": "Add what you have available so projections are accurate." }
  ],
  "forecast_is_estimate": true
}
```

## 9. Dashboard alerts

`GET /api/dashboard/alerts` → **200**

Returns the `alerts` array from the overview, most urgent first.

```json
[
  {
    "type": "commitments_exceed_balance",
    "severity": "urgent",
    "message": "Your commitments (ZAR 7900.00) are more than what you have available (ZAR 5000.00)."
  },
  {
    "type": "payment_overdue",
    "severity": "warning",
    "message": "Mokoena Studio project payment was due on 20 Oct 2026 but has not arrived."
  }
]
```

| `type` | `severity` | When it appears | Suggested UI |
|---|---|---|---|
| `profile_incomplete` | info | No currency saved yet | Inline hint |
| `commitments_exceed_balance` | urgent | Unpaid commitments in horizon exceed available now | Red banner |
| `payment_overdue` | warning | Next expected payment date has passed | Amber banner |
| `payment_expected` | info | Next expected payment is still upcoming | Inline |
| `goal_reached` | success | A goal's saved amount ≥ target | Toast |
| `goal_due_soon` | warning | Goal due within 14 days with nothing saved | Amber banner |
| `no_available_balance` | info | Available balance is `"0.00"` | Inline hint |

Match on `type`, never on `message` (messages are display text and may change).

---

## 10. Commitments

Essential bills ("What must you pay?"). Independent of the onboarding draft.

### Load

`GET /api/onboarding/commitments` → **200**

```json
{
  "commitments": [
    { "id": 12, "name": "Apartment rent", "amount": "4500.00", "due_date": "2026-11-01", "is_paid": false }
  ]
}
```

### Replace

`PUT /api/onboarding/commitments` → **200**

The body replaces the **entire** list — send everything that should remain.
`{"commitments": []}` clears it. Rows must not include `id`.

```json
{
  "commitments": [
    { "name": "Apartment rent", "amount": "4500.00", "due_date": "2026-11-01" },
    { "name": "Phone contract", "amount": "650.00" }
  ]
}
```

| Field | Type | Rules |
|---|---|---|
| `name` | string | 1–100 characters |
| `amount` | money | Greater than 0 |
| `due_date` | date | Optional |
| `is_paid` | bool | Default `false` |

## 11. Upcoming commitments

`GET /api/dashboard/upcoming` → **200**

Unpaid commitments due within the forecast horizon (`FORECAST_HORIZON_DAYS`,
default 30 days). Undated commitments are not included.

```json
{
  "commitments": [
    { "name": "Apartment rent", "amount": "4500.00", "due_date": "2026-11-01" }
  ],
  "total": "4500.00"
}
```

---

## 12. Cash-flow timeline (Cash flow screen)

`GET /api/cashflow/timeline?view=until_next_payment` → **200**

`view` is `until_next_payment` (default: today up to the next expected
payment) or `monthly` (with `month=2025-06`, defaulting to the current month).

```json
{
  "view": "until_next_payment",
  "currency": "ZAR",
  "period_label": "Today – 28 Jun 2025",
  "start_date": "2025-06-23",
  "end_date": "2025-06-28",
  "starting_balance": "18450.00",
  "projected_end_balance": "22550.00",
  "projected_end_label": "Ending balance",
  "expected_not_received": "12000.00",
  "planned_savings": "0.00",
  "events": [
    { "date": "2025-06-23", "label": "Available now", "kind": "starting_balance", "amount": null, "balance": "18450.00", "confirmed": true, "pending": false, "note": null, "transaction_id": null },
    { "date": "2025-06-25", "label": "Apartment rent", "kind": "expense", "amount": "6500.00", "balance": "11950.00", "confirmed": false, "pending": true, "note": "Upcoming", "transaction_id": null },
    { "date": "2025-06-28", "label": "Mokoena Studio project", "kind": "income", "amount": "12000.00", "balance": "22550.00", "confirmed": false, "pending": true, "note": "Depends on payment arriving", "transaction_id": null }
  ]
}
```

| Field | Meaning |
|---|---|
| `kind` | `starting_balance`, `income`, `expense` or `savings_allocation` |
| `balance` | Running balance **after** this event — render it as-is |
| `confirmed` | Money has actually moved |
| `pending` | Still to happen → show the "Upcoming" / "Depends on payment arriving" styling |
| `planned_savings` | Monthly plan applied on the month's last day; moves no money |

How balances are built (so the numbers never double-count):

- The starting figure is the onboarding "available now" rolled back to the
  period start using confirmed transactions.
- Expected income and unpaid commitments appear as `pending` events. Once
  confirmed (section 14) the original record is closed and drops out.
- Expected money is **not** confirmed cash; label it as an estimate.

## 13. Transactions (Transactions + Transaction form screens)

### List a month

`GET /api/transactions?month=2025-06&kind=all&from_date=2025-06-18` → **200**

- `month` — `YYYY-MM`, defaults to the current month
- `kind` — `all`, `income` or `expenses` (the screen's segmented filter)
- `from_date` — the "From date (optional)" box, applied inside the month

```json
{
  "items": [
    {
      "id": 31,
      "direction": "income",
      "description": "Mokoena Studio project",
      "amount": "12000.00",
      "transaction_date": "2025-06-28",
      "status": "expected",
      "category": "client_payment",
      "recurrence": "none",
      "recurrence_interval": null,
      "recurrence_end_date": null,
      "notes": "Second instalment",
      "confirmed_at": null,
      "is_savings_allocation": false,
      "created_at": "2025-06-23T08:12:44.210Z"
    }
  ],
  "total_income": "12000.00",
  "total_expenses": "4200.00",
  "net": "7800.00",
  "month": "2025-06"
}
```

`status`: `expected` (money not moved yet), `received` (income received **or**
expense paid), `cancelled` (never counts).

### Form options

`GET /api/transactions/options` → **200**

```json
{
  "statuses": ["expected", "received", "cancelled"],
  "recurrences": ["none", "daily", "weekly", "monthly", "yearly"],
  "income_categories": ["client_payment", "salary", "refund", "other"],
  "expense_categories": ["housing", "utilities", "food", "transport", "subscriptions", "equipment", "tax", "other"]
}
```

### Add a transaction

`POST /api/transactions` → **201**

```json
{
  "direction": "expense",
  "description": "Apartment rent",
  "amount": "6500.00",
  "transaction_date": "2025-06-25",
  "status": "expected",
  "category": "housing",
  "recurrence": "monthly",
  "recurrence_end_date": "2026-06-25",
  "notes": null
}
```

| Field | Type | Rules |
|---|---|---|
| `direction` | `income` \| `expense` | Required |
| `description` | string | 1–150 characters |
| `amount` | money | Greater than 0 |
| `transaction_date` | date | Required |
| `status` | `expected` \| `received` \| `cancelled` | Default `expected` |
| `category` | string | Optional; see options |
| `recurrence` | `none` \| `daily` \| `weekly` \| `monthly` \| `yearly` | Default `none` |
| `recurrence_interval` | int | Every N periods; defaults to 1 |
| `recurrence_end_date` | date | Optional; series stops after this |
| `notes` | string | Optional, ≤ 2000 characters |

Recurring rows appear once in the list and repeat inside the cash-flow
timeline while still `expected`.

### Edit / delete

`PATCH /api/transactions/{id}` — same fields, all optional. Sending
`{"status": "received"}` confirms it, `{"status": "expected"}` reopens it.
`DELETE /api/transactions/{id}` → **204**.

### Confirm

`POST /api/transactions/{id}/confirm` → **200** (*Mark received* / *Mark paid*)
— only for `expected` rows; a second call returns `409`.

For rows that came from onboarding, use the specific routes so the original
record is closed too:

- `POST /api/transactions/incomes/{income_id}/mark-received` — the id is
  `expected_incomes[].id` from `GET /api/onboarding`
- `POST /api/transactions/commitments/{commitment_id}/mark-paid` — the id is
  `commitments[].id` from `GET /api/onboarding/commitments`

Both return the created transaction with status **200** and make the
income/commitment stop being projected.

---

## 14. Savings goals (Goals + Goal form screens)

### List

`GET /api/goals` → **200**

```json
[
  {
    "id": 4,
    "name": "Emergency buffer",
    "target_amount": "30000.00",
    "saved_amount": "4500.00",
    "remaining": "25500.00",
    "target_date": "2025-12-31",
    "priority": "high",
    "is_active": true,
    "progress_percentage": 15,
    "status": "on_track",
    "status_label": "On track"
  }
]
```

`status`: `on_track`, `behind`, `reached` or `no_date`. Render
`status_label`; branch on `status`.

### Create / edit / delete

`POST /api/goals` → **201** — the first goal created becomes active.

```json
{ "name": "Tax reserve", "target_amount": "20000.00", "saved_amount": "0.00", "target_date": "2026-02-28", "priority": "medium" }
```

`PATCH /api/goals/{id}` — any of `name`, `target_amount`, `saved_amount`,
`target_date`, `priority`, `is_active`. Sending `{"is_active": true}` makes it
the active goal and demotes the previous one (there is always at most one).

`DELETE /api/goals/{id}` → **204**. If the active goal is deleted, the oldest
remaining goal becomes active.

### Record money put aside

`POST /api/goals/{id}/contributions` → **200**

```json
{ "amount": "1000.00", "contributed_on": "2025-06-23" }
```

Adds to `saved_amount` and records a `Savings — <goal>` transaction
(category `savings`). FlowShelter never moves money itself. Dates in the
future return `409`.

---

## 15. Set the monthly savings plan

`PATCH /api/onboarding` with

```json
{ "financial_profile": { "savings_plan_amount": "1000.00" } }
```

shows as the "Planned savings allocation" line in the monthly cash flow and the
"Planned savings: R 1 000" note. It is a plan only.

## Database update

Run once, in order, after deploying this version:

```bash
python create_tables.py     # adds the new transactions table
python migrate_cashflow.py  # adds savings_plan_amount, is_active + an index
```

`migrate_cashflow.py` is idempotent — re-running it reports `skip` for
columns that already exist. Without it, the profile/goal queries and the new
endpoints fail with an "undefined column" error.

## Known gaps

- Confirmed transactions are not edited back into the onboarding balance;
  "available now" stays the figure the user last entered.
- No push notifications or scheduler: a recurring series is expanded when the
  cash flow is requested, not stored as future rows.
- Deleting a goal keeps its contribution transactions, so the cash-flow
  history still matches what was actually put aside.