import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Plus, Edit3, Trash2, Loader2, AlertCircle, Package, X } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

const CATEGORIES = [
    { value: 'CLOTHES', label: 'Clothes', icon: '👕' },
    { value: 'TOYS', label: 'Toys', icon: '🧸' },
    { value: 'BOOKS', label: 'Books', icon: '📚' },
];

const URGENCY_LEVELS = [
    { value: 'LOW', label: 'Low', color: 'bg-gray-100 text-gray-700' },
    { value: 'MEDIUM', label: 'Medium', color: 'bg-blue-100 text-blue-700' },
    { value: 'HIGH', label: 'High', color: 'bg-orange-100 text-orange-700' },
    { value: 'CRITICAL', label: 'Critical', color: 'bg-red-100 text-red-700' },
];

export default function NeedsList() {
    const { token } = useAuth();
    const navigate = useNavigate();
    const [needs, setNeeds] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showForm, setShowForm] = useState(false);
    const [editingId, setEditingId] = useState(null);
    const [formData, setFormData] = useState({ category: 'CLOTHES', quantity_needed: 1, urgency: 'MEDIUM', description: '' });
    const [saving, setSaving] = useState(false);
    const [deletingId, setDeletingId] = useState(null);
    const [error, setError] = useState('');

    const fetchNeeds = async () => {
        try {
            const data = await api.getNeeds(token);
            setNeeds(Array.isArray(data) ? data : (data?.results || []));
        } catch (err) {
            setError('Failed to load needs.');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { fetchNeeds(); }, [token]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setSaving(true);
        setError('');
        try {
            if (editingId) {
                await api.updateNeed(token, editingId, formData);
            } else {
                await api.createNeed(token, formData);
            }
            setShowForm(false);
            setEditingId(null);
            setFormData({ category: 'CLOTHES', quantity_needed: 1, urgency: 'MEDIUM', description: '' });
            await fetchNeeds();
        } catch (err) {
            setError(err.message || 'Failed to save need.');
        } finally {
            setSaving(false);
        }
    };

    const handleEdit = (need) => {
        setEditingId(need.id);
        setFormData({
            category: need.category,
            quantity_needed: need.quantity_needed,
            urgency: need.urgency,
            description: need.description || '',
        });
        setShowForm(true);
    };

    const handleDelete = async (id) => {
        if (!window.confirm('Delete this need?')) return;
        setDeletingId(id);
        try {
            await api.deleteNeed(token, id);
            await fetchNeeds();
        } catch (err) {
            setError(err.message || 'Failed to delete need.');
        } finally {
            setDeletingId(null);
        }
    };

    const cancelForm = () => {
        setShowForm(false);
        setEditingId(null);
        setFormData({ category: 'CLOTHES', quantity_needed: 1, urgency: 'MEDIUM', description: '' });
    };

    return (
        <div className="min-h-screen bg-gray-50" style={{ fontFamily: "'Inter', sans-serif" }}>
            {/* Header */}
            <div className="bg-white border-b border-gray-200 sticky top-0 z-10">
                <div className="max-w-3xl mx-auto px-6 py-4 flex items-center justify-between">
                    <button onClick={() => navigate('/acceptor/dashboard')} className="flex items-center space-x-2 text-gray-600 hover:text-gray-900 transition">
                        <ArrowLeft className="w-5 h-5" />
                        <span className="font-medium">Dashboard</span>
                    </button>
                    <h1 className="text-lg font-bold text-gray-900">Needs List</h1>
                    <button onClick={() => setShowForm(true)} className="flex items-center space-x-1 px-3 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition text-sm font-medium">
                        <Plus className="w-4 h-4" />
                        <span>Add Need</span>
                    </button>
                </div>
            </div>

            <div className="max-w-3xl mx-auto px-6 py-8">
                {error && (
                    <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl mb-6 text-sm flex items-center space-x-2">
                        <AlertCircle className="w-4 h-4" />
                        <span>{error}</span>
                    </div>
                )}

                {/* Form Modal */}
                {showForm && (
                    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 mb-6 animate-fadeIn">
                        <div className="flex items-center justify-between mb-4">
                            <h2 className="text-lg font-bold text-gray-900">{editingId ? 'Edit Need' : 'Add New Need'}</h2>
                            <button onClick={cancelForm} className="p-1 hover:bg-gray-100 rounded-lg transition">
                                <X className="w-5 h-5 text-gray-400" />
                            </button>
                        </div>
                        <form onSubmit={handleSubmit} className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">Category</label>
                                <div className="grid grid-cols-3 gap-3">
                                    {CATEGORIES.map(cat => (
                                        <button key={cat.value} type="button"
                                            onClick={() => setFormData(p => ({ ...p, category: cat.value }))}
                                            className={`p-3 rounded-xl border-2 text-center transition-all ${formData.category === cat.value
                                                ? 'border-green-600 bg-green-50' : 'border-gray-200 hover:border-gray-300'}`}
                                        >
                                            <div className="text-xl">{cat.icon}</div>
                                            <div className="text-sm font-medium mt-1">{cat.label}</div>
                                        </button>
                                    ))}
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">Quantity Needed</label>
                                    <input type="number" min="1" className="input-field"
                                        value={formData.quantity_needed}
                                        onChange={(e) => setFormData(p => ({ ...p, quantity_needed: parseInt(e.target.value) || 1 }))}
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">Urgency</label>
                                    <select className="input-field" value={formData.urgency}
                                        onChange={(e) => setFormData(p => ({ ...p, urgency: e.target.value }))}>
                                        {URGENCY_LEVELS.map(u => <option key={u.value} value={u.value}>{u.label}</option>)}
                                    </select>
                                </div>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                                <textarea className="input-field" rows="2" placeholder="Optional details..."
                                    value={formData.description}
                                    onChange={(e) => setFormData(p => ({ ...p, description: e.target.value }))}
                                />
                            </div>

                            <button type="submit" disabled={saving} className="btn-primary w-full flex items-center justify-center space-x-2">
                                {saving ? <Loader2 className="w-5 h-5 animate-spin" /> : null}
                                <span>{saving ? 'Saving...' : editingId ? 'Update Need' : 'Create Need'}</span>
                            </button>
                        </form>
                    </div>
                )}

                {/* Needs List */}
                {loading ? (
                    <div className="flex items-center justify-center py-16">
                        <Loader2 className="w-8 h-8 text-green-600 animate-spin" />
                    </div>
                ) : needs.length === 0 ? (
                    <div className="text-center py-16">
                        <Package className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                        <h3 className="text-lg font-semibold text-gray-600">No Needs Yet</h3>
                        <p className="text-gray-400 mt-1">Add your organization's current needs to receive better-matched donations.</p>
                    </div>
                ) : (
                    <div className="space-y-3">
                        {needs.map(need => {
                            const urgencyInfo = URGENCY_LEVELS.find(u => u.value === need.urgency) || URGENCY_LEVELS[1];
                            const catInfo = CATEGORIES.find(c => c.value === need.category);
                            return (
                                <div key={need.id} className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 hover:shadow-md transition-all duration-200">
                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center space-x-4">
                                            <div className="text-3xl">{catInfo?.icon || '📦'}</div>
                                            <div>
                                                <div className="flex items-center space-x-2">
                                                    <span className="font-bold text-gray-900">{catInfo?.label || need.category}</span>
                                                    <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${urgencyInfo.color}`}>
                                                        {urgencyInfo.label}
                                                    </span>
                                                </div>
                                                <p className="text-sm text-gray-500 mt-0.5">{need.quantity_needed} items needed</p>
                                                {need.description && <p className="text-sm text-gray-400 mt-1">{need.description}</p>}
                                            </div>
                                        </div>
                                        <div className="flex items-center space-x-2">
                                            <button onClick={() => handleEdit(need)} className="p-2 hover:bg-gray-100 rounded-lg transition">
                                                <Edit3 className="w-4 h-4 text-gray-400" />
                                            </button>
                                            <button onClick={() => handleDelete(need.id)} disabled={deletingId === need.id} className="p-2 hover:bg-red-50 rounded-lg transition">
                                                {deletingId === need.id ? <Loader2 className="w-4 h-4 animate-spin text-red-400" /> : <Trash2 className="w-4 h-4 text-red-400" />}
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>
        </div>
    );
}
