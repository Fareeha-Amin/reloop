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
import { Landing } from './pages/Landing';
import { Notifications } from './pages/Notifications';
import { NotFound, Placeholder } from './pages/Placeholder';
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
      { path: '/map', element: <Placeholder /> },
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
      // Second half of Phase 3: acceptor dashboard and admin panel (labelled stubs until then).
      { path: '/acceptor/*', element: <RequireRole role={ROLE.acceptor}><Placeholder /></RequireRole> },
      { path: '/admin/*', element: <RequireRole role={ROLE.admin}><Placeholder /></RequireRole> },
      { path: '*', element: <NotFound /> },
    ],
  },
]);

export function App() {
  return <RouterProvider router={router} />;
}
