import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Building2, MapPin, Phone, Mail, Save, Loader2, Edit3, X, Leaf, CheckCircle, User, Shield, Truck, Package, Star, Archive } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

const STORAGE_OPTIONS = ['Small', 'Medium', 'Large'];

const VERIFICATION_BADGES = {
    VERIFIED: { label: 'Verified', color: 'bg-green-100 text-green-700 border-green-200', icon: '✅' },
    PENDING: { label: 'Pending Verification', color: 'bg-amber-100 text-amber-700 border-amber-200', icon: '⏳' },
    REJECTED: { label: 'Verification Rejected', color: 'bg-red-100 text-red-700 border-red-200', icon: '❌' },
};

export default function AcceptorProfile() {
    const { user, token, login } = useAuth();
    const navigate = useNavigate();
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [editing, setEditing] = useState(false);
    const [success, setSuccess] = useState('');
    const [error, setError] = useState('');

    const [userProfile, setUserProfile] = useState(null);
    const [acceptorProfile, setAcceptorProfile] = useState(null);

    const [form, setForm] = useState({
        first_name: '',
        last_name: '',
        email: '',
        phone_number: '',
        organization_name: '',
        contact_person: '',
        registration_id: '',
        address: '',
        pincode: '',
        storage_capacity: '',
        has_pickup_capability: false,
    });

    useEffect(() => {
        const fetchProfile = async () => {
            try {
                const [userData, accData] = await Promise.all([
                    api.getUserProfile(token),
                    api.getAcceptorProfile(token),
                ]);
                setUserProfile(userData);
                setAcceptorProfile(accData);
                setForm({
                    first_name: userData.first_name || '',
                    last_name: userData.last_name || '',
                    email: userData.email || '',
                    phone_number: userData.phone_number || '',
                    organization_name: accData.organization_name || '',
                    contact_person: accData.contact_person || '',
                    registration_id: accData.registration_id || '',
                    address: accData.address || '',
                    pincode: accData.pincode || '',
                    storage_capacity: accData.storage_capacity || '',
                    has_pickup_capability: accData.has_pickup_capability || false,
                });
            } catch (err) {
                setError('Failed to load profile.');
            } finally {
                setLoading(false);
            }
        };
        fetchProfile();
    }, [token]);

    const handleSave = async () => {
        setSaving(true);
        setError('');
        setSuccess('');
        try {
            const updatedUser = await api.updateUserProfile(token, {
                first_name: form.first_name,
                last_name: form.last_name,
                email: form.email,
                phone_number: form.phone_number || null,
            });
            const updatedAcc = await api.updateAcceptorProfile(token, {
                organization_name: form.organization_name,
                contact_person: form.contact_person,
                registration_id: form.registration_id,
                address: form.address,
                pincode: form.pincode,
                storage_capacity: form.storage_capacity,
                has_pickup_capability: form.has_pickup_capability,
            });
            setUserProfile(updatedUser);
            setAcceptorProfile(updatedAcc);
            login(updatedUser, token);
            setEditing(false);
            setSuccess('Profile updated successfully!');
            setTimeout(() => setSuccess(''), 3000);
        } catch (err) {
            setError(err.message || 'Failed to save profile.');
        } finally {
            setSaving(false);
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <Loader2 className="w-8 h-8 text-green-600 animate-spin" />
            </div>
        );
    }

    const badge = VERIFICATION_BADGES[acceptorProfile?.verification_status] || VERIFICATION_BADGES.PENDING;

    return (
        <div className="min-h-screen bg-gray-50" style={{ fontFamily: "'Inter', sans-serif" }}>
            {/* Header */}
            <nav className="bg-white/80 backdrop-blur-lg border-b border-gray-200 sticky top-0 z-20">
                <div className="max-w-3xl mx-auto px-6 py-3 flex items-center justify-between">
                    <button onClick={() => navigate('/acceptor/dashboard')} className="flex items-center space-x-2 text-gray-600 hover:text-gray-900 transition">
                        <ArrowLeft className="w-5 h-5" />
                        <span className="font-medium">Dashboard</span>
                    </button>
                    <div className="flex items-center space-x-2">
                        <div className="bg-gradient-to-r from-green-600 to-emerald-600 p-1.5 rounded-lg"><Leaf className="w-5 h-5 text-white" /></div>
                        <span className="text-xl font-bold bg-gradient-to-r from-green-700 to-emerald-600 bg-clip-text text-transparent">ReLoop</span>
                    </div>
                </div>
            </nav>

            <div className="max-w-3xl mx-auto px-6 py-8 space-y-6">
                {/* Profile Header Card */}
                <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
                    <div className="h-24 bg-gradient-to-r from-blue-500 to-indigo-600" />
                    <div className="px-6 pb-6 -mt-10">
                        <div className="flex items-end justify-between">
                            <div className="flex items-end space-x-4">
                                <div className="w-20 h-20 bg-white rounded-2xl shadow-lg flex items-center justify-center border-4 border-white">
                                    <div className="w-full h-full bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl flex items-center justify-center text-white text-2xl font-bold">
                                        {(acceptorProfile?.organization_name?.[0] || '?').toUpperCase()}
                                    </div>
                                </div>
                                <div className="pb-1">
                                    <h1 className="text-xl font-bold text-gray-900">
                                        {acceptorProfile?.organization_name}
                                    </h1>
                                    <div className="flex items-center space-x-2 mt-0.5">
                                        <p className="text-sm text-gray-500">@{userProfile?.username}</p>
                                        <span className={`px-2 py-0.5 rounded-full text-xs font-semibold border ${badge.color}`}>
                                            {badge.icon} {badge.label}
                                        </span>
                                    </div>
                                </div>
                            </div>
                            {!editing ? (
                                <button onClick={() => setEditing(true)} className="flex items-center space-x-1.5 px-4 py-2 bg-blue-50 text-blue-700 rounded-xl hover:bg-blue-100 transition text-sm font-medium">
                                    <Edit3 className="w-4 h-4" />
                                    <span>Edit Profile</span>
                                </button>
                            ) : (
                                <div className="flex items-center space-x-2">
                                    <button onClick={() => setEditing(false)} className="flex items-center space-x-1 px-3 py-2 bg-gray-100 text-gray-600 rounded-xl hover:bg-gray-200 transition text-sm font-medium">
                                        <X className="w-4 h-4" /><span>Cancel</span>
                                    </button>
                                    <button onClick={handleSave} disabled={saving} className="flex items-center space-x-1 px-4 py-2 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition text-sm font-medium disabled:opacity-50">
                                        {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                                        <span>Save</span>
                                    </button>
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                {/* Messages */}
                {success && (
                    <div className="flex items-center space-x-2 px-4 py-3 bg-green-50 border border-green-200 rounded-xl text-sm text-green-700 font-medium">
                        <CheckCircle className="w-4 h-4" /><span>{success}</span>
                    </div>
                )}
                {error && (
                    <div className="px-4 py-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700 font-medium">{error}</div>
                )}

                {/* Organization Details */}
                <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
                    <h2 className="text-lg font-bold text-gray-900 mb-5 flex items-center space-x-2">
                        <Building2 className="w-5 h-5 text-blue-600" />
                        <span>Organization Details</span>
                    </h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                        <div className="md:col-span-2">
                            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">Organization Name</label>
                            {editing ? (
                                <input type="text" value={form.organization_name} onChange={e => setForm({ ...form, organization_name: e.target.value })}
                                    className="w-full px-3 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition" />
                            ) : (
                                <p className="text-gray-900 font-medium">{acceptorProfile?.organization_name || '—'}</p>
                            )}
                        </div>
                        <div>
                            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">Contact Person</label>
                            {editing ? (
                                <input type="text" value={form.contact_person} onChange={e => setForm({ ...form, contact_person: e.target.value })}
                                    className="w-full px-3 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition" />
                            ) : (
                                <p className="text-gray-900 font-medium">{acceptorProfile?.contact_person || '—'}</p>
                            )}
                        </div>
                        <div>
                            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">Registration ID</label>
                            {editing ? (
                                <input type="text" value={form.registration_id} onChange={e => setForm({ ...form, registration_id: e.target.value })}
                                    placeholder="NGO Registration Number"
                                    className="w-full px-3 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition" />
                            ) : (
                                <div className="flex items-center space-x-2">
                                    <Shield className="w-4 h-4 text-gray-400" />
                                    <p className="text-gray-900 font-medium">{acceptorProfile?.registration_id || '—'}</p>
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                {/* Personal Info */}
                <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
                    <h2 className="text-lg font-bold text-gray-900 mb-5 flex items-center space-x-2">
                        <User className="w-5 h-5 text-green-600" />
                        <span>Account Details</span>
                    </h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                        <div>
                            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">First Name</label>
                            {editing ? (
                                <input type="text" value={form.first_name} onChange={e => setForm({ ...form, first_name: e.target.value })}
                                    className="w-full px-3 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition" />
                            ) : (
                                <p className="text-gray-900 font-medium">{userProfile?.first_name || '—'}</p>
                            )}
                        </div>
                        <div>
                            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">Last Name</label>
                            {editing ? (
                                <input type="text" value={form.last_name} onChange={e => setForm({ ...form, last_name: e.target.value })}
                                    className="w-full px-3 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition" />
                            ) : (
                                <p className="text-gray-900 font-medium">{userProfile?.last_name || '—'}</p>
                            )}
                        </div>
                        <div>
                            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">Email</label>
                            {editing ? (
                                <input type="email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })}
                                    className="w-full px-3 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition" />
                            ) : (
                                <div className="flex items-center space-x-2">
                                    <Mail className="w-4 h-4 text-gray-400" />
                                    <p className="text-gray-900 font-medium">{userProfile?.email || '—'}</p>
                                </div>
                            )}
                        </div>
                        <div>
                            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">Phone</label>
                            {editing ? (
                                <input type="tel" value={form.phone_number} onChange={e => setForm({ ...form, phone_number: e.target.value })}
                                    placeholder="+91..."
                                    className="w-full px-3 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition" />
                            ) : (
                                <div className="flex items-center space-x-2">
                                    <Phone className="w-4 h-4 text-gray-400" />
                                    <p className="text-gray-900 font-medium">{userProfile?.phone_number || '—'}</p>
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                {/* Address & Capabilities */}
                <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
                    <h2 className="text-lg font-bold text-gray-900 mb-5 flex items-center space-x-2">
                        <MapPin className="w-5 h-5 text-red-500" />
                        <span>Address & Capabilities</span>
                    </h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                        <div className="md:col-span-2">
                            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">Address</label>
                            {editing ? (
                                <textarea value={form.address} onChange={e => setForm({ ...form, address: e.target.value })} rows={2}
                                    className="w-full px-3 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition resize-none" />
                            ) : (
                                <p className="text-gray-900 font-medium">{acceptorProfile?.address || '—'}</p>
                            )}
                        </div>
                        <div>
                            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">City</label>
                            <p className="text-gray-900 font-medium">{acceptorProfile?.city || '—'}</p>
                        </div>
                        <div>
                            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">Pincode</label>
                            {editing ? (
                                <input type="text" value={form.pincode} onChange={e => setForm({ ...form, pincode: e.target.value })}
                                    className="w-full px-3 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition" />
                            ) : (
                                <p className="text-gray-900 font-medium">{acceptorProfile?.pincode || '—'}</p>
                            )}
                        </div>
                        <div>
                            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">Storage Capacity</label>
                            {editing ? (
                                <select value={form.storage_capacity} onChange={e => setForm({ ...form, storage_capacity: e.target.value })}
                                    className="w-full px-3 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition bg-white">
                                    <option value="">Select...</option>
                                    {STORAGE_OPTIONS.map(opt => <option key={opt} value={opt}>{opt}</option>)}
                                </select>
                            ) : (
                                <div className="flex items-center space-x-2">
                                    <Archive className="w-4 h-4 text-gray-400" />
                                    <p className="text-gray-900 font-medium">{acceptorProfile?.storage_capacity || '—'}</p>
                                </div>
                            )}
                        </div>
                        <div>
                            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">Pickup Capability</label>
                            {editing ? (
                                <label className="relative inline-flex items-center cursor-pointer mt-1">
                                    <input type="checkbox" checked={form.has_pickup_capability}
                                        onChange={e => setForm({ ...form, has_pickup_capability: e.target.checked })}
                                        className="sr-only peer" />
                                    <div className="w-11 h-6 bg-gray-200 peer-focus:ring-2 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:bg-blue-600 after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all" />
                                    <span className="ml-3 text-sm font-medium text-gray-700">
                                        {form.has_pickup_capability ? 'Yes' : 'No'}
                                    </span>
                                </label>
                            ) : (
                                <div className="flex items-center space-x-2">
                                    <Truck className="w-4 h-4 text-gray-400" />
                                    <p className="text-gray-900 font-medium">{acceptorProfile?.has_pickup_capability ? 'Yes' : 'No'}</p>
                                </div>
                            )}
                        </div>
                    </div>
                    {acceptorProfile?.latitude && (
                        <p className="text-xs text-gray-400 mt-3">📍 {parseFloat(acceptorProfile.latitude).toFixed(4)}, {parseFloat(acceptorProfile.longitude).toFixed(4)}</p>
                    )}
                </div>
            </div>
        </div>
    );
}
