import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Package, Recycle, Leaf, Award, LogOut, Plus, Loader2, MessageCircle, ChevronDown, ChevronUp, Trash2, Edit3, Wallet } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

const MiniBarChart = ({ data, color }) => {
    const max = Math.max(...data.map(d => d.value), 1);
    return (
        <div className="flex items-end space-x-1 h-16">
            {data.map((d, i) => (
                <div key={i} className="flex-1 flex flex-col items-center">
                    <div className="w-full rounded-t-sm" style={{ height: `${(d.value / max) * 100}%`, backgroundColor: color, minHeight: '2px' }} />
                    <span className="text-[9px] text-gray-400 mt-1">{d.label}</span>
                </div>
            ))}
        </div>
    );
};

export default function DonorDashboard() {
    const { user, token, logout } = useAuth();
    const navigate = useNavigate();
    const [donations, setDonations] = useState([]);
    const [loading, setLoading] = useState(true);
    const [expandedMetric, setExpandedMetric] = useState(null);
    const [unreadMap, setUnreadMap] = useState({});
    const [deletingId, setDeletingId] = useState(null);
    const [walletBalance, setWalletBalance] = useState(0);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const [donationsData, unreadData] = await Promise.all([
                    api.getDonations(token),
                    api.getPerDonationUnread(token).catch(() => ({})),
                ]);
                // Handle paginated response: { count, results } or flat array
                const donationsList = Array.isArray(donationsData) ? donationsData : (donationsData?.results || []);
                setDonations(donationsList);
                setUnreadMap(unreadData || {});
                // Try to get wallet balance from user profile
                if (user?.donor_profile?.wallet_balance) {
                    setWalletBalance(parseFloat(user.donor_profile.wallet_balance));
                }
            } catch (err) {
                console.error('Dashboard load error:', err);
            } finally {
                setLoading(false);
            }
        };
        fetchData();
        const interval = setInterval(async () => {
            try { setUnreadMap(await api.getPerDonationUnread(token).catch(() => ({}))); } catch { }
        }, 15000);
        return () => clearInterval(interval);
    }, [token]);

    const handleDelete = async (e, id) => {
        e.stopPropagation();
        if (!window.confirm('Delete this donation?')) return;
        setDeletingId(id);
        try {
            await api.deleteDonation(token, id);
            setDonations(prev => prev.filter(d => d.id !== id));
        } catch (err) {
            alert(err.message || 'Cannot delete this donation.');
        } finally {
            setDeletingId(null);
        }
    };

    const totalDonations = donations.length;
    const catBreakdown = {};
    donations.forEach(d => { catBreakdown[d.category] = (catBreakdown[d.category] || 0) + 1; });
    const wasteKg = donations.reduce((sum, d) => {
        const weights = { CLOTHES: 0.5, TOYS: 0.3, BOOKS: 0.8 };
        return sum + (d.quantity * (weights[d.category] || 0.5));
    }, 0);
    const carbonOffset = wasteKg * 2.5;
    const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const monthlyData = monthNames.map((label, i) => ({
        label,
        value: donations.filter(d => new Date(d.created_at).getMonth() === i).length,
    }));
    const completedCount = donations.filter(d => ['COMPLETED', 'DELIVERED'].includes(d.status)).length;
    const activeDonations = donations.filter(d => !['REJECTED', 'CANCELLED'].includes(d.status)).length;
    const completionPct = activeDonations > 0 ? Math.round((completedCount / activeDonations) * 100) : 0;

    const metrics = [
        {
            key: 'total', label: 'Total Donations', value: totalDonations, icon: Package, color: 'from-blue-500 to-blue-600',
            detail: (<div className="space-y-2">{Object.entries(catBreakdown).map(([cat, count]) => (
                <div key={cat} className="flex justify-between text-sm"><span className="text-gray-600">{cat}</span><span className="font-semibold">{count}</span></div>
            ))}</div>)
        },
        {
            key: 'waste', label: 'Waste Diverted', value: `${wasteKg.toFixed(1)} kg`, icon: Recycle, color: 'from-green-500 to-emerald-600',
            detail: <MiniBarChart data={monthlyData} color="#16a34a" />
        },
        {
            key: 'carbon', label: 'Carbon Offset', value: `${carbonOffset.toFixed(1)} kg`, icon: Leaf, color: 'from-teal-500 to-cyan-600',
            detail: (<div className="text-sm text-gray-600"><p>≈ {(carbonOffset / 21.7).toFixed(1)} trees planted</p><p className="mt-1">≈ {(carbonOffset / 2.3).toFixed(0)} km of driving offset</p></div>)
        },
        {
            key: 'impact', label: 'Completion Rate', value: `${completionPct}%`, icon: Award, color: 'from-purple-500 to-indigo-600',
            detail: (<div><div className="w-full bg-gray-200 rounded-full h-2.5"><div className="bg-purple-600 h-2.5 rounded-full transition-all" style={{ width: `${completionPct}%` }} /></div><p className="text-xs text-gray-500 mt-2">{completedCount} of {activeDonations} active donations completed</p></div>)
        },
    ];

    const STATUS_COLORS = {
        CREATED: 'bg-gray-100 text-gray-700', MATCHED: 'bg-blue-100 text-blue-700', ACCEPTED: 'bg-green-100 text-green-700',
        PICKUP_SCHEDULED: 'bg-indigo-100 text-indigo-700', IN_TRANSIT: 'bg-yellow-100 text-yellow-800',
        DELIVERED: 'bg-emerald-100 text-emerald-700', COMPLETED: 'bg-green-200 text-green-800',
        REJECTED: 'bg-red-100 text-red-700', CANCELLED: 'bg-gray-200 text-gray-600', WASTE_COLLECTED: 'bg-orange-100 text-orange-700',
    };

    if (loading) {
        return (<div className="min-h-screen bg-gray-50 flex items-center justify-center"><Loader2 className="w-8 h-8 text-green-600 animate-spin" /></div>);
    }

    return (
        <div className="min-h-screen bg-gray-50" style={{ fontFamily: "'Inter', sans-serif" }}>
            {/* Navbar */}
            <nav className="bg-white/80 backdrop-blur-lg border-b border-gray-200 sticky top-0 z-20">
                <div className="max-w-6xl mx-auto px-6 py-3 flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                        <div className="bg-gradient-to-r from-green-600 to-emerald-600 p-1.5 rounded-lg"><Leaf className="w-5 h-5 text-white" /></div>
                        <span className="text-xl font-bold bg-gradient-to-r from-green-700 to-emerald-600 bg-clip-text text-transparent">ReLoop</span>
                    </div>
                    <div className="flex items-center space-x-4">
                        {walletBalance > 0 && (
                            <div className="flex items-center space-x-1 px-3 py-1.5 bg-amber-50 rounded-lg border border-amber-200">
                                <Wallet className="w-4 h-4 text-amber-600" />
                                <span className="text-sm font-semibold text-amber-700">₹{walletBalance.toFixed(2)}</span>
                            </div>
                        )}
                        <span className="text-sm text-gray-600">Hi, {user?.first_name || user?.username}</span>
                        <Link to="/donor/donate" className="btn-primary text-sm py-2 px-4 flex items-center space-x-1"><Plus className="w-4 h-4" /><span>New Donation</span></Link>
                        <button onClick={logout} className="flex items-center space-x-1 text-gray-500 hover:text-gray-700 text-sm"><LogOut className="w-4 h-4" /><span>Logout</span></button>
                    </div>
                </div>
            </nav>

            <div className="max-w-6xl mx-auto px-6 py-8">
                <h1 className="text-2xl font-bold text-gray-900 mb-6">Dashboard</h1>

                {/* Metrics */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
                    {metrics.map((metric) => {
                        const Icon = metric.icon;
                        const isExpanded = expandedMetric === metric.key;
                        return (
                            <div key={metric.key}>
                                <div onClick={() => setExpandedMetric(isExpanded ? null : metric.key)}
                                    className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 cursor-pointer hover:shadow-md transition-all duration-200 group">
                                    <div className="flex items-center justify-between mb-3">
                                        <div className={`p-2 rounded-xl bg-gradient-to-r ${metric.color}`}><Icon className="w-5 h-5 text-white" /></div>
                                        <div className="text-gray-300 group-hover:text-gray-400 transition">{isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}</div>
                                    </div>
                                    <div className="text-2xl font-bold text-gray-900">{metric.value}</div>
                                    <div className="text-xs text-gray-500 mt-1">{metric.label}</div>
                                </div>
                                {isExpanded && (<div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4 mt-2 animate-fadeIn">{metric.detail}</div>)}
                            </div>
                        );
                    })}
                </div>

                {/* Donations List */}
                <div className="bg-white rounded-2xl shadow-sm border border-gray-100">
                    <div className="p-5 border-b border-gray-100"><h2 className="text-lg font-bold text-gray-900">Your Donations</h2></div>
                    {donations.length === 0 ? (
                        <div className="p-12 text-center">
                            <Package className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                            <h3 className="text-lg font-semibold text-gray-600">No Donations Yet</h3>
                            <p className="text-gray-400 mt-1 mb-4">Start making a difference today.</p>
                            <Link to="/donor/donate" className="btn-primary inline-flex items-center space-x-2"><Plus className="w-4 h-4" /><span>Create Donation</span></Link>
                        </div>
                    ) : (
                        <div className="divide-y divide-gray-100">
                            {donations.map(donation => {
                                const isEditable = ['CREATED', 'MATCHED'].includes(donation.status);
                                const unread = unreadMap[donation.id] || 0;
                                return (
                                    <div key={donation.id}
                                        onClick={() => navigate(`/donation/${donation.id}`)}
                                        className="p-5 hover:bg-gray-50 cursor-pointer transition group">
                                        <div className="flex items-center justify-between">
                                            <div className="flex-1">
                                                <div className="flex items-center space-x-2 mb-1">
                                                    <span className="font-bold text-gray-900">{donation.category}</span>
                                                    <span className="text-gray-400">·</span>
                                                    <span className="text-sm text-gray-500">{donation.quantity} items</span>
                                                    {donation.is_priority && <span className="px-2 py-0.5 bg-orange-100 text-orange-700 text-xs font-bold rounded-full">⚡ Priority</span>}
                                                    <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${STATUS_COLORS[donation.status] || ''}`}>
                                                        {donation.status?.replace(/_/g, ' ')}
                                                    </span>
                                                </div>
                                                <p className="text-sm text-gray-500">{donation.pickup_address?.substring(0, 60)}...</p>
                                                {donation.acceptor_name && <p className="text-xs text-green-600 mt-1">→ {donation.acceptor_name}</p>}
                                            </div>
                                            <div className="flex items-center space-x-2">
                                                {unread > 0 && (
                                                    <Link to={`/chat/${donation.id}`} onClick={e => e.stopPropagation()}
                                                        className="relative p-2 hover:bg-green-50 rounded-lg transition">
                                                        <MessageCircle className="w-5 h-5 text-green-600" />
                                                        <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center">{unread}</span>
                                                    </Link>
                                                )}
                                                {isEditable && (
                                                    <button onClick={(e) => handleDelete(e, donation.id)} disabled={deletingId === donation.id}
                                                        className="p-2 hover:bg-red-50 rounded-lg transition opacity-0 group-hover:opacity-100">
                                                        {deletingId === donation.id ? <Loader2 className="w-4 h-4 animate-spin text-red-400" /> : <Trash2 className="w-4 h-4 text-red-400" />}
                                                    </button>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
