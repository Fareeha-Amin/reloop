import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, User, MapPin, Phone, Mail, Wallet, Award, Package, Save, Loader2, Edit3, X, Leaf, CheckCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

export default function DonorProfile() {
    const { user, token, login } = useAuth();
    const navigate = useNavigate();
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [editing, setEditing] = useState(false);
    const [success, setSuccess] = useState('');
    const [error, setError] = useState('');

    const [userProfile, setUserProfile] = useState(null);
    const [donorProfile, setDonorProfile] = useState(null);

    // Editable fields
    const [form, setForm] = useState({
        first_name: '',
        last_name: '',
        email: '',
        phone_number: '',
        address: '',
        pincode: '',
    });

    useEffect(() => {
        const fetchProfile = async () => {
            try {
                const [userData, donorData] = await Promise.all([
                    api.getUserProfile(token),
                    api.getDonorProfile(token),
                ]);
                setUserProfile(userData);
                setDonorProfile(donorData);
                setForm({
                    first_name: userData.first_name || '',
                    last_name: userData.last_name || '',
                    email: userData.email || '',
                    phone_number: userData.phone_number || '',
                    address: donorData.address || '',
                    pincode: donorData.pincode || '',
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
            // Update user fields
            const updatedUser = await api.updateUserProfile(token, {
                first_name: form.first_name,
                last_name: form.last_name,
                email: form.email,
                phone_number: form.phone_number || null,
            });
            // Update donor profile fields
            const updatedDonor = await api.updateDonorProfile(token, {
                address: form.address,
                pincode: form.pincode,
            });
            setUserProfile(updatedUser);
            setDonorProfile(updatedDonor);
            // Sync auth context with updated user data
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

    return (
        <div className="min-h-screen bg-gray-50" style={{ fontFamily: "'Inter', sans-serif" }}>
            {/* Header */}
            <nav className="bg-white/80 backdrop-blur-lg border-b border-gray-200 sticky top-0 z-20">
                <div className="max-w-3xl mx-auto px-6 py-3 flex items-center justify-between">
                    <button onClick={() => navigate('/donor/dashboard')} className="flex items-center space-x-2 text-gray-600 hover:text-gray-900 transition">
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
                    <div className="h-24 bg-gradient-to-r from-green-500 to-emerald-600" />
                    <div className="px-6 pb-6 -mt-10">
                        <div className="flex items-end justify-between">
                            <div className="flex items-end space-x-4">
                                <div className="w-20 h-20 bg-white rounded-2xl shadow-lg flex items-center justify-center border-4 border-white">
                                    <div className="w-full h-full bg-gradient-to-br from-green-500 to-emerald-600 rounded-xl flex items-center justify-center text-white text-2xl font-bold">
                                        {(userProfile?.first_name?.[0] || userProfile?.username?.[0] || '?').toUpperCase()}
                                    </div>
                                </div>
                                <div className="pb-1">
                                    <h1 className="text-xl font-bold text-gray-900">
                                        {userProfile?.first_name} {userProfile?.last_name}
                                    </h1>
                                    <p className="text-sm text-gray-500">@{userProfile?.username} · Donor</p>
                                </div>
                            </div>
                            {!editing ? (
                                <button onClick={() => setEditing(true)} className="flex items-center space-x-1.5 px-4 py-2 bg-green-50 text-green-700 rounded-xl hover:bg-green-100 transition text-sm font-medium">
                                    <Edit3 className="w-4 h-4" />
                                    <span>Edit Profile</span>
                                </button>
                            ) : (
                                <div className="flex items-center space-x-2">
                                    <button onClick={() => setEditing(false)} className="flex items-center space-x-1 px-3 py-2 bg-gray-100 text-gray-600 rounded-xl hover:bg-gray-200 transition text-sm font-medium">
                                        <X className="w-4 h-4" /><span>Cancel</span>
                                    </button>
                                    <button onClick={handleSave} disabled={saving} className="flex items-center space-x-1 px-4 py-2 bg-green-600 text-white rounded-xl hover:bg-green-700 transition text-sm font-medium disabled:opacity-50">
                                        {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                                        <span>Save</span>
                                    </button>
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                {/* Success / Error Messages */}
                {success && (
                    <div className="flex items-center space-x-2 px-4 py-3 bg-green-50 border border-green-200 rounded-xl text-sm text-green-700 font-medium">
                        <CheckCircle className="w-4 h-4" /><span>{success}</span>
                    </div>
                )}
                {error && (
                    <div className="px-4 py-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700 font-medium">{error}</div>
                )}

                {/* Profile Details / Edit Form */}
                <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
                    <h2 className="text-lg font-bold text-gray-900 mb-5 flex items-center space-x-2">
                        <User className="w-5 h-5 text-green-600" />
                        <span>Personal Information</span>
                    </h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                        <div>
                            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">First Name</label>
                            {editing ? (
                                <input type="text" value={form.first_name} onChange={e => setForm({ ...form, first_name: e.target.value })}
                                    className="w-full px-3 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-green-500 focus:border-green-500 outline-none transition" />
                            ) : (
                                <p className="text-gray-900 font-medium">{userProfile?.first_name || '—'}</p>
                            )}
                        </div>
                        <div>
                            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">Last Name</label>
                            {editing ? (
                                <input type="text" value={form.last_name} onChange={e => setForm({ ...form, last_name: e.target.value })}
                                    className="w-full px-3 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-green-500 focus:border-green-500 outline-none transition" />
                            ) : (
                                <p className="text-gray-900 font-medium">{userProfile?.last_name || '—'}</p>
                            )}
                        </div>
                        <div>
                            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">Email</label>
                            {editing ? (
                                <input type="email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })}
                                    className="w-full px-3 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-green-500 focus:border-green-500 outline-none transition" />
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
                                    className="w-full px-3 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-green-500 focus:border-green-500 outline-none transition" />
                            ) : (
                                <div className="flex items-center space-x-2">
                                    <Phone className="w-4 h-4 text-gray-400" />
                                    <p className="text-gray-900 font-medium">{userProfile?.phone_number || '—'}</p>
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                {/* Address Section */}
                <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
                    <h2 className="text-lg font-bold text-gray-900 mb-5 flex items-center space-x-2">
                        <MapPin className="w-5 h-5 text-red-500" />
                        <span>Address</span>
                    </h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                        <div className="md:col-span-2">
                            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">Address</label>
                            {editing ? (
                                <textarea value={form.address} onChange={e => setForm({ ...form, address: e.target.value })} rows={2}
                                    className="w-full px-3 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-green-500 focus:border-green-500 outline-none transition resize-none" />
                            ) : (
                                <p className="text-gray-900 font-medium">{donorProfile?.address || '—'}</p>
                            )}
                        </div>
                        <div>
                            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">City</label>
                            <p className="text-gray-900 font-medium">{donorProfile?.city || '—'}</p>
                        </div>
                        <div>
                            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">Pincode</label>
                            {editing ? (
                                <input type="text" value={form.pincode} onChange={e => setForm({ ...form, pincode: e.target.value })}
                                    className="w-full px-3 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-green-500 focus:border-green-500 outline-none transition" />
                            ) : (
                                <p className="text-gray-900 font-medium">{donorProfile?.pincode || '—'}</p>
                            )}
                        </div>
                    </div>
                    {donorProfile?.latitude && (
                        <p className="text-xs text-gray-400 mt-3">📍 {parseFloat(donorProfile.latitude).toFixed(4)}, {parseFloat(donorProfile.longitude).toFixed(4)}</p>
                    )}
                </div>
            </div>
        </div>
    );
}
