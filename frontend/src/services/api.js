const API_BASE_URL = 'http://localhost:8000/api';

// Helper function to handle API responses
const handleResponse = async (response) => {
    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        const message = data.detail || data.error || data.message || 'Request failed';
        const error = new Error(message);
        // Django returns field-level errors under 'errors' key
        if (data.errors) {
            error.fieldErrors = data.errors;
        }
        // Also handle DRF's default format where field names are top-level keys
        if (!data.errors && !data.detail && !data.error && typeof data === 'object') {
            const fieldKeys = Object.keys(data).filter(k => Array.isArray(data[k]));
            if (fieldKeys.length > 0) {
                error.fieldErrors = {};
                fieldKeys.forEach(k => { error.fieldErrors[k] = data[k]; });
            }
        }
        throw error;
    }

    return data;
};


const api = {
    // Auth
    register: async (data) => {
        try {
            const response = await fetch(`${API_BASE_URL}/users/register/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            });
            return await handleResponse(response);
        } catch (error) {
            console.error('Register error:', error);
            throw error;
        }
    },

    login: async (data) => {
        try {
            const response = await fetch(`${API_BASE_URL}/users/login/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            });
            return await handleResponse(response);
        } catch (error) {
            console.error('Login error:', error);
            throw error;
        }
    },

    // Donations
    getDonations: async (token) => {
        try {
            const response = await fetch(`${API_BASE_URL}/donations/`, {
                headers: { 'Authorization': `Bearer ${token}` },
            });
            return await handleResponse(response);
        } catch (error) {
            console.error('Get donations error:', error);
            throw error;
        }
    },

    createDonation: async (token, formData) => {
        try {
            const response = await fetch(`${API_BASE_URL}/donations/`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` },
                body: formData,
            });
            return await handleResponse(response);
        } catch (error) {
            console.error('Create donation error:', error);
            throw error;
        }
    },

    acceptDonation: async (token, id) => {
        try {
            const response = await fetch(`${API_BASE_URL}/donations/${id}/accept/`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` },
            });
            return await handleResponse(response);
        } catch (error) {
            console.error('Accept donation error:', error);
            throw error;
        }
    },

    rejectDonation: async (token, id) => {
        try {
            const response = await fetch(`${API_BASE_URL}/donations/${id}/reject/`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` },
            });
            return await handleResponse(response);
        } catch (error) {
            console.error('Reject donation error:', error);
            throw error;
        }
    },

    updateDonationStatus: async (token, id, status) => {
        try {
            const response = await fetch(`${API_BASE_URL}/donations/${id}/status/`, {
                method: 'PATCH',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ status }),
            });
            return await handleResponse(response);
        } catch (error) {
            console.error('Update donation status error:', error);
            throw error;
        }
    },

    // AI - NGO Suggestions
    getSuggestedNGOs: async (token, category, lat, lon) => {
        try {
            const params = new URLSearchParams();
            if (category) params.append('category', category);
            if (lat) params.append('lat', lat);
            if (lon) params.append('lon', lon);
            const response = await fetch(`${API_BASE_URL}/ai/suggest-ngos/?${params}`, {
                headers: { 'Authorization': `Bearer ${token}` },
            });
            return await handleResponse(response);
        } catch (error) {
            console.error('Get suggested NGOs error:', error);
            throw error;
        }
    },

    // User Profile (base user fields: first_name, last_name, email, phone_number)
    getUserProfile: async (token) => {
        try {
            const response = await fetch(`${API_BASE_URL}/users/profile/`, {
                headers: { 'Authorization': `Bearer ${token}` },
            });
            return await handleResponse(response);
        } catch (error) {
            console.error('Get user profile error:', error);
            throw error;
        }
    },

    updateUserProfile: async (token, data) => {
        try {
            const response = await fetch(`${API_BASE_URL}/users/profile/`, {
                method: 'PATCH',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data),
            });
            return await handleResponse(response);
        } catch (error) {
            console.error('Update user profile error:', error);
            throw error;
        }
    },

    // Donor Profile
    getDonorProfile: async (token) => {
        try {
            const response = await fetch(`${API_BASE_URL}/users/donor-profile/`, {
                headers: { 'Authorization': `Bearer ${token}` },
            });
            return await handleResponse(response);
        } catch (error) {
            console.error('Get donor profile error:', error);
            throw error;
        }
    },

    updateDonorProfile: async (token, data) => {
        try {
            const response = await fetch(`${API_BASE_URL}/users/donor-profile/`, {
                method: 'PATCH',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data),
            });
            return await handleResponse(response);
        } catch (error) {
            console.error('Update donor profile error:', error);
            throw error;
        }
    },

    // Acceptor Profile
    getAcceptorProfile: async (token) => {
        try {
            const response = await fetch(`${API_BASE_URL}/users/acceptor-profile/`, {
                headers: { 'Authorization': `Bearer ${token}` },
            });
            return await handleResponse(response);
        } catch (error) {
            console.error('Get acceptor profile error:', error);
            throw error;
        }
    },

    updateAcceptorProfile: async (token, data) => {
        try {
            const response = await fetch(`${API_BASE_URL}/users/acceptor-profile/`, {
                method: 'PATCH',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data),
            });
            return await handleResponse(response);
        } catch (error) {
            console.error('Update acceptor profile error:', error);
            throw error;
        }
    },

    // Donor Actions (re-match, upgrade priority, waste redirect)
    submitDonorAction: async (token, donationId, action) => {
        try {
            const response = await fetch(`${API_BASE_URL}/donations/${donationId}/donor-action/`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ action }),
            });
            return await handleResponse(response);
        } catch (error) {
            console.error('Donor action error:', error);
            throw error;
        }
    },

    // Acceptors
    getNearbyAcceptors: async (token, lat, lon, category = '', maxDistance = 50) => {
        try {
            const params = new URLSearchParams({ lat, lon, max_distance: maxDistance });
            if (category) params.append('category', category);
            const response = await fetch(`${API_BASE_URL}/acceptors/nearby/?${params}`, {
                headers: { 'Authorization': `Bearer ${token}` },
            });
            return await handleResponse(response);
        } catch (error) {
            console.error('Get nearby acceptors error:', error);
            throw error;
        }
    },

    // Analytics
    getImpactDashboard: async (token) => {
        try {
            const response = await fetch(`${API_BASE_URL}/analytics/dashboard/`, {
                headers: { 'Authorization': `Bearer ${token}` },
            });
            return await handleResponse(response);
        } catch (error) {
            console.error('Get impact dashboard error:', error);
            throw error;
        }
    },

    getLeaderboard: async (token, type = 'donors') => {
        try {
            const response = await fetch(`${API_BASE_URL}/analytics/leaderboard/?type=${type}`, {
                headers: { 'Authorization': `Bearer ${token}` },
            });
            return await handleResponse(response);
        } catch (error) {
            console.error('Get leaderboard error:', error);
            throw error;
        }
    },

    // Messaging
    getMessages: async (token, donationId) => {
        try {
            const response = await fetch(`${API_BASE_URL}/messaging/${donationId}/`, {
                headers: { 'Authorization': `Bearer ${token}` },
            });
            return await handleResponse(response);
        } catch (error) {
            console.error('Get messages error:', error);
            throw error;
        }
    },

    sendMessage: async (token, donationId, content) => {
        try {
            const response = await fetch(`${API_BASE_URL}/messaging/${donationId}/`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ content }),
            });
            return await handleResponse(response);
        } catch (error) {
            console.error('Send message error:', error);
            throw error;
        }
    },

    getUnreadCount: async (token) => {
        try {
            const response = await fetch(`${API_BASE_URL}/messaging/unread/`, {
                headers: { 'Authorization': `Bearer ${token}` },
            });
            return await handleResponse(response);
        } catch (error) {
            console.error('Get unread count error:', error);
            throw error;
        }
    },

    // Payments
    initiatePayment: async (token, data) => {
        try {
            const response = await fetch(`${API_BASE_URL}/payments/initiate/`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data),
            });
            return await handleResponse(response);
        } catch (error) {
            console.error('Initiate payment error:', error);
            throw error;
        }
    },

    completePayment: async (token, paymentId) => {
        try {
            const response = await fetch(`${API_BASE_URL}/payments/${paymentId}/complete/`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` },
            });
            return await handleResponse(response);
        } catch (error) {
            console.error('Complete payment error:', error);
            throw error;
        }
    },

    getPayments: async (token) => {
        try {
            const response = await fetch(`${API_BASE_URL}/payments/`, {
                headers: { 'Authorization': `Bearer ${token}` },
            });
            return await handleResponse(response);
        } catch (error) {
            console.error('Get payments error:', error);
            throw error;
        }
    },

    // Donation CRUD
    getDonation: async (token, id) => {
        try {
            const response = await fetch(`${API_BASE_URL}/donations/${id}/`, {
                headers: { 'Authorization': `Bearer ${token}` },
            });
            return await handleResponse(response);
        } catch (error) {
            console.error('Get donation error:', error);
            throw error;
        }
    },

    updateDonation: async (token, id, data) => {
        try {
            const response = await fetch(`${API_BASE_URL}/donations/${id}/`, {
                method: 'PATCH',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data),
            });
            return await handleResponse(response);
        } catch (error) {
            console.error('Update donation error:', error);
            throw error;
        }
    },

    deleteDonation: async (token, id) => {
        try {
            const response = await fetch(`${API_BASE_URL}/donations/${id}/`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` },
            });
            if (response.status === 204) return {};
            return await handleResponse(response);
        } catch (error) {
            console.error('Delete donation error:', error);
            throw error;
        }
    },

    rejectDonation: async (token, id) => {
        try {
            const response = await fetch(`${API_BASE_URL}/donations/${id}/reject/`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` },
            });
            return await handleResponse(response);
        } catch (error) {
            console.error('Reject donation error:', error);
            throw error;
        }
    },

    triggerFallback: async (token, donationId) => {
        try {
            const response = await fetch(`${API_BASE_URL}/donations/${donationId}/fallback/`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` },
            });
            return await handleResponse(response);
        } catch (error) {
            console.error('Trigger fallback error:', error);
            throw error;
        }
    },

    // Per-donation unread counts
    getPerDonationUnread: async (token) => {
        try {
            const response = await fetch(`${API_BASE_URL}/messaging/unread/per-donation/`, {
                headers: { 'Authorization': `Bearer ${token}` },
            });
            return await handleResponse(response);
        } catch (error) {
            console.error('Get per-donation unread error:', error);
            throw error;
        }
    },

    // Needs List CRUD
    getNeeds: async (token) => {
        try {
            const response = await fetch(`${API_BASE_URL}/acceptors/needs/`, {
                headers: { 'Authorization': `Bearer ${token}` },
            });
            return await handleResponse(response);
        } catch (error) {
            console.error('Get needs error:', error);
            throw error;
        }
    },

    createNeed: async (token, data) => {
        try {
            const response = await fetch(`${API_BASE_URL}/acceptors/needs/`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data),
            });
            return await handleResponse(response);
        } catch (error) {
            console.error('Create need error:', error);
            throw error;
        }
    },

    updateNeed: async (token, id, data) => {
        try {
            const response = await fetch(`${API_BASE_URL}/acceptors/needs/${id}/`, {
                method: 'PATCH',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data),
            });
            return await handleResponse(response);
        } catch (error) {
            console.error('Update need error:', error);
            throw error;
        }
    },

    deleteNeed: async (token, id) => {
        try {
            const response = await fetch(`${API_BASE_URL}/acceptors/needs/${id}/`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` },
            });
            if (response.status === 204) return {};
            return await handleResponse(response);
        } catch (error) {
            console.error('Delete need error:', error);
            throw error;
        }
    },

    // Nearby acceptors for map
    getWasteCollectors: async (token) => {
        try {
            const response = await fetch(`${API_BASE_URL}/donations/waste-collectors/`, {
                headers: { 'Authorization': `Bearer ${token}` },
            });
            return await handleResponse(response);
        } catch (error) {
            console.error('Get waste collectors error:', error);
            return [];
        }
    },
};

export default api;
