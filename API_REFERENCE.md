# ReLoop API Quick Reference

## Authentication

### Register
```http
POST /api/users/register/
Content-Type: application/json

{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "securepass123",
  "password_confirm": "securepass123",
  "first_name": "John",
  "last_name": "Doe",
  "phone_number": "+919876543210",
  "role": "DONOR",  // or "ACCEPTOR"
  "address": "123 Main St, Bangalore"
}
```

### Login
```http
POST /api/users/login/
Content-Type: application/json

{
  "username": "john_doe",
  "password": "securepass123"
}

Response:
{
  "user": {...},
  "tokens": {
    "refresh": "...",
    "access": "..."
  }
}
```

## Donations

### Create Donation
```http
POST /api/donations/
Authorization: Bearer <access_token>
Content-Type: multipart/form-data

{
  "category": "CLOTHES",  // CLOTHES, TOYS, BOOKS
  "quantity": 25,
  "condition": "GENTLY_USED",  // NEW, GENTLY_USED, USED
  "description": "Winter clothes for children",
  "pickup_address": "123 Main St, Bangalore",
  "preferred_pickup_start": "2024-02-20T10:00:00Z",
  "preferred_pickup_end": "2024-02-20T18:00:00Z",
  "uploaded_images": [<file1>, <file2>]
}

Response includes AI-suggested acceptor
```

### List Donations
```http
GET /api/donations/
Authorization: Bearer <access_token>

Response: Filtered by user role
```

### Accept Donation (Acceptor)
```http
POST /api/donations/123/accept/
Authorization: Bearer <access_token>
```

## Map Discovery

### Get Nearby Acceptors
```http
GET /api/acceptors/nearby/?lat=12.9716&lon=77.5946&category=CLOTHES&max_distance=50
Authorization: Bearer <access_token>

Response: List of nearby verified acceptors with distance
```

## Logistics

### Calculate Pickup Cost
```http
POST /api/logistics/calculate-cost/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "distance_km": 15.5,
  "provider_id": 1
}

Response:
{
  "distance_km": 15.5,
  "base_cost": 310.0,
  "platform_commission": 31.0,
  "commission_rate": 10.0,
  "total_cost": 341.0
}
```

### Create Pickup Request
```http
POST /api/logistics/pickups/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "donation": 123,
  "pickup_type": "PLATFORM_ARRANGED",  // PLATFORM_ARRANGED, SELF_SCHEDULED, DROP_OFF
  "logistics_provider": 1
}
```

## Payments

### Initiate Payment
```http
POST /api/payments/initiate/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "donation_id": 123,
  "amount": 341.0,
  "payment_method": "Card"
}

Response:
{
  "payment_id": 1,
  "transaction_id": "TXN-ABC123",
  "amount": 341.0,
  "status": "PENDING"
}
```

### Complete Payment
```http
POST /api/payments/1/complete/
Authorization: Bearer <access_token>

Response: Auto-success simulation
```

## Analytics

### Impact Dashboard
```http
GET /api/analytics/dashboard/
Authorization: Bearer <access_token>

Response:
{
  "total_donations": 5,
  "total_waste_diverted": 12.5,
  "total_carbon_offset": 31.25,
  "total_impact_points": 281,
  "impact_level": "SILVER",
  "recent_donations": [...]
}
```

### Leaderboard
```http
GET /api/analytics/leaderboard/?type=donors
Authorization: Bearer <access_token>

Response: Top 10 donors by impact score
```

## Status Codes

- `200 OK` - Success
- `201 Created` - Resource created
- `400 Bad Request` - Invalid data
- `401 Unauthorized` - Missing/invalid token
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error
