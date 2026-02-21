import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, Package, MapPin, Calendar, Clock, Truck, MessageCircle, Edit3, Trash2, Loader2, AlertTriangle, Star, Zap, CheckCircle, Circle, ChevronRight } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

const STATUS_COLORS = {
    CREATED: 'bg-gray-100 text-gray-700',
    MATCHED: 'bg-blue-100 text-blue-700',
    ACCEPTED: 'bg-green-100 text-green-700',
    PICKUP_SCHEDULED: 'bg-indigo-100 text-indigo-700',
    IN_TRANSIT: 'bg-yellow-100 text-yellow-800',
    DELIVERED: 'bg-emerald-100 text-emerald-700',
    COMPLETED: 'bg-green-200 text-green-800',
    REJECTED: 'bg-red-100 text-red-700',
    CANCELLED: 'bg-gray-200 text-gray-600',
    WASTE_COLLECTED: 'bg-orange-100 text-orange-700',
};

// Ordered lifecycle stages for the progress tracker
const LIFECYCLE_STAGES = [
    { key: 'MATCHED', label: 'Matched' },
    { key: 'ACCEPTED', label: 'Accepted' },
    { key: 'PICKUP_SCHEDULED', label: 'Pickup Scheduled' },
    { key: 'IN_TRANSIT', label: 'In Transit' },
    { key: 'DELIVERED', label: 'Delivered' },
    { key: 'COMPLETED', label: 'Completed' },
];

const STAGE_ORDER = ['CREATED', 'MATCHED', 'ACCEPTED', 'PICKUP_SCHEDULED', 'IN_TRANSIT', 'DELIVERED', 'COMPLETED'];

export default function DonationDetail() {
    const { id } = useParams();
    const navigate = useNavigate();
    const { user, token } = useAuth();
    const [donation, setDonation] = useState(null);
    const [loading, setLoading] = useState(true);
    const [deleting, setDeleting] = useState(false);
    const [updatingStatus, setUpdatingStatus] = useState(false);
    const [error, setError] = useState('');

    const isEditable = donation && ['CREATED', 'MATCHED'].includes(donation.status);
    const isDonor = user?.role === 'DONOR';
    const isAcceptor = user?.role === 'ACCEPTOR';

    useEffect(() => {
        const fetchDonation = async () => {
            try {
                const data = await api.getDonation(token, id);
                setDonation(data);
            } catch (err) {
                setError('Donation not found or access denied.');
            } finally {
                setLoading(false);
            }
        };
        fetchDonation();
    }, [id, token]);

    const handleDelete = async () => {
        if (!window.confirm('Are you sure you want to delete this donation?')) return;
        setDeleting(true);
        try {
            await api.deleteDonation(token, id);
            navigate(isDonor ? '/donor/dashboard' : '/acceptor/dashboard');
        } catch (err) {
            setError(err.message || 'Failed to delete donation.');
            setDeleting(false);
        }
    };

    const handleStatusUpdate = async (newStatus) => {
        setUpdatingStatus(true);
        try {
            const data = await api.updateDonationStatus(token, donation.id, newStatus);
            setDonation(data);
        } catch (err) {
            setError(err.message || 'Failed to update status.');
        } finally {
            setUpdatingStatus(false);
        }
    };

    // Determine what the next action is based on current status and role
    const getNextAction = () => {
        if (!donation || ['COMPLETED', 'REJECTED', 'CANCELLED', 'WASTE_COLLECTED'].includes(donation.status)) return null;

        const statusActions = {
            ACCEPTED: isAcceptor
                ? { label: 'Schedule Pickup', status: 'PICKUP_SCHEDULED', color: 'bg-indigo-600 hover:bg-indigo-700' }
                : null,
            PICKUP_SCHEDULED: isDonor
                ? { label: 'Mark In Transit', status: 'IN_TRANSIT', color: 'bg-yellow-600 hover:bg-yellow-700' }
                : null,
            IN_TRANSIT: isAcceptor
                ? { label: 'Mark Delivered', status: 'DELIVERED', color: 'bg-emerald-600 hover:bg-emerald-700' }
                : null,
            DELIVERED: isAcceptor
                ? { label: 'Mark Completed', status: 'COMPLETED', color: 'bg-green-600 hover:bg-green-700' }
                : null,
        };

        return statusActions[donation.status] || null;
    };

    const currentStageIndex = donation ? STAGE_ORDER.indexOf(donation.status) : -1;

    if (loading) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <Loader2 className="w-8 h-8 text-green-600 animate-spin" />
            </div>
        );
    }

    if (error || !donation) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
                <div className="text-center">
                    <AlertTriangle className="w-12 h-12 text-red-400 mx-auto mb-4" />
                    <p className="text-gray-600">{error || 'Donation not found.'}</p>
                    <button onClick={() => navigate(-1)} className="mt-4 btn-primary">Go Back</button>
                </div>
            </div>
        );
    }

    const donor = donation.donor || {};
    const acceptor = donation.acceptor || null;
    const aiSuggested = donation.ai_suggested_acceptor || null;
    const nextAction = getNextAction();

    return (
        <div className="min-h-screen bg-gray-50" style={{ fontFamily: "'Inter', sans-serif" }}>
            {/* Header */}
            <div className="bg-white border-b border-gray-200 sticky top-0 z-10">
                <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
                    <button onClick={() => navigate(-1)} className="flex items-center space-x-2 text-gray-600 hover:text-gray-900 transition">
                        <ArrowLeft className="w-5 h-5" />
                        <span className="font-medium">Back</span>
                    </button>
                    <div className="flex items-center space-x-3">
                        <Link to={`/chat/${donation.id}`} className="flex items-center space-x-1 px-3 py-2 bg-green-50 text-green-700 rounded-lg hover:bg-green-100 transition text-sm font-medium">
                            <MessageCircle className="w-4 h-4" />
                            <span>Chat</span>
                        </Link>
                        {isDonor && isEditable && (
                            <>
                                <Link to={`/donor/donate?edit=${donation.id}`} className="flex items-center space-x-1 px-3 py-2 bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100 transition text-sm font-medium">
                                    <Edit3 className="w-4 h-4" />
                                    <span>Edit</span>
                                </Link>
                                <button onClick={handleDelete} disabled={deleting} className="flex items-center space-x-1 px-3 py-2 bg-red-50 text-red-700 rounded-lg hover:bg-red-100 transition text-sm font-medium">
                                    {deleting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                                    <span>Delete</span>
                                </button>
                            </>
                        )}
                    </div>
                </div>
            </div>

            {/* Content */}
            <div className="max-w-4xl mx-auto px-6 py-8 space-y-6">
                {/* Title & Status */}
                <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
                    <div className="flex items-start justify-between">
                        <div>
                            <div className="flex items-center space-x-3 mb-2">
                                <h1 className="text-2xl font-bold text-gray-900">
                                    {donation.category} Donation
                                </h1>
                                {donation.is_priority && (
                                    <span className="flex items-center space-x-1 px-2 py-0.5 bg-orange-100 text-orange-700 text-xs font-bold rounded-full">
                                        <Zap className="w-3 h-3" /> <span>Priority</span>
                                    </span>
                                )}
                            </div>
                            <p className="text-gray-500 text-sm">Donation #{donation.id} · Created {new Date(donation.created_at).toLocaleDateString()}</p>
                        </div>
                        <span className={`px-3 py-1 rounded-full text-sm font-semibold ${STATUS_COLORS[donation.status] || 'bg-gray-100 text-gray-600'}`}>
                            {donation.status?.replace(/_/g, ' ')}
                        </span>
                    </div>
                </div>

                {/* Status Progress Tracker */}
                {!['REJECTED', 'CANCELLED', 'WASTE_COLLECTED', 'CREATED'].includes(donation.status) && (
                    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
                        <h2 className="text-lg font-bold text-gray-900 mb-5">Donation Progress</h2>
                        <div className="flex items-center justify-between">
                            {LIFECYCLE_STAGES.map((stage, i) => {
                                const stageIdx = STAGE_ORDER.indexOf(stage.key);
                                const isCurrent = donation.status === stage.key;
                                const isCompleted = currentStageIndex > stageIdx;
                                const isPending = currentStageIndex < stageIdx;

                                return (
                                    <div key={stage.key} className="flex items-center flex-1 last:flex-none">
                                        <div className="flex flex-col items-center">
                                            <div className={`w-9 h-9 rounded-full flex items-center justify-center transition-all duration-300 ${isCompleted ? 'bg-green-600 text-white' :
                                                    isCurrent ? 'bg-blue-600 text-white ring-4 ring-blue-100' :
                                                        'bg-gray-200 text-gray-400'
                                                }`}>
                                                {isCompleted ? (
                                                    <CheckCircle className="w-5 h-5" />
                                                ) : (
                                                    <span className="text-xs font-bold">{i + 1}</span>
                                                )}
                                            </div>
                                            <span className={`text-xs mt-2 font-medium text-center w-20 ${isCurrent ? 'text-blue-700' : isCompleted ? 'text-green-700' : 'text-gray-400'
                                                }`}>
                                                {stage.label}
                                            </span>
                                        </div>
                                        {i < LIFECYCLE_STAGES.length - 1 && (
                                            <div className={`flex-1 h-1 mx-1 rounded-full transition-all duration-300 ${isCompleted ? 'bg-green-400' : 'bg-gray-200'
                                                }`} />
                                        )}
                                    </div>
                                );
                            })}
                        </div>

                        {/* Next Action Button */}
                        {nextAction && (
                            <div className="mt-6 pt-4 border-t border-gray-100">
                                <button
                                    onClick={() => handleStatusUpdate(nextAction.status)}
                                    disabled={updatingStatus}
                                    className={`w-full flex items-center justify-center space-x-2 px-6 py-3 text-white rounded-xl font-semibold transition-all duration-200 ${nextAction.color} disabled:opacity-50`}
                                >
                                    {updatingStatus ? (
                                        <><Loader2 className="w-5 h-5 animate-spin" /><span>Updating...</span></>
                                    ) : (
                                        <><ChevronRight className="w-5 h-5" /><span>{nextAction.label}</span></>
                                    )}
                                </button>
                            </div>
                        )}

                        {donation.status === 'COMPLETED' && (
                            <div className="mt-6 pt-4 border-t border-gray-100 text-center">
                                <div className="inline-flex items-center space-x-2 px-4 py-2 bg-green-50 text-green-700 rounded-xl">
                                    <CheckCircle className="w-5 h-5" />
                                    <span className="font-semibold">Donation Completed Successfully!</span>
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {/* Details Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Item Details */}
                    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
                        <h2 className="text-lg font-bold text-gray-900 mb-4 flex items-center space-x-2">
                            <Package className="w-5 h-5 text-green-600" />
                            <span>Item Details</span>
                        </h2>
                        <div className="space-y-3">
                            <div className="flex justify-between"><span className="text-gray-500">Category</span><span className="font-semibold">{donation.category}</span></div>
                            <div className="flex justify-between"><span className="text-gray-500">Quantity</span><span className="font-semibold">{donation.quantity} items</span></div>
                            <div className="flex justify-between"><span className="text-gray-500">Condition</span><span className="font-semibold">{donation.condition?.replace(/_/g, ' ')}</span></div>
                            {donation.description && (
                                <div>
                                    <span className="text-gray-500 text-sm">Description</span>
                                    <p className="text-gray-800 mt-1">{donation.description}</p>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Logistics */}
                    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
                        <h2 className="text-lg font-bold text-gray-900 mb-4 flex items-center space-x-2">
                            <Truck className="w-5 h-5 text-blue-600" />
                            <span>Logistics</span>
                        </h2>
                        <div className="space-y-3">
                            <div className="flex justify-between"><span className="text-gray-500">Delivery Method</span><span className="font-semibold">{donation.delivery_method?.replace(/_/g, ' ') || 'Not set'}</span></div>
                            {donation.logistics_provider_choice && (
                                <div className="flex justify-between"><span className="text-gray-500">Provider</span><span className="font-semibold">{donation.logistics_provider_choice}</span></div>
                            )}
                            {donation.suggested_pickup_time && (
                                <div className="flex justify-between"><span className="text-gray-500">Pickup Time</span><span className="font-semibold">{new Date(donation.suggested_pickup_time).toLocaleString()}</span></div>
                            )}
                        </div>
                    </div>

                    {/* Location */}
                    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
                        <h2 className="text-lg font-bold text-gray-900 mb-4 flex items-center space-x-2">
                            <MapPin className="w-5 h-5 text-red-500" />
                            <span>Location</span>
                        </h2>
                        <p className="text-gray-700">{donation.pickup_address}</p>
                        {donation.pickup_latitude && (
                            <p className="text-xs text-gray-400 mt-2">
                                📍 {parseFloat(donation.pickup_latitude).toFixed(4)}, {parseFloat(donation.pickup_longitude).toFixed(4)}
                            </p>
                        )}
                    </div>

                    {/* Schedule */}
                    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
                        <h2 className="text-lg font-bold text-gray-900 mb-4 flex items-center space-x-2">
                            <Calendar className="w-5 h-5 text-purple-600" />
                            <span>Schedule</span>
                        </h2>
                        <div className="space-y-3">
                            {donation.donation_deadline && (
                                <div className="flex justify-between">
                                    <span className="text-gray-500">Deadline</span>
                                    <span className="font-semibold">{new Date(donation.donation_deadline).toLocaleDateString()}</span>
                                </div>
                            )}
                            {donation.preferred_pickup_start && (
                                <div className="flex justify-between">
                                    <span className="text-gray-500">Preferred Window</span>
                                    <span className="font-semibold text-sm">
                                        {new Date(donation.preferred_pickup_start).toLocaleString()} — {new Date(donation.preferred_pickup_end).toLocaleString()}
                                    </span>
                                </div>
                            )}
                            {!donation.donation_deadline && !donation.preferred_pickup_start && (
                                <p className="text-gray-400 text-sm">No schedule set</p>
                            )}
                        </div>
                    </div>
                </div>

                {/* NGO Info */}
                {(acceptor || aiSuggested) && (
                    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
                        <h2 className="text-lg font-bold text-gray-900 mb-4 flex items-center space-x-2">
                            <Star className="w-5 h-5 text-yellow-500" />
                            <span>NGO Assignment</span>
                        </h2>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {acceptor && (
                                <div className="p-4 bg-green-50 rounded-xl border border-green-200">
                                    <div className="text-xs font-semibold text-green-600 mb-1">Selected NGO</div>
                                    <div className="font-bold text-gray-900">{acceptor.acceptor_profile?.organization_name || acceptor.username}</div>
                                    <div className="text-sm text-gray-500">{acceptor.email}</div>
                                </div>
                            )}
                            {aiSuggested && (
                                <div className="p-4 bg-blue-50 rounded-xl border border-blue-200">
                                    <div className="text-xs font-semibold text-blue-600 mb-1">AI Suggested</div>
                                    <div className="font-bold text-gray-900">{aiSuggested.acceptor_profile?.organization_name || aiSuggested.username}</div>
                                    {donation.matching_score && <div className="text-sm text-blue-600 font-semibold">{donation.matching_score}% match</div>}
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {/* Images */}
                {donation.images && donation.images.length > 0 && (
                    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
                        <h2 className="text-lg font-bold text-gray-900 mb-4">Photos</h2>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                            {donation.images.map((img, i) => (
                                <img key={i} src={img.image} alt={`Donation ${i + 1}`}
                                    className="w-full h-32 object-cover rounded-xl border border-gray-200" />
                            ))}
                        </div>
                    </div>
                )}

                {/* Donor Info */}
                <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
                    <h2 className="text-lg font-bold text-gray-900 mb-3">Donor</h2>
                    <div className="flex items-center space-x-3">
                        <div className="w-10 h-10 bg-gradient-to-r from-green-500 to-emerald-600 rounded-full flex items-center justify-center text-white font-bold">
                            {(donor.username || '?')[0].toUpperCase()}
                        </div>
                        <div>
                            <div className="font-semibold text-gray-900">{donor.first_name} {donor.last_name}</div>
                            <div className="text-sm text-gray-500">@{donor.username}</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

