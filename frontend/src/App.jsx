import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { useEffect } from 'react';
import Landing from './pages/Landing';
import Login from './pages/Login';
import Register from './pages/Register';
import DonorDashboard from './pages/DonorDashboard';
import AcceptorDashboard from './pages/AcceptorDashboard';
import CreateDonation from './pages/CreateDonation';
import ChatThread from './pages/ChatThread';

// Admin redirect to Django admin panel
function AdminRedirect() {
  useEffect(() => {
    window.location.href = 'http://localhost:8000/admin/';
  }, []);
  return <div className="min-h-screen flex items-center justify-center">Redirecting to admin panel...</div>;
}

// Protected Route Component
function ProtectedRoute({ children, allowedRoles }) {
  const { user, token } = useAuth();

  if (!token || !user) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return <Navigate to="/" replace />;
  }

  return children;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      {/* Donor Routes */}
      <Route
        path="/donor/dashboard"
        element={
          <ProtectedRoute allowedRoles={['DONOR']}>
            <DonorDashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/donor/donate"
        element={
          <ProtectedRoute allowedRoles={['DONOR']}>
            <CreateDonation />
          </ProtectedRoute>
        }
      />

      {/* Acceptor Routes */}
      <Route
        path="/acceptor/dashboard"
        element={
          <ProtectedRoute allowedRoles={['ACCEPTOR']}>
            <AcceptorDashboard />
          </ProtectedRoute>
        }
      />

      {/* Admin Route - redirect to Django admin */}
      <Route
        path="/admin/*"
        element={
          <ProtectedRoute allowedRoles={['ADMIN']}>
            <AdminRedirect />
          </ProtectedRoute>
        }
      />

      {/* Chat Route - accessible by both donors and acceptors */}
      <Route
        path="/chat/:donationId"
        element={
          <ProtectedRoute allowedRoles={['DONOR', 'ACCEPTOR']}>
            <ChatThread />
          </ProtectedRoute>
        }
      />

      {/* Catch all */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <Router>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </Router>
  );
}
