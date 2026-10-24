/** Page URLs, built in one place. */

export const paths = {
  home: '/',
  login: '/login',
  register: '/register',
  registerDonor: '/register/donor',
  registerOrganisation: '/register/organisation',
  map: '/map',
  notifications: '/notifications',

  donor: '/donor',
  newDonation: '/donor/donations/new',
  donation: (id: string) => `/donor/donations/${id}`,
  candidates: (id: string) => `/donor/donations/${id}/candidates`,

  acceptor: '/acceptor',
  offer: (matchId: string) => `/acceptor/offers/${matchId}`,
  heldDonation: (id: string) => `/acceptor/donations/${id}`,

  admin: '/admin',
  adminDonation: (id: string) => `/admin/donations/${id}`,
};
