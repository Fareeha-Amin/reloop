import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Package, Leaf, LogOut, Loader2, MessageCircle, Check, X, ChevronDown, ChevronUp, Inbox, CheckCircle, ListChecks, BarChart3, Truck, UserCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

const STATUS_COLORS = {
    CREATED: 'bg-gray-100 text-gray-700', MATCHED: 'bg-blue-100 text-blue-700', ACCEPTED: 'bg-green-100 text-green-700',
    PICKUP_SCHEDULED: 'bg-indigo-100 text-indigo-700', IN_TRANSIT: 'bg-yellow-100 text-yellow-800',
    DELIVERED: 'bg-emerald-100 text-emerald-700', COMPLETED: 'bg-green-200 text-green-800',
    REJECTED: 'bg-red-100 text-red-700', CANCELLED: 'bg-gray-200 text-gray-600',
    RE_MATCHING: 'bg-amber-100 text-amber-700', ESCALATED: 'bg-orange-100 text-orange-700',
    WASTE_REDIRECTED: 'bg-purple-100 text-purple-700', WASTE_COLLECTED: 'bg-purple-200 text-purple-800',
};

export default function AcceptorDashboard() {
    const { user, token, logout } = useAuth();
    const navigate = useNavigate();
    const [donations, setDonations] = useState([]);
    const [loading, setLoading] = useState(true);
    const [acceptingId, setAcceptingId] = useState(null);
    const [rejectingId, setRejectingId] = useState(null);
    const [unreadMap, setUnreadMap] = useState({});
    const [expandedMetric, setExpandedMetric] = useState(null);
    const [offersPickup, setOffersPickup] = useState(false);
    const [togglingPickup, setTogglingPickup] = useState(false);

    const fetchData = async () => {
        try {
            const [donData, unreadData] = await Promise.all([
                api.getDonations(token),
                api.getPerDonationUnread(token).catch(() => ({})),
            ]);
            setDonations(Array.isArray(donData) ? donData : (donData?.results || []));
            setUnreadMap(unreadData || {});
        } catch (err) {
            console.error('Dashboard error:', err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
        // Fetch pickup capability
        api.getAcceptorProfile(token).then(profile => {
            setOffersPickup(profile.has_pickup_capability || false);
        }).catch(() => { });
        const interval = setInterval(async () => {
            try { setUnreadMap(await api.getPerDonationUnread(token).catch(() => ({}))); } catch { }
        }, 15000);
        return () => clearInterval(interval);
    }, [token]);

    const handleTogglePickup = async () => {
        setTogglingPickup(true);
        try {
            const updated = await api.updateAcceptorProfile(token, { has_pickup_capability: !offersPickup });
            setOffersPickup(updated.has_pickup_capability);
        } catch (err) {
            console.error('Failed to toggle pickup:', err);
        } finally {
            setTogglingPickup(false);
        }
    };

    const handleAccept = async (e, id) => {
        e.stopPropagation();
        setAcceptingId(id);
        try {
            await api.acceptDonation(token, id);
            await fetchData();
        } catch (err) {
            alert(err.message || 'Failed to accept.');
        } finally {
            setAcceptingId(null);
        }
    };

    const handleReject = async (e, id) => {
        e.stopPropagation();
        if (!window.confirm('Reject this donation?')) return;
        setRejectingId(id);
        try {
            await api.rejectDonation(token, id);
            await fetchData();
        } catch (err) {
            alert(err.message || 'Failed to reject.');
        } finally {
            setRejectingId(null);
        }
    };

    const pendingDonations = donations.filter(d => d.status === 'CREATED' || d.status === 'MATCHED');
    const acceptedDonations = donations.filter(d => ['ACCEPTED', 'PICKUP_SCHEDULED', 'IN_TRANSIT', 'DELIVERED', 'COMPLETED'].includes(d.status));

    // Metrics
    const totalReceived = acceptedDonations.length;
    const activeRequests = pendingDonations.length;
    const completedCount = donations.filter(d => d.status === 'COMPLETED').length;
    const catStats = {};
    acceptedDonations.forEach(d => { catStats[d.category] = (catStats[d.category] || 0) + 1; });
    const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const monthlyData = monthNames.map((label, i) => ({
        label,
        value: acceptedDonations.filter(d => new Date(d.created_at).getMonth() === i).length,
    }));
    const totalItems = acceptedDonations.reduce((sum, d) => sum + d.quantity, 0);
    const impactKg = acceptedDonations.reduce((sum, d) => {
        const w = { CLOTHES: 0.5, TOYS: 0.3, BOOKS: 0.8 };
        return sum + d.quantity * (w[d.category] || 0.5);
    }, 0);

    const metrics = [
        {
            key: 'received', label: 'Donations Received', value: totalReceived, icon: CheckCircle, color: 'from-green-500 to-emerald-600',
            detail: (<div className="space-y-2">{Object.entries(catStats).map(([cat, count]) => (
                <div key={cat} className="flex justify-between text-sm"><span className="text-gray-600">{cat}</span><span className="font-semibold">{count}</span></div>
            ))}{Object.keys(catStats).length === 0 && <p className="text-sm text-gray-400">No donations yet</p>}</div>)
        },
        {
            key: 'active', label: 'Active Requests', value: activeRequests, icon: Inbox, color: 'from-blue-500 to-blue-600',
            detail: (<div className="space-y-2">{pendingDonations.slice(0, 3).map(d => (
                <div key={d.id} className="flex justify-between text-sm"><span className="text-gray-600">{d.category}</span><span className="font-semibold">{d.quantity} items</span></div>
            ))}</div>)
        },
        {
            key: 'items', label: 'Total Items Received', value: totalItems, icon: Package, color: 'from-purple-500 to-indigo-600',
            detail: (<div className="flex items-end space-x-1 h-16">{monthlyData.map((d, i) => {
                const max = Math.max(...monthlyData.map(m => m.value), 1);
                return (<div key={i} className="flex-1 flex flex-col items-center">
                    <div className="w-full rounded-t-sm bg-purple-500" style={{ height: `${(d.value / max) * 100}%`, minHeight: '2px' }} />
                    <span className="text-[9px] text-gray-400 mt-1">{d.label}</span>
                </div>);
            })}</div>)
        },
        {
            key: 'impact', label: 'Impact Generated', value: `${impactKg.toFixed(1)} kg`, icon: BarChart3, color: 'from-teal-500 to-cyan-600',
            detail: (<div className="text-sm text-gray-600"><p>≈ {(impactKg * 2.5 / 21.7).toFixed(1)} trees equivalent saved</p><p className="mt-1">{completedCount} donations completed</p></div>)
        },
    ];

    if (loading) {
        return (<div className="min-h-screen bg-gray-50 flex items-center justify-center"><Loader2 className="w-8 h-8 text-green-600 animate-spin" /></div>);
    }

    const DonationCard = ({ donation, showActions }) => {
        const unread = unreadMap[donation.id] || 0;
        return (
            <div onClick={() => navigate(`/donation/${donation.id}`)}
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
                        <p className="text-xs text-gray-400 mt-1">by {donation.donor_name}</p>
                    </div>
                    <div className="flex items-center space-x-2">
                        {unread > 0 && (
                            <Link to={`/chat/${donation.id}`} onClick={e => e.stopPropagation()} className="relative p-2 hover:bg-green-50 rounded-lg transition">
                                <MessageCircle className="w-5 h-5 text-green-600" />
                                <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center">{unread}</span>
                            </Link>
                        )}
                        {showActions && (
                            <>
                                <button onClick={(e) => handleAccept(e, donation.id)} disabled={acceptingId === donation.id}
                                    className="px-3 py-1.5 bg-green-600 text-white rounded-lg text-sm font-semibold hover:bg-green-700 transition flex items-center space-x-1">
                                    {acceptingId === donation.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                                    <span>Accept</span>
                                </button>
                                <button onClick={(e) => handleReject(e, donation.id)} disabled={rejectingId === donation.id}
                                    className="px-3 py-1.5 bg-red-50 text-red-600 rounded-lg text-sm font-semibold hover:bg-red-100 transition flex items-center space-x-1">
                                    {rejectingId === donation.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <X className="w-4 h-4" />}
                                    <span>Reject</span>
                                </button>
                            </>
                        )}
                    </div>
                </div>
            </div>
        );
    };

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
                        <span className="text-sm text-gray-600">{user?.acceptor_profile?.organization_name || user?.username}</span>
                        <Link to="/acceptor/profile" className="flex items-center space-x-1 px-3 py-2 bg-gray-50 text-gray-700 rounded-lg hover:bg-gray-100 transition text-sm font-medium">
                            <UserCircle className="w-4 h-4" /><span>Profile</span>
                        </Link>
                        <Link to="/acceptor/needs" className="flex items-center space-x-1 px-3 py-2 bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100 transition text-sm font-medium">
                            <ListChecks className="w-4 h-4" /><span>Needs List</span>
                        </Link>
                        <button onClick={logout} className="flex items-center space-x-1 text-gray-500 hover:text-gray-700 text-sm"><LogOut className="w-4 h-4" /><span>Logout</span></button>
                    </div>
                </div>
            </nav>

            <div className="max-w-6xl mx-auto px-6 py-8">
                <h1 className="text-2xl font-bold text-gray-900 mb-6">NGO Dashboard</h1>

                {/* Pickup Capability Toggle */}
                <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 mb-6 flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                        <div className="p-2 rounded-xl bg-gradient-to-r from-indigo-500 to-purple-600">
                            <Truck className="w-5 h-5 text-white" />
                        </div>
                        <div>
                            <div className="font-semibold text-gray-900">Pickup Service</div>
                            <div className="text-xs text-gray-500">Allow donors to request pickup from your organization</div>
                        </div>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                        <input
                            type="checkbox"
                            checked={offersPickup}
                            onChange={handleTogglePickup}
                            disabled={togglingPickup}
                            className="sr-only peer"
                        />
                        <div className={`w-11 h-6 bg-gray-200 peer-focus:ring-2 peer-focus:ring-indigo-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:bg-indigo-600 after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all ${togglingPickup ? 'opacity-50' : ''}`}></div>
                        <span className={`ml-3 text-sm font-medium ${offersPickup ? 'text-indigo-700' : 'text-gray-400'}`}>
                            {offersPickup ? 'Active' : 'Inactive'}
                        </span>
                    </label>
                </div>

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

                {/* Pending Donations */}
                <div className="bg-white rounded-2xl shadow-sm border border-gray-100 mb-6">
                    <div className="p-5 border-b border-gray-100 flex items-center justify-between">
                        <h2 className="text-lg font-bold text-gray-900">Pending Requests</h2>
                        <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs font-bold rounded-full">{pendingDonations.length}</span>
                    </div>
                    {pendingDonations.length === 0 ? (
                        <div className="p-8 text-center text-gray-400"><Inbox className="w-8 h-8 mx-auto mb-2 opacity-50" /><p>No pending requests</p></div>
                    ) : (
                        <div className="divide-y divide-gray-100">
                            {pendingDonations.map(d => <DonationCard key={d.id} donation={d} showActions={true} />)}
                        </div>
                    )}
                </div>

                {/* Accepted Donations */}
                <div className="bg-white rounded-2xl shadow-sm border border-gray-100">
                    <div className="p-5 border-b border-gray-100 flex items-center justify-between">
                        <h2 className="text-lg font-bold text-gray-900">Accepted Donations</h2>
                        <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs font-bold rounded-full">{acceptedDonations.length}</span>
                    </div>
                    {acceptedDonations.length === 0 ? (
                        <div className="p-8 text-center text-gray-400"><CheckCircle className="w-8 h-8 mx-auto mb-2 opacity-50" /><p>No accepted donations yet</p></div>
                    ) : (
                        <div className="divide-y divide-gray-100">
                            {acceptedDonations.map(d => <DonationCard key={d.id} donation={d} showActions={false} />)}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

