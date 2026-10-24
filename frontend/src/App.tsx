import { createBrowserRouter, RouterProvider } from 'react-router';

import { AppShell } from './components/AppShell';
import { RequireRole, RequireSession } from './components/RequireRole';
import { Login } from './pages/auth/Login';
import { RegisterChoice } from './pages/auth/RegisterChoice';
import { RegisterDonor } from './pages/auth/RegisterDonor';
import { RegisterOrganisation } from './pages/auth/RegisterOrganisation';
import { Candidates } from './pages/donor/Candidates';
import { DonationDetail } from './pages/donor/DonationDetail';
import { DonorDashboard } from './pages/donor/DonorDashboard';
import { NewDonation } from './pages/donor/NewDonation';
import { AcceptorDashboard } from './pages/acceptor/AcceptorDashboard';
import { HeldDonation } from './pages/acceptor/HeldDonation';
import { OfferDetail } from './pages/acceptor/OfferDetail';
import { AdminDonation } from './pages/admin/AdminDonation';
import { AdminOrganisation } from './pages/admin/AdminOrganisation';
import { AdminPanel } from './pages/admin/AdminPanel';
import { DiscoveryMap } from './pages/DiscoveryMap';
import { Landing } from './pages/Landing';
import { NotFound } from './pages/NotFound';
import { Notifications } from './pages/Notifications';
import { ROLE } from './vocab/roles';

const router = createBrowserRouter([
  {
    element: <AppShell />,
    children: [
      { path: '/', element: <Landing /> },
      { path: '/login', element: <Login /> },
      { path: '/register', element: <RegisterChoice /> },
      { path: '/register/donor', element: <RegisterDonor /> },
      { path: '/register/organisation', element: <RegisterOrganisation /> },
      { path: '/map', element: <DiscoveryMap /> },
      {
        path: '/notifications',
        element: (
          <RequireSession>
            <Notifications />
          </RequireSession>
        ),
      },
      {
        path: '/donor',
        element: <RequireRole role={ROLE.donor}><DonorDashboard /></RequireRole>,
      },
      {
        path: '/donor/donations/new',
        element: <RequireRole role={ROLE.donor}><NewDonation /></RequireRole>,
      },
      {
        path: '/donor/donations/:id',
        element: <RequireRole role={ROLE.donor}><DonationDetail /></RequireRole>,
      },
      {
        path: '/donor/donations/:id/candidates',
        element: <RequireRole role={ROLE.donor}><Candidates /></RequireRole>,
      },
      {
        path: '/acceptor',
        element: <RequireRole role={ROLE.acceptor}><AcceptorDashboard /></RequireRole>,
      },
      {
        path: '/acceptor/offers/:matchId',
        element: <RequireRole role={ROLE.acceptor}><OfferDetail /></RequireRole>,
      },
      {
        path: '/acceptor/donations/:id',
        element: <RequireRole role={ROLE.acceptor}><HeldDonation /></RequireRole>,
      },
      {
        path: '/admin',
        element: <RequireRole role={ROLE.admin}><AdminPanel /></RequireRole>,
      },
      {
        path: '/admin/donations/:id',
        element: <RequireRole role={ROLE.admin}><AdminDonation /></RequireRole>,
      },
      {
        path: '/admin/organisations/:id',
        element: <RequireRole role={ROLE.admin}><AdminOrganisation /></RequireRole>,
      },
      { path: '*', element: <NotFound /> },
    ],
  },
]);

export function App() {
  return <RouterProvider router={router} />;
}
