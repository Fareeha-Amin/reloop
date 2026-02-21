import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { Leaf, Loader2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

export default function Register() {
    const [searchParams] = useSearchParams();
    const defaultRole = searchParams.get('role')?.toUpperCase() || 'DONOR';

    const [formData, setFormData] = useState({
        username: '',
        email: '',
        password: '',
        password_confirm: '',
        first_name: '',
        last_name: '',
        phone_number: '',
        role: defaultRole === 'ACCEPTOR' ? 'ACCEPTOR' : 'DONOR',
        address: '',
        // Acceptor fields
        organization_name: '',
        contact_person: '',
    });
    const [errors, setErrors] = useState({});
    const [generalError, setGeneralError] = useState('');
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();
    const { login } = useAuth();

    const handleChange = (field, value) => {
        setFormData(prev => ({ ...prev, [field]: value }));
        // Clear field error on change
        if (errors[field]) {
            setErrors(prev => {
                const next = { ...prev };
                delete next[field];
                return next;
            });
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setErrors({});
        setGeneralError('');
        setLoading(true);

        try {
            const response = await api.register(formData);
            if (response.user && response.tokens) {
                login(response.user, response.tokens.access);
                if (response.user.role === 'ADMIN') {
                    window.location.href = '/admin/';
                } else {
                    navigate(response.user.role === 'DONOR' ? '/donor/dashboard' : '/acceptor/dashboard');
                }
            } else {
                setGeneralError('Unexpected response from server.');
            }
        } catch (err) {
            console.error('Registration error:', err);
            // Parse field-level errors from server
            if (err.fieldErrors) {
                setErrors(err.fieldErrors);
                // Build a readable summary of field errors for the banner
                const messages = Object.entries(err.fieldErrors).map(([field, msgs]) => {
                    const msg = Array.isArray(msgs) ? msgs[0] : msgs;
                    return `${field}: ${msg}`;
                });
                setGeneralError(messages.join(' | ') || err.message || 'Validation failed.');
            } else {
                setGeneralError(err.message || 'Registration failed. Please try again.');
            }
        } finally {
            setLoading(false);
        }
    };

    const fieldError = (field) => {
        if (!errors[field]) return null;
        const msg = Array.isArray(errors[field]) ? errors[field][0] : errors[field];
        return <p className="text-red-500 text-xs mt-1">{msg}</p>;
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-green-50 via-emerald-50 to-teal-50 flex items-center justify-center p-6"
            style={{ fontFamily: "'Inter', sans-serif" }}>
            <div className="max-w-2xl w-full bg-white rounded-2xl shadow-xl p-8 animate-fadeIn">
                <div className="text-center mb-8">
                    <div className="flex items-center justify-center space-x-2 mb-3">
                        <div className="bg-gradient-to-r from-green-600 to-emerald-600 p-2 rounded-xl">
                            <Leaf className="w-7 h-7 text-white" />
                        </div>
                        <span className="text-2xl font-bold bg-gradient-to-r from-green-700 to-emerald-600 bg-clip-text text-transparent">ReLoop</span>
                    </div>
                    <h2 className="text-3xl font-bold text-gray-900">Create Account</h2>
                    <p className="text-gray-500 mt-2">Join the circular economy movement</p>
                </div>

                {generalError && (
                    <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl mb-6 text-sm">
                        {generalError}
                    </div>
                )}

                <form onSubmit={handleSubmit} className="space-y-5">
                    {/* Role Selection */}
                    <div>
                        <label className="block text-sm font-semibold text-gray-700 mb-2">I am a</label>
                        <div className="grid grid-cols-2 gap-4">
                            <button
                                type="button"
                                onClick={() => handleChange('role', 'DONOR')}
                                className={`p-4 rounded-xl border-2 transition-all duration-200 ${formData.role === 'DONOR'
                                    ? 'border-green-600 bg-green-50 shadow-sm'
                                    : 'border-gray-200 hover:border-gray-300'
                                    }`}
                            >
                                <div className="font-semibold text-gray-900">🤝 Donor</div>
                                <div className="text-xs text-gray-500 mt-1">Individual donating items</div>
                            </button>
                            <button
                                type="button"
                                onClick={() => handleChange('role', 'ACCEPTOR')}
                                className={`p-4 rounded-xl border-2 transition-all duration-200 ${formData.role === 'ACCEPTOR'
                                    ? 'border-green-600 bg-green-50 shadow-sm'
                                    : 'border-gray-200 hover:border-gray-300'
                                    }`}
                            >
                                <div className="font-semibold text-gray-900">🏢 NGO/Institution</div>
                                <div className="text-xs text-gray-500 mt-1">Accepting donations</div>
                            </button>
                        </div>
                    </div>

                    {/* Name Fields */}
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-xs font-medium text-gray-600 mb-1">First Name</label>
                            <input
                                type="text"
                                placeholder="John"
                                className="input-field"
                                value={formData.first_name}
                                onChange={(e) => handleChange('first_name', e.target.value)}
                                required
                            />
                            {fieldError('first_name')}
                        </div>
                        <div>
                            <label className="block text-xs font-medium text-gray-600 mb-1">Last Name</label>
                            <input
                                type="text"
                                placeholder="Doe"
                                className="input-field"
                                value={formData.last_name}
                                onChange={(e) => handleChange('last_name', e.target.value)}
                                required
                            />
                            {fieldError('last_name')}
                        </div>
                    </div>

                    <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">Username</label>
                        <input
                            type="text"
                            placeholder="johndoe"
                            className="input-field"
                            value={formData.username}
                            onChange={(e) => handleChange('username', e.target.value)}
                            required
                        />
                        {fieldError('username')}
                    </div>

                    <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">Email</label>
                        <input
                            type="email"
                            placeholder="john@example.com"
                            className="input-field"
                            value={formData.email}
                            onChange={(e) => handleChange('email', e.target.value)}
                            required
                        />
                        {fieldError('email')}
                    </div>

                    <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">Phone Number</label>
                        <input
                            type="tel"
                            placeholder="+91XXXXXXXXXX"
                            className="input-field"
                            value={formData.phone_number}
                            onChange={(e) => handleChange('phone_number', e.target.value)}
                        />
                        {fieldError('phone_number')}
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-xs font-medium text-gray-600 mb-1">Password</label>
                            <input
                                type="password"
                                placeholder="Min 8 characters"
                                className="input-field"
                                value={formData.password}
                                onChange={(e) => handleChange('password', e.target.value)}
                                required
                            />
                            {fieldError('password')}
                        </div>
                        <div>
                            <label className="block text-xs font-medium text-gray-600 mb-1">Confirm Password</label>
                            <input
                                type="password"
                                placeholder="Repeat password"
                                className="input-field"
                                value={formData.password_confirm}
                                onChange={(e) => handleChange('password_confirm', e.target.value)}
                                required
                            />
                            {fieldError('password_confirm')}
                        </div>
                    </div>

                    <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">Address</label>
                        <textarea
                            placeholder="Full address for location-based matching"
                            className="input-field"
                            rows="2"
                            value={formData.address}
                            onChange={(e) => handleChange('address', e.target.value)}
                            required
                        />
                        {fieldError('address')}
                    </div>

                    {/* Acceptor-specific fields */}
                    {formData.role === 'ACCEPTOR' && (
                        <div className="space-y-4 p-4 bg-emerald-50 rounded-xl border border-emerald-200">
                            <h3 className="text-sm font-semibold text-emerald-800">Organization Details</h3>
                            <div>
                                <label className="block text-xs font-medium text-gray-600 mb-1">Organization Name</label>
                                <input
                                    type="text"
                                    placeholder="e.g., Helping Hands Foundation"
                                    className="input-field"
                                    value={formData.organization_name}
                                    onChange={(e) => handleChange('organization_name', e.target.value)}
                                    required
                                />
                                {fieldError('organization_name')}
                            </div>
                            <div>
                                <label className="block text-xs font-medium text-gray-600 mb-1">Contact Person</label>
                                <input
                                    type="text"
                                    placeholder="Primary contact name"
                                    className="input-field"
                                    value={formData.contact_person}
                                    onChange={(e) => handleChange('contact_person', e.target.value)}
                                    required
                                />
                                {fieldError('contact_person')}
                            </div>
                        </div>
                    )}

                    <button
                        type="submit"
                        disabled={loading}
                        className="btn-primary w-full flex items-center justify-center space-x-2"
                    >
                        {loading ? (
                            <>
                                <Loader2 className="w-5 h-5 animate-spin" />
                                <span>Creating Account...</span>
                            </>
                        ) : (
                            <span>Create Account</span>
                        )}
                    </button>
                </form>

                <p className="text-center mt-6 text-gray-500 text-sm">
                    Already have an account?{' '}
                    <Link to="/login" className="text-green-600 hover:text-green-700 font-semibold">
                        Login
                    </Link>
                </p>
            </div>
        </div>
    );
}
