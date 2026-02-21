import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Leaf, Package, CheckCircle, Clock, LogOut, MessageCircle, Loader2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

export default function AcceptorDashboard() {
    const { user, token, logout } = useAuth();
    const navigate = useNavigate();
    const [donations, setDonations] = useState([]);
    const [loading, setLoading] = useState(true);
    const [acceptingId, setAcceptingId] = useState(null);
    const [unreadCount, setUnreadCount] = useState(0);

    useEffect(() => {
        loadDonations();
    }, []);

    const loadDonations = async () => {
        try {
            const [data, unread] = await Promise.all([
                api.getDonations(token),
                api.getUnreadCount(token).catch(() => ({ unread_count: 0 })),
            ]);
            const donationsList = Array.isArray(data) ? data : (data?.results || []);
            setDonations(donationsList);
            setUnreadCount(unread.unread_count || 0);
        } catch (err) {
            console.error('Error:', err);
            setDonations([]);
        } finally {
            setLoading(false);
        }
    };

    const handleAccept = async (id) => {
        setAcceptingId(id);
        try {
            await api.acceptDonation(token, id);
            await loadDonations();
        } catch (err) {
            console.error('Error accepting:', err);
        } finally {
            setAcceptingId(null);
        }
    };

    const handleLogout = () => {
        logout();
        navigate('/');
    };

    const pendingDonations = donations.filter(d => d.status === 'CREATED' || d.status === 'MATCHED');
    const acceptedDonations = donations.filter(d => ['ACCEPTED', 'PICKUP_SCHEDULED', 'IN_TRANSIT', 'DELIVERED', 'COMPLETED'].includes(d.status));

    const statusColors = {
        CREATED: 'bg-blue-100 text-blue-700',
        MATCHED: 'bg-purple-100 text-purple-700',
        ACCEPTED: 'bg-green-100 text-green-700',
        PICKUP_SCHEDULED: 'bg-yellow-100 text-yellow-700',
        IN_TRANSIT: 'bg-orange-100 text-orange-700',
        DELIVERED: 'bg-teal-100 text-teal-700',
        COMPLETED: 'bg-emerald-100 text-emerald-700',
    };

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50">
                <Loader2 className="w-10 h-10 text-green-600 animate-spin" />
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-gray-50 to-emerald-50" style={{ fontFamily: "'Inter', sans-serif" }}>
            {/* Navbar */}
            <nav className="bg-white/80 backdrop-blur-lg shadow-sm sticky top-0 z-50">
                <div className="container mx-auto px-6 py-4 flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                        <div className="bg-gradient-to-r from-green-600 to-emerald-600 p-1.5 rounded-lg">
                            <Leaf className="w-5 h-5 text-white" />
                        </div>
                        <span className="text-lg font-bold bg-gradient-to-r from-green-700 to-emerald-600 bg-clip-text text-transparent">ReLoop</span>
                        <span className="text-xs bg-emerald-100 text-emerald-700 px-2 py-1 rounded-full font-medium">NGO</span>
                    </div>
                    <div className="flex items-center space-x-4">
                        <span className="text-sm text-gray-500">{user?.username}</span>
                        {unreadCount > 0 && (
                            <span className="px-2 py-1 bg-red-500 text-white text-xs font-bold rounded-full">{unreadCount}</span>
                        )}
                        <button onClick={handleLogout} className="text-gray-400 hover:text-red-500 transition">
                            <LogOut className="w-5 h-5" />
                        </button>
                    </div>
                </div>
            </nav>

            <div className="container mx-auto px-6 py-8">
                <div className="mb-8">
                    <h1 className="text-2xl font-bold text-gray-900">NGO Dashboard</h1>
                    <p className="text-gray-500 text-sm">Accept and manage incoming donations</p>
                </div>

                {/* Stats */}
                <div className="grid grid-cols-3 gap-4 mb-8">
                    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5">
                        <div className="flex items-center space-x-3 mb-2">
                            <div className="p-2 rounded-xl bg-blue-100">
                                <Clock className="w-5 h-5 text-blue-600" />
                            </div>
                        </div>
                        <div className="text-2xl font-bold text-gray-900">{pendingDonations.length}</div>
                        <div className="text-xs text-gray-500">Pending</div>
                    </div>
                    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5">
                        <div className="flex items-center space-x-3 mb-2">
                            <div className="p-2 rounded-xl bg-green-100">
                                <CheckCircle className="w-5 h-5 text-green-600" />
                            </div>
                        </div>
                        <div className="text-2xl font-bold text-gray-900">{acceptedDonations.length}</div>
                        <div className="text-xs text-gray-500">Accepted</div>
                    </div>
                    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5">
                        <div className="flex items-center space-x-3 mb-2">
                            <div className="p-2 rounded-xl bg-purple-100">
                                <Package className="w-5 h-5 text-purple-600" />
                            </div>
                        </div>
                        <div className="text-2xl font-bold text-gray-900">{donations.length}</div>
                        <div className="text-xs text-gray-500">Total Items</div>
                    </div>
                </div>

                {/* Pending Donations */}
                <div className="bg-white rounded-2xl shadow-sm border border-gray-100 mb-6">
                    <div className="p-6 border-b border-gray-100">
                        <h2 className="text-lg font-bold text-gray-900 flex items-center space-x-2">
                            <Clock className="w-5 h-5 text-blue-600" />
                            <span>Available Donations</span>
                            {pendingDonations.length > 0 && (
                                <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs font-bold rounded-full">{pendingDonations.length}</span>
                            )}
                        </h2>
                    </div>
                    {pendingDonations.length === 0 ? (
                        <div className="p-12 text-center text-gray-400">
                            <p>No pending donations at the moment</p>
                        </div>
                    ) : (
                        <div className="divide-y divide-gray-50">
                            {pendingDonations.map((donation) => (
                                <div key={donation.id} className="p-5 hover:bg-gray-50 transition">
                                    <div className="flex items-center justify-between">
                                        <div className="flex-1">
                                            <div className="flex items-center space-x-3 mb-1">
                                                <span className="text-lg">
                                                    {donation.category === 'CLOTHES' ? '👕' : donation.category === 'TOYS' ? '🧸' : '📚'}
                                                </span>
                                                <h3 className="font-semibold text-gray-900">{donation.category} × {donation.quantity}</h3>
                                                {donation.is_priority && (
                                                    <span className="px-2 py-0.5 bg-orange-100 text-orange-700 text-xs font-bold rounded-full">⚡ Priority</span>
                                                )}
                                            </div>
                                            <p className="text-sm text-gray-500">{donation.description || 'No description'}</p>
                                            <p className="text-xs text-gray-400 mt-1">by {donation.donor_name} • {donation.pickup_address}</p>
                                        </div>
                                        <button
                                            onClick={() => handleAccept(donation.id)}
                                            disabled={acceptingId === donation.id}
                                            className="px-4 py-2 bg-green-600 text-white rounded-xl text-sm font-semibold hover:bg-green-700 transition disabled:opacity-50 flex items-center space-x-2"
                                        >
                                            {acceptingId === donation.id ? (
                                                <Loader2 className="w-4 h-4 animate-spin" />
                                            ) : (
                                                <span>Accept</span>
                                            )}
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* Accepted Donations */}
                {acceptedDonations.length > 0 && (
                    <div className="bg-white rounded-2xl shadow-sm border border-gray-100">
                        <div className="p-6 border-b border-gray-100">
                            <h2 className="text-lg font-bold text-gray-900 flex items-center space-x-2">
                                <CheckCircle className="w-5 h-5 text-green-600" />
                                <span>Accepted Donations</span>
                            </h2>
                        </div>
                        <div className="divide-y divide-gray-50">
                            {acceptedDonations.map((donation) => (
                                <div key={donation.id} className="p-5 hover:bg-gray-50 transition">
                                    <div className="flex items-center justify-between">
                                        <div className="flex-1">
                                            <div className="flex items-center space-x-3 mb-1">
                                                <span className="text-lg">
                                                    {donation.category === 'CLOTHES' ? '👕' : donation.category === 'TOYS' ? '🧸' : '📚'}
                                                </span>
                                                <h3 className="font-semibold text-gray-900">{donation.category} × {donation.quantity}</h3>
                                                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusColors[donation.status] || 'bg-gray-100 text-gray-600'}`}>
                                                    {donation.status?.replace(/_/g, ' ')}
                                                </span>
                                            </div>
                                            <p className="text-sm text-gray-500">by {donation.donor_name}</p>
                                        </div>
                                        <Link
                                            to={`/chat/${donation.id}`}
                                            className="p-2 text-gray-400 hover:text-green-600 hover:bg-green-50 rounded-lg transition"
                                        >
                                            <MessageCircle className="w-5 h-5" />
                                        </Link>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
