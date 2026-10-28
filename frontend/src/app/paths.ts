/** Page URLs, built in one place. */

/** A donation page with this query parameter opens its chat panel (components/chat.tsx). */
export const CHAT_PARAM = 'chat';
export const CHAT_PARAM_OPEN = 'open';
export const withChatOpen = (path: string) => `${path}?${CHAT_PARAM}=${CHAT_PARAM_OPEN}`;

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
  sendToRecycling: '/donor/donations/recycle',
  donation: (id: string) => `/donor/donations/${id}`,
  candidates: (id: string) => `/donor/donations/${id}/candidates`,
  bookPickup: (id: string) => `/donor/donations/${id}/book-pickup`,
  bookRecyclerPickup: (id: string) => `/donor/donations/${id}/book-recycler-pickup`,
  wallet: '/donor/wallet',

  acceptor: '/acceptor',
  acceptorProfile: '/acceptor/profile',
  offer: (matchId: string) => `/acceptor/offers/${matchId}`,
  heldDonation: (id: string) => `/acceptor/donations/${id}`,

  admin: '/admin',
  adminDonation: (id: string) => `/admin/donations/${id}`,
  adminOrganisation: (id: string) => `/admin/organisations/${id}`,
};
