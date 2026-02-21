# ReLoop - Circular Donation Platform

A location-based item donation platform connecting donors with NGOs/institutions through AI-powered matching, logistics coordination, and impact tracking.

## 🌟 Features

### Core Functionality
- **Role-Based Access**: Donor, Acceptor (NGO/Institution), and Admin roles
- **Item Categories**: Clothes, Toys, and Books
- **AI-Powered Matching**: Smart algorithm matches donations with nearby NGOs based on distance, needs, capacity, and ratings
- **Map-Based Discovery**: Interactive map showing nearby acceptors with filters
- **Logistics Integration**: Simulated third-party logistics (Rapido, Porter, Uber) with cost calculation
- **Payment System**: Dummy payment gateway with commission tracking
- **Impact Tracking**: Environmental metrics (waste diverted, carbon offset, impact points)
- **Leaderboards**: Top donors and cities by impact
- **Corporate/School Drives**: Bulk donation events with participant management
- **Review System**: Donors can rate acceptors

### AI Features
- **Smart Matching Engine**: Multi-factor scoring (distance, needs, capacity, ratings)
- **Pickup Scheduler**: Optimal time suggestions based on preferences and traffic
- **Impact Calculator**: Automatic environmental impact computation
- **Image Validation**: Upload validation with size and type checks

## 🏗️ Tech Stack

### Backend
- **Framework**: Django 5.0.1
- **API**: Django REST Framework 3.14
- **Database**: MySQL
- **Authentication**: JWT (djangorestframework-simplejwt)
- **Task Queue**: Celery 5.3.6
- **Cache**: Redis 5.0.1
- **Geocoding**: geopy 2.4.1
- **AI**: OpenAI API (optional)

### Frontend (To be implemented)
- **Framework**: React 18+
- **Styling**: Tailwind CSS
- **Maps**: Google Maps API
- **HTTP Client**: Axios

## 📦 Installation

### Prerequisites
- Python 3.12+
- MySQL Server
- Redis Server (optional, for Celery)
- Node.js 18+ (for frontend)

### Backend Setup

1. **Clone the repository**
```bash
cd C:\Users\Shazfari\.gemini\antigravity\scratch\reloop
```

2. **Install Python dependencies**
```bash
cd backend
pip install -r requirements.txt
```

3. **Configure environment variables**
```bash
# Copy .env.example to .env
copy .env.example .env

# Edit .env and update:
# - DB_PASSWORD (your MySQL password)
# - GOOGLE_MAPS_API_KEY (get from Google Cloud Console)
# - OPENAI_API_KEY (optional, for advanced AI features)
```

4. **Create MySQL database**
```sql
CREATE DATABASE reloop_platform_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

5. **Run migrations**
```bash
python manage.py makemigrations
python manage.py migrate
```

6. **Create superuser**
```bash
python manage.py createsuperuser
```

7. **Load seed data (optional)**
```bash
python seed_data.py
```

8. **Run development server**
```bash
python manage.py runserver
```

The API will be available at `http://localhost:8000`

### Frontend Setup (Coming Soon)
```bash
cd frontend
npm install
npm run dev
```

## 📚 API Documentation

### Base URL
```
http://localhost:8000/api
```

### Authentication
All endpoints except registration and login require JWT authentication.

**Headers:**
```
Authorization: Bearer <access_token>
```

### Endpoints

#### Users
- `POST /users/register/` - Register new user
- `POST /users/login/` - Login and get JWT tokens
- `GET /users/profile/` - Get current user profile
- `PATCH /users/profile/` - Update user profile
- `GET /users/donor-profile/` - Get donor profile
- `GET /users/acceptor-profile/` - Get acceptor profile

#### Donations
- `GET /donations/` - List donations (filtered by role)
- `POST /donations/` - Create new donation (triggers AI matching)
- `GET /donations/<id>/` - Get donation details
- `POST /donations/<id>/accept/` - Accept donation (acceptor only)
- `POST /donations/<id>/reject/` - Reject donation (acceptor only)
- `PATCH /donations/<id>/status/` - Update donation status

#### Acceptors
- `GET /acceptors/needs/` - List current needs
- `POST /acceptors/needs/` - Create new need
- `GET /acceptors/nearby/` - Get nearby acceptors (map view)
- `POST /acceptors/<id>/verify/` - Verify acceptor (admin only)

#### Logistics
- `GET /logistics/providers/` - List logistics providers
- `GET /logistics/pickups/` - List pickup requests
- `POST /logistics/pickups/` - Create pickup request
- `POST /logistics/calculate-cost/` - Calculate pickup cost

#### Payments
- `GET /payments/` - List payments
- `POST /payments/initiate/` - Initiate payment
- `POST /payments/<id>/complete/` - Complete payment (simulated)
- `GET /payments/commissions/` - List commissions (admin only)
- `GET /payments/commissions/summary/` - Commission summary (admin only)

#### Analytics
- `GET /analytics/impact/` - List impact metrics
- `GET /analytics/dashboard/` - User impact dashboard
- `GET /analytics/leaderboard/` - Global leaderboard
- `GET /analytics/drives/` - List drive events
- `POST /analytics/drives/` - Create drive event
- `POST /analytics/drives/<id>/join/` - Join drive
- `GET /analytics/reviews/` - List reviews
- `POST /analytics/reviews/` - Create review
- `GET /analytics/statistics/` - Platform statistics (admin only)

## 🔐 Default Credentials (Seed Data)

```
Admin:
  Username: admin
  Password: admin123

Donor:
  Username: john_donor
  Password: donor123

Acceptor:
  Username: helping_hands_ngo
  Password: acceptor123
```

## 🗂️ Project Structure

```
reloop/
├── backend/
│   ├── reloop/              # Main project settings
│   ├── users/               # User authentication & profiles
│   ├── donations/           # Donation management
│   ├── acceptors/           # NGO/Institution management
│   ├── logistics/           # Pickup & delivery coordination
│   ├── payments/            # Payment & commission tracking
│   ├── analytics/           # Impact metrics & reporting
│   ├── ai_engine/           # AI matching & scheduling
│   ├── manage.py
│   ├── requirements.txt
│   ├── seed_data.py
│   └── .env
├── frontend/                # React application (to be implemented)
└── README.md
```

## 🚀 Workflow Example

### Donor Flow
1. Register as donor with address
2. Create donation (category, quantity, condition, images)
3. View AI-suggested acceptor or browse map
4. Select acceptor
5. Schedule pickup (platform-arranged, self-scheduled, or drop-off)
6. Make payment (if platform-arranged)
7. Track donation status
8. View impact dashboard

### Acceptor Flow
1. Register as NGO/institution
2. Wait for admin verification
3. List current needs
4. Receive donation requests
5. Accept/reject donations
6. Schedule pickup (if self-handling)
7. Update donation status
8. View analytics

### Admin Flow
1. Verify NGO registrations
2. Monitor platform statistics
3. View commission earnings
4. Manage users and donations

## 🌍 Environmental Impact

The platform calculates:
- **Waste Diverted**: Estimated kg diverted from landfill
- **Carbon Offset**: kg CO2 equivalent saved
- **Impact Points**: Gamified scoring system
- **Impact Levels**: Bronze, Silver, Gold, Platinum badges

## 🔧 Configuration

### Google Maps API
1. Get API key from [Google Cloud Console](https://console.cloud.google.com/)
2. Enable Maps JavaScript API and Geocoding API
3. Add key to `.env` file

### OpenAI API (Optional)
1. Get API key from [OpenAI Platform](https://platform.openai.com/)
2. Add key to `.env` file
3. Used for advanced image validation (not implemented in MVP)

## 📊 Database Schema

Key models:
- **User**: Custom user with role field
- **DonorProfile**: Donor details with geocoded location
- **AcceptorProfile**: NGO/institution details with verification
- **Donation**: Item donations with status workflow
- **CurrentNeed**: Acceptor's current requirements
- **PickupRequest**: Logistics coordination
- **Payment**: Transaction records
- **ImpactMetrics**: Environmental impact tracking
- **DriveEvent**: Corporate/school collaboration
- **Review**: Donor ratings for acceptors

## 🧪 Testing

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test users
python manage.py test donations
python manage.py test ai_engine
```

## 📝 License

This project is for educational and demonstration purposes.

## 🤝 Contributing

This is a demonstration project. For production use, implement:
- Real logistics API integration
- Real payment gateway (Razorpay, Stripe)
- OpenAI Vision API for image validation
- Email notifications
- SMS notifications
- Real-time tracking
- Mobile apps

## 📞 Support

For issues or questions, please check the API documentation or review the code comments.

---

**Built with ❤️ for a circular economy**
