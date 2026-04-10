# Steadily API

Lightweight Python REST API for the Steadily personal finance app. Designed to run on AWS Lambda with API Gateway — no web framework, just plain Python + psycopg2.

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

### Transaction Query Params

`?category_id=`, `?start_date=`, `?end_date=`, `?search=`, `?page=1`, `?per_page=20`, `?sort_by=transaction_date`, `?sort_order=desc`

## Running Tests

```bash
pytest tests/ -v
```
