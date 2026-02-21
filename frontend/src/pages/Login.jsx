import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Leaf, Loader2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

export default function Login() {
    const [formData, setFormData] = useState({ username: '', password: '' });
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();
    const { login } = useAuth();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            const response = await api.login(formData);

            if (response.user && response.tokens) {
                login(response.user, response.tokens.access);

                // Role-based redirect
                const role = response.user.role;
                if (role === 'ADMIN') {
                    window.location.href = '/admin/';
                } else if (role === 'ACCEPTOR') {
                    navigate('/acceptor/dashboard');
                } else {
                    navigate('/donor/dashboard');
                }
            } else {
                setError('Invalid response from server.');
            }
        } catch (err) {
            console.error('Login error:', err);
            setError(err.message || 'Login failed. Please check your credentials.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-green-50 via-emerald-50 to-teal-50 flex items-center justify-center p-6"
            style={{ fontFamily: "'Inter', sans-serif" }}>
            <div className="max-w-md w-full bg-white rounded-2xl shadow-xl p-8 animate-fadeIn">
                <div className="text-center mb-8">
                    <div className="flex items-center justify-center space-x-2 mb-3">
                        <div className="bg-gradient-to-r from-green-600 to-emerald-600 p-2 rounded-xl">
                            <Leaf className="w-7 h-7 text-white" />
                        </div>
                        <span className="text-2xl font-bold bg-gradient-to-r from-green-700 to-emerald-600 bg-clip-text text-transparent">ReLoop</span>
                    </div>
                    <h2 className="text-3xl font-bold text-gray-900">Welcome Back</h2>
                    <p className="text-gray-500 mt-2">Sign in to your account</p>
                </div>

                {error && (
                    <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl mb-6 text-sm animate-shake">
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit} className="space-y-5">
                    <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">Username</label>
                        <input
                            type="text"
                            placeholder="Enter your username"
                            className="input-field"
                            value={formData.username}
                            onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                            required
                        />
                    </div>

                    <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">Password</label>
                        <input
                            type="password"
                            placeholder="Enter your password"
                            className="input-field"
                            value={formData.password}
                            onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                            required
                        />
                    </div>

                    <button
                        type="submit"
                        disabled={loading}
                        className="btn-primary w-full flex items-center justify-center space-x-2"
                    >
                        {loading ? (
                            <>
                                <Loader2 className="w-5 h-5 animate-spin" />
                                <span>Signing in...</span>
                            </>
                        ) : (
                            <span>Sign In</span>
                        )}
                    </button>
                </form>

                {/* Demo Credentials */}
                <div className="mt-6 p-4 bg-gray-50 rounded-xl border border-gray-200">
                    <p className="text-xs font-semibold text-gray-500 mb-2">Demo Accounts</p>
                    <div className="grid grid-cols-2 gap-3 text-xs">
                        <div className="bg-white p-2 rounded-lg border">
                            <span className="font-medium text-green-700">Donor</span>
                            <p className="text-gray-500">john_donor / donor123</p>
                        </div>
                        <div className="bg-white p-2 rounded-lg border">
                            <span className="font-medium text-emerald-700">NGO</span>
                            <p className="text-gray-500">helping_hands_ngo / acceptor123</p>
                        </div>
                    </div>
                </div>

                <p className="text-center mt-6 text-gray-500 text-sm">
                    Don't have an account?{' '}
                    <Link to="/register" className="text-green-600 hover:text-green-700 font-semibold">
                        Create Account
                    </Link>
                </p>
            </div>
        </div>
    );
}
