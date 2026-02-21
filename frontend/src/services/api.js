const API_BASE_URL = 'http://localhost:8000/api';

// Helper function to handle API responses
const handleResponse = async (response) => {
    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        const error = new Error(data.detail || data.error || 'Request failed');
        if (data.errors) {
            error.fieldErrors = data.errors;
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
};

export default api;
