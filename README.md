# Steadily API

Lightweight Python REST API for the Steadily personal finance app. Designed to run on AWS Lambda with API Gateway — no web framework, just plain Python + psycopg2.

Deployed URL: https://d17qicjfvn0awy.cloudfront.net/
Frontend Repo: https://github.com/cjrojas72/steadily

## Project Structure

```
steadily-backend/
├── lambda_handler.py       # Entry point — routes requests to handlers
├── config.py               # Loads env vars
├── db.py                   # psycopg2 connection management
├── routes/
│   ├── auth.py             # signup, login, logout, me, refresh
│   ├── transactions.py     # CRUD + filters + bulk create
│   ├── categories.py       # CRUD (blocks default delete)
│   ├── budgets.py          # create/update (upsert), list, delete
│   └── analytics.py        # monthly-spending, monthly-totals
├── services/               # SQL queries and business logic
├── middleware/
│   └── auth.py             # JWT verification via Supabase secret
├── schemas/                # Request validation functions
├── utils/
│   ├── response.py         # Standard JSON response helpers
│   └── pagination.py       # Pagination params extraction
└── tests/
```

## Local Development

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create `.env` from `.env.example` and fill in your Supabase credentials.

For local testing, use [SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html):
```bash
sam local start-api
```

## AWS Lambda Deployment

**Handler:** `lambda_handler.handler`

### Environment Variables

Set these in your Lambda configuration:
- `DATABASE_URL` — Supabase pooler connection string
- `SUPABASE_URL` — `https://[ref].supabase.co`
- `SUPABASE_ANON_KEY` — Supabase anon/public key
- `SUPABASE_JWT_SECRET` — Supabase JWT secret
- `CORS_ORIGINS` — Frontend URL

### Packaging

```bash
pip install -r requirements.txt -t package/
cp -r routes/ services/ middleware/ schemas/ utils/ lambda_handler.py config.py db.py package/
cd package && zip -r ../deployment.zip .
```

Upload `deployment.zip` to Lambda.

> **Important:** If you build the package on Windows, `psycopg2-binary` can include a Windows-specific import shim that breaks on Lambda's Linux runtime. Rebuild the package in Linux/WSL/Docker or use an AWS Lambda layer for `psycopg2`.
>
> Example Docker build:
>
> ```bash
> docker run --rm -v "$PWD":/app -w /app public.ecr.aws/lambda/python:3.12 \
>   bash -lc "pip install -r requirements.txt -t package/ && cp -r routes/ services/ middleware/ schemas/ utils/ lambda_handler.py config.py db.py package/ && cd package && zip -r ../deployment.zip ."
> ```
>
> If you still see Lambda import errors, switch to a dedicated `psycopg2` Lambda layer instead of bundling `psycopg2-binary` directly.

### API Gateway

Configure with route: `ANY /api/{proxy+}`

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/health` | No | Health check |
| POST | `/api/auth/signup` | No | Register via Supabase |
| POST | `/api/auth/login` | No | Login, returns JWT |
| POST | `/api/auth/refresh` | No | Refresh access token |
| POST | `/api/auth/logout` | Yes | Confirm logout |
| GET | `/api/auth/me` | Yes | Current user profile |
| GET | `/api/transactions` | Yes | List (filterable, paginated) |
| POST | `/api/transactions` | Yes | Create one or bulk (array) |
| GET | `/api/transactions/:id` | Yes | Get by ID |
| PATCH | `/api/transactions/:id` | Yes | Update |
| DELETE | `/api/transactions/:id` | Yes | Delete |
| GET | `/api/categories` | Yes | List all |
| POST | `/api/categories` | Yes | Create |
| PATCH | `/api/categories/:id` | Yes | Update |
| DELETE | `/api/categories/:id` | Yes | Delete |
| GET | `/api/budgets` | Yes | List all |
| POST | `/api/budgets` | Yes | Create or update |
| DELETE | `/api/budgets/:id` | Yes | Delete |
| GET | `/api/analytics/monthly-spending` | Yes | By category per month |
| GET | `/api/analytics/monthly-totals` | Yes | Income/expense per month |
| GET | `/api/profile` | Yes | Current user's profile fields |
| PATCH | `/api/profile` | Yes | Update first_name / last_name / phone1 / display_name |

### Transaction Query Params

`?category_id=`, `?start_date=`, `?end_date=`, `?search=`, `?page=1`, `?per_page=20`, `?sort_by=transaction_date`, `?sort_order=desc`

## Running Tests

```bash
pytest tests/ -v
```

## Change Log

### Profile endpoints (`/api/profile`)

New `routes/profile.py`, `services/profile_service.py`, and
`schemas/profile_schema.py` surface an authenticated profile read/update API:

- `GET /api/profile` — returns `{ id, email, display_name, first_name, last_name, phone1, currency, created_at }`
- `PATCH /api/profile` — accepts any subset of `first_name`, `last_name`, `phone1`, `display_name`

The service uses a `_has_column` guard so it silently skips updates to fields
that don't exist on the `profiles` table yet. Run the following migration
before deploying to populate the new columns:

```sql
ALTER TABLE profiles
  ADD COLUMN IF NOT EXISTS first_name text,
  ADD COLUMN IF NOT EXISTS last_name  text,
  ADD COLUMN IF NOT EXISTS phone1     text;
```

Phone numbers are validated with a loose international regex
(`+`, digits, spaces, dashes, parens — length 7–20). An empty string clears
the value.

### Budget `spent` is now stored, not computed

`budgets.spent` (float4) is maintained by the transaction service:

- `create_transaction` / `create_transactions_bulk` apply `+amount` to every
  matching budget.
- `update_transaction` reverses the old row's impact (`-amount`) and applies
  the new one (`+amount`) in a single DB transaction.
- `delete_transaction` applies `-amount`.

A budget is considered "matching" when:

1. it belongs to the same profile and category,
2. `created_at::date <= transaction_date::date`, and
3. the transaction date falls inside the current active period
   (weekly = `date_trunc('week', CURRENT_DATE)` Monday–Sunday,
   monthly = same year + month as `CURRENT_DATE`,
   yearly = same year as `CURRENT_DATE`).

Only `type = 'expense'` transactions affect `spent`; income is ignored
(see the income-handling change in the previous entry).

`services/budget_service.get_budgets` now reads `COALESCE(b.spent, 0) AS spent_amount`
directly — no transactions JOIN — when the column exists. If the column is
missing it falls back to the previous computed-from-transactions query.

Run this migration once per deployment:

```sql
ALTER TABLE budgets
  ADD COLUMN IF NOT EXISTS spent real NOT NULL DEFAULT 0;
```

> **Caveat:** the stored value does not auto-reset when a new weekly/monthly/yearly
> period starts. A scheduled job or on-read period-change check is a follow-up.

### Tests

`tests/test_schemas.py` covers `validate_update` for the profile schema
(valid payload, partial update, clearing phone, invalid phone, unknown-field
ignoring, non-string rejection). `tests/test_handler.py` adds an
`unauthenticated_profile` case confirming `/api/profile` returns 401 without a
token. No DB-integration tests are added — the handler/schema layer is still
the only unit-tested surface.
