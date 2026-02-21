import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Leaf, Package, Recycle, TreePine, Award, Plus, LogOut, MessageCircle, ChevronDown, ChevronUp, Loader2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

// Simple bar chart component
function MiniBarChart({ data, color = '#16a34a' }) {
    const max = Math.max(...data.map(d => d.value), 1);
    return (
        <div className="flex items-end space-x-1 h-16">
            {data.map((d, i) => (
                <div key={i} className="flex flex-col items-center flex-1">
                    <div
                        className="w-full rounded-t transition-all duration-500"
                        style={{
                            height: `${(d.value / max) * 100}%`,
                            backgroundColor: color,
                            minHeight: '2px',
                            opacity: 0.7 + (i / data.length) * 0.3,
                        }}
                    />
                    <span className="text-[9px] text-gray-400 mt-1">{d.label}</span>
                </div>
            ))}
        </div>
    );
}

export default function DonorDashboard() {
    const { user, token, logout } = useAuth();
    const navigate = useNavigate();
    const [donations, setDonations] = useState([]);
    const [loading, setLoading] = useState(true);
    const [expandedMetric, setExpandedMetric] = useState(null);
    const [unreadCount, setUnreadCount] = useState(0);

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        try {
            const [donationsData, unread] = await Promise.all([
                api.getDonations(token),
                api.getUnreadCount(token).catch(() => ({ unread_count: 0 })),
            ]);
            const donationsList = Array.isArray(donationsData) ? donationsData : (donationsData?.results || []);
            setDonations(donationsList);
            setUnreadCount(unread.unread_count || 0);
        } catch (err) {
            console.error('Error loading data:', err);
            setDonations([]);
        } finally {
            setLoading(false);
        }
    };

    const handleLogout = () => {
        logout();
        navigate('/');
    };

    // Calculate metrics
    const totalDonations = donations.length;
    const completedDonations = donations.filter(d => d.status === 'COMPLETED' || d.status === 'DELIVERED').length;
    const wasteKg = donations.reduce((acc, d) => {
        const weights = { CLOTHES: 0.5, TOYS: 0.3, BOOKS: 0.8 };
        return acc + ((d.quantity || 0) * (weights[d.category] || 0.5));
    }, 0);
    const carbonOffset = (wasteKg * 2.1).toFixed(1);

    // Category breakdown
    const catBreakdown = donations.reduce((acc, d) => {
        acc[d.category] = (acc[d.category] || 0) + 1;
        return acc;
    }, {});

    // Monthly data (last 6 months)
    const monthlyData = Array.from({ length: 6 }, (_, i) => {
        const d = new Date();
        d.setMonth(d.getMonth() - (5 - i));
        const m = d.toLocaleString('default', { month: 'short' });
        const count = donations.filter(don => {
            const created = new Date(don.created_at);
            return created.getMonth() === d.getMonth() && created.getFullYear() === d.getFullYear();
        }).length;
        return { label: m, value: count };
    });

    const statusColors = {
        CREATED: 'bg-blue-100 text-blue-700',
        MATCHED: 'bg-purple-100 text-purple-700',
        ACCEPTED: 'bg-green-100 text-green-700',
        PICKUP_SCHEDULED: 'bg-yellow-100 text-yellow-700',
        IN_TRANSIT: 'bg-orange-100 text-orange-700',
        DELIVERED: 'bg-teal-100 text-teal-700',
        COMPLETED: 'bg-emerald-100 text-emerald-700',
        REJECTED: 'bg-red-100 text-red-700',
        WASTE_COLLECTED: 'bg-amber-100 text-amber-700',
    };

    const metrics = [
        {
            key: 'total',
            label: 'Total Donations',
            value: totalDonations,
            icon: Package,
            color: 'from-blue-500 to-blue-600',
            detail: (
                <div className="space-y-2">
                    {Object.entries(catBreakdown).map(([cat, count]) => (
                        <div key={cat} className="flex justify-between text-sm">
                            <span className="text-gray-600">{cat}</span>
                            <span className="font-semibold">{count}</span>
                        </div>
                    ))}
                </div>
            ),
        },
        {
            key: 'waste',
            label: 'Waste Diverted',
            value: `${wasteKg.toFixed(1)} kg`,
            icon: Recycle,
            color: 'from-green-500 to-emerald-600',
            detail: <MiniBarChart data={monthlyData} color="#16a34a" />,
        },
        {
            key: 'carbon',
            label: 'Carbon Offset',
            value: `${carbonOffset} kg`,
            icon: TreePine,
            color: 'from-teal-500 to-teal-600',
            detail: (
                <p className="text-sm text-gray-600">
                    Equivalent to planting <strong>{Math.floor(parseFloat(carbonOffset) / 10)}</strong> trees 🌳
                </p>
            ),
        },
        {
            key: 'impact',
            label: 'Impact Level',
            value: totalDonations >= 10 ? 'Gold' : totalDonations >= 5 ? 'Silver' : 'Bronze',
            icon: Award,
            color: 'from-amber-500 to-yellow-600',
            detail: (
                <div className="text-sm text-gray-600">
                    <p>{completedDonations} completed out of {totalDonations} total</p>
                    <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                        <div className="bg-amber-500 h-2 rounded-full transition-all" style={{ width: `${totalDonations > 0 ? (completedDonations / totalDonations * 100) : 0}%` }} />
                    </div>
                </div>
            ),
        },
    ];

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50">
                <Loader2 className="w-10 h-10 text-green-600 animate-spin" />
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-gray-50 to-green-50" style={{ fontFamily: "'Inter', sans-serif" }}>
            {/* Navbar */}
            <nav className="bg-white/80 backdrop-blur-lg shadow-sm sticky top-0 z-50">
                <div className="container mx-auto px-6 py-4 flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                        <div className="bg-gradient-to-r from-green-600 to-emerald-600 p-1.5 rounded-lg">
                            <Leaf className="w-5 h-5 text-white" />
                        </div>
                        <span className="text-lg font-bold bg-gradient-to-r from-green-700 to-emerald-600 bg-clip-text text-transparent">ReLoop</span>
                    </div>
                    <div className="flex items-center space-x-4">
                        <span className="text-sm text-gray-500">Hi, <strong>{user?.first_name || user?.username}</strong></span>
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
                <div className="flex items-center justify-between mb-8">
                    <div>
                        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
                        <p className="text-gray-500 text-sm">Track your impact and manage donations</p>
                    </div>
                    <Link to="/donor/donate" className="btn-primary flex items-center space-x-2">
                        <Plus className="w-5 h-5" />
                        <span>New Donation</span>
                    </Link>
                </div>

                {/* Metrics Grid */}
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
                    {metrics.map((metric) => {
                        const Icon = metric.icon;
                        const isExpanded = expandedMetric === metric.key;
                        return (
                            <div key={metric.key}>
                                <div
                                    onClick={() => setExpandedMetric(isExpanded ? null : metric.key)}
                                    className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 cursor-pointer hover:shadow-md transition-all duration-200 group"
                                >
                                    <div className="flex items-center justify-between mb-3">
                                        <div className={`p-2 rounded-xl bg-gradient-to-r ${metric.color}`}>
                                            <Icon className="w-5 h-5 text-white" />
                                        </div>
                                        <div className="text-gray-300 group-hover:text-gray-400 transition">
                                            {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                                        </div>
                                    </div>
                                    <div className="text-2xl font-bold text-gray-900">{metric.value}</div>
                                    <div className="text-xs text-gray-500 mt-1">{metric.label}</div>
                                </div>
                                {isExpanded && (
                                    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4 mt-2 animate-fadeIn">
                                        {metric.detail}
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>

                {/* Donations List */}
                <div className="bg-white rounded-2xl shadow-sm border border-gray-100">
                    <div className="p-6 border-b border-gray-100">
                        <h2 className="text-lg font-bold text-gray-900">Your Donations</h2>
                    </div>
                    {donations.length === 0 ? (
                        <div className="p-12 text-center text-gray-400">
                            <Package className="w-12 h-12 mx-auto mb-3 opacity-50" />
                            <p className="font-medium">No donations yet</p>
                            <p className="text-sm">Create your first donation to get started!</p>
                        </div>
                    ) : (
                        <div className="divide-y divide-gray-50">
                            {donations.map((donation) => (
                                <div key={donation.id} className="p-5 hover:bg-gray-50 transition group">
                                    <div className="flex items-center justify-between">
                                        <div className="flex-1">
                                            <div className="flex items-center space-x-3 mb-1">
                                                <span className="text-lg">
                                                    {donation.category === 'CLOTHES' ? '👕' : donation.category === 'TOYS' ? '🧸' : '📚'}
                                                </span>
                                                <h3 className="font-semibold text-gray-900">
                                                    {donation.category} × {donation.quantity}
                                                </h3>
                                                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusColors[donation.status] || 'bg-gray-100 text-gray-600'}`}>
                                                    {donation.status?.replace(/_/g, ' ')}
                                                </span>
                                            </div>
                                            <p className="text-sm text-gray-500">{donation.description || 'No description'}</p>
                                            {donation.ai_suggested_acceptor_name && (
                                                <p className="text-xs text-green-600 mt-1">→ {donation.ai_suggested_acceptor_name}</p>
                                            )}
                                        </div>
                                        <div className="flex items-center space-x-2">
                                            {(donation.acceptor || donation.ai_suggested_acceptor) && (
                                                <Link
                                                    to={`/chat/${donation.id}`}
                                                    className="p-2 text-gray-400 hover:text-green-600 hover:bg-green-50 rounded-lg transition"
                                                >
                                                    <MessageCircle className="w-5 h-5" />
                                                </Link>
                                            )}
                                            <span className="text-xs text-gray-400">
                                                {new Date(donation.created_at).toLocaleDateString()}
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
