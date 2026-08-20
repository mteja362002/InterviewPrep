# PrepOS Auth Testing Playbook

## Step 1: MongoDB Verification
```
mongosh
use prepos_db
db.users.find({role: "admin"}).pretty()
db.users.findOne({role: "admin"}, {password_hash: 1})
```
Verify:
- bcrypt hash starts with `$2b$`
- Indexes: `users.email` (unique), `login_attempts.identifier`, `password_reset_tokens.expires_at` (TTL)

## Step 2: API Testing
```
BASE=https://repo-validator-15.preview.emergentagent.com

# Register
curl -c cookies.txt -X POST $BASE/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user1@test.com","password":"Test@1234","name":"Test User"}'

# Login
curl -c cookies.txt -X POST $BASE/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@prepos.io","password":"Admin@123"}'

# Me
curl -b cookies.txt $BASE/api/auth/me

# Logout
curl -b cookies.txt -X POST $BASE/api/auth/logout

# Forgot password (link is logged to backend console)
curl -X POST $BASE/api/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@prepos.io"}'
```

## Admin Credentials
- Email: `admin@prepos.io`
- Password: `Admin@123`

## Auth Endpoints
- POST /api/auth/register
- POST /api/auth/login
- POST /api/auth/logout
- GET /api/auth/me
- POST /api/auth/refresh
- POST /api/auth/forgot-password
- POST /api/auth/reset-password
- GET /api/onboarding
- POST /api/onboarding
- GET /api/profile
- PATCH /api/profile
- GET /api/settings
- PATCH /api/settings
