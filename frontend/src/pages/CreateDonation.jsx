import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Leaf, Upload, ArrowLeft, MapPin, Star, Zap, Clock, Truck, Package, Loader2, Calendar } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

const CATEGORIES = [
    { value: 'CLOTHES', label: 'Clothes', emoji: '👕' },
    { value: 'TOYS', label: 'Toys', emoji: '🧸' },
    { value: 'BOOKS', label: 'Books', emoji: '📚' },
];

const CONDITIONS = [
    { value: 'NEW', label: 'New', color: 'green' },
    { value: 'GENTLY_USED', label: 'Gently Used', color: 'blue' },
    { value: 'USED', label: 'Used', color: 'gray' },
];

const DELIVERY_METHODS = [
    { value: 'PLATFORM_LOGISTICS', label: 'Platform Logistics', desc: 'Porter, Rapido, Uber', icon: Truck },
    { value: 'NGO_PICKUP', label: 'NGO Pickup', desc: 'Let the NGO arrange pickup', icon: Package },
    { value: 'SELF_DROP', label: 'Self Drop-off', desc: 'Drop items yourself', icon: MapPin },
];

export default function CreateDonation() {
    const { token } = useAuth();
    const navigate = useNavigate();
    const [step, setStep] = useState(1); // Multi-step form
    const [formData, setFormData] = useState({
        category: 'CLOTHES',
        quantity: '',
        condition: 'GENTLY_USED',
        description: '',
        pickup_address: '',
        delivery_method: 'SELF_DROP',
        logistics_provider_choice: '',
        is_priority: false,
    });
    const [images, setImages] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [suggestedNGOs, setSuggestedNGOs] = useState([]);
    const [selectedNGO, setSelectedNGO] = useState(null);
    const [loadingNGOs, setLoadingNGOs] = useState(false);

    // Fetch NGO suggestions when moving to step 2
    useEffect(() => {
        if (step === 2 && formData.category) {
            fetchNGOSuggestions();
        }
    }, [step]);

    const fetchNGOSuggestions = async () => {
        setLoadingNGOs(true);
        try {
            const data = await api.getSuggestedNGOs(token, formData.category);
            setSuggestedNGOs(Array.isArray(data) ? data : (data?.results || []));
        } catch (err) {
            console.error('Failed to fetch NGO suggestions:', err);
        } finally {
            setLoadingNGOs(false);
        }
    };

    const handleImageChange = (e) => {
        const files = Array.from(e.target.files);
        setImages(files);
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            const formDataObj = new FormData();
            Object.keys(formData).forEach(key => {
                if (formData[key] !== '' && formData[key] !== null) {
                    formDataObj.append(key, formData[key]);
                }
            });
            if (selectedNGO) {
                formDataObj.append('selected_acceptor', selectedNGO.id);
            }
            images.forEach((image) => {
                formDataObj.append('uploaded_images', image);
            });

            const response = await api.createDonation(token, formDataObj);
            if (response.id) {
                navigate('/donor/dashboard');
            } else {
                setError('Failed to create donation');
            }
        } catch (err) {
            setError(err.message || 'Error creating donation. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    const getScoreColor = (score) => {
        if (score >= 70) return 'text-green-600 bg-green-50';
        if (score >= 40) return 'text-yellow-600 bg-yellow-50';
        return 'text-gray-600 bg-gray-50';
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-gray-50 to-green-50" style={{ fontFamily: "'Inter', sans-serif" }}>
            {/* Navbar */}
            <nav className="bg-white/80 backdrop-blur-lg shadow-sm sticky top-0 z-50">
                <div className="container mx-auto px-6 py-4 flex items-center space-x-4">
                    <button onClick={() => navigate(-1)} className="text-gray-600 hover:text-gray-800 transition">
                        <ArrowLeft className="w-5 h-5" />
                    </button>
                    <div className="flex items-center space-x-2">
                        <div className="bg-gradient-to-r from-green-600 to-emerald-600 p-1.5 rounded-lg">
                            <Leaf className="w-5 h-5 text-white" />
                        </div>
                        <span className="text-lg font-bold text-gray-900">Create Donation</span>
                    </div>
                    {/* Step Indicator */}
                    <div className="flex-1 flex justify-center">
                        <div className="flex items-center space-x-2">
                            {[1, 2, 3].map((s) => (
                                <div key={s} className="flex items-center">
                                    <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold transition-all ${step >= s ? 'bg-green-600 text-white' : 'bg-gray-200 text-gray-500'
                                        }`}>
                                        {s}
                                    </div>
                                    {s < 3 && <div className={`w-12 h-0.5 ${step > s ? 'bg-green-600' : 'bg-gray-200'}`} />}
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </nav>

            <div className="container mx-auto px-6 py-8 max-w-3xl">
                {error && (
                    <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl mb-6 text-sm">
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit}>
                    {/* Step 1: Item Details */}
                    {step === 1 && (
                        <div className="space-y-6 animate-fadeIn">
                            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
                                <h2 className="text-xl font-bold text-gray-900 mb-6">What are you donating?</h2>

                                {/* Category */}
                                <div className="mb-6">
                                    <label className="block text-sm font-semibold text-gray-700 mb-3">Category</label>
                                    <div className="grid grid-cols-3 gap-4">
                                        {CATEGORIES.map((cat) => (
                                            <button
                                                key={cat.value}
                                                type="button"
                                                onClick={() => setFormData({ ...formData, category: cat.value })}
                                                className={`p-4 rounded-xl border-2 transition-all duration-200 ${formData.category === cat.value
                                                    ? 'border-green-600 bg-green-50 shadow-sm'
                                                    : 'border-gray-200 hover:border-gray-300'
                                                    }`}
                                            >
                                                <div className="text-2xl mb-1">{cat.emoji}</div>
                                                <div className="font-semibold text-gray-900 text-sm">{cat.label}</div>
                                            </button>
                                        ))}
                                    </div>
                                </div>

                                {/* Quantity + Condition */}
                                <div className="grid grid-cols-2 gap-4 mb-6">
                                    <div>
                                        <label className="block text-sm font-semibold text-gray-700 mb-2">Quantity</label>
                                        <input
                                            type="number"
                                            className="input-field"
                                            value={formData.quantity}
                                            onChange={(e) => setFormData({ ...formData, quantity: e.target.value })}
                                            required
                                            min="1"
                                            placeholder="e.g. 5"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-semibold text-gray-700 mb-2">Condition</label>
                                        <select
                                            className="input-field"
                                            value={formData.condition}
                                            onChange={(e) => setFormData({ ...formData, condition: e.target.value })}
                                        >
                                            {CONDITIONS.map(c => (
                                                <option key={c.value} value={c.value}>{c.label}</option>
                                            ))}
                                        </select>
                                    </div>
                                </div>

                                {/* Description */}
                                <div className="mb-6">
                                    <label className="block text-sm font-semibold text-gray-700 mb-2">Description</label>
                                    <textarea
                                        className="input-field"
                                        rows="3"
                                        value={formData.description}
                                        onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                        placeholder="Describe the items you're donating..."
                                    />
                                </div>

                                {/* Pickup Address */}
                                <div className="mb-6">
                                    <label className="block text-sm font-semibold text-gray-700 mb-2">Pickup Address</label>
                                    <textarea
                                        className="input-field"
                                        rows="2"
                                        value={formData.pickup_address}
                                        onChange={(e) => setFormData({ ...formData, pickup_address: e.target.value })}
                                        required
                                        placeholder="Enter your full pickup address"
                                    />
                                </div>

                                {/* Images */}
                                <div>
                                    <label className="block text-sm font-semibold text-gray-700 mb-2">Photos</label>
                                    <div className="border-2 border-dashed border-gray-300 rounded-xl p-6 text-center hover:border-green-400 transition-colors">
                                        <Upload className="w-10 h-10 text-gray-400 mx-auto mb-2" />
                                        <p className="text-gray-500 text-sm mb-3">Click to upload photos of your items</p>
                                        <input
                                            type="file"
                                            multiple
                                            accept="image/*"
                                            onChange={handleImageChange}
                                            className="hidden"
                                            id="image-upload"
                                        />
                                        <label htmlFor="image-upload" className="inline-block px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium cursor-pointer hover:bg-green-700 transition">
                                            Choose Files
                                        </label>
                                        {images.length > 0 && (
                                            <p className="text-sm text-green-600 mt-2 font-medium">{images.length} file(s) selected</p>
                                        )}
                                    </div>
                                </div>
                            </div>

                            <button
                                type="button"
                                onClick={() => {
                                    if (!formData.quantity || !formData.pickup_address) {
                                        setError('Please fill in all required fields.');
                                        return;
                                    }
                                    setError('');
                                    setStep(2);
                                }}
                                className="btn-primary w-full"
                            >
                                Continue to NGO Selection →
                            </button>
                        </div>
                    )}

                    {/* Step 2: NGO Selection */}
                    {step === 2 && (
                        <div className="space-y-6 animate-fadeIn">
                            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
                                <h2 className="text-xl font-bold text-gray-900 mb-2">Choose an NGO</h2>
                                <p className="text-gray-500 text-sm mb-6">AI-ranked suggestions based on distance, urgency, and category match</p>

                                {loadingNGOs ? (
                                    <div className="flex items-center justify-center py-12">
                                        <Loader2 className="w-8 h-8 text-green-600 animate-spin" />
                                        <span className="ml-3 text-gray-500">Finding best matches...</span>
                                    </div>
                                ) : suggestedNGOs.length === 0 ? (
                                    <div className="text-center py-8 text-gray-500">
                                        <p>No NGOs available at the moment. You can still create the donation.</p>
                                    </div>
                                ) : (
                                    <div className="space-y-3">
                                        {suggestedNGOs.map((ngo, index) => (
                                            <div
                                                key={ngo.id}
                                                onClick={() => setSelectedNGO(selectedNGO?.id === ngo.id ? null : ngo)}
                                                className={`p-4 rounded-xl border-2 cursor-pointer transition-all duration-200 ${selectedNGO?.id === ngo.id
                                                    ? 'border-green-600 bg-green-50 shadow-md'
                                                    : 'border-gray-200 hover:border-gray-300 hover:shadow-sm'
                                                    }`}
                                            >
                                                <div className="flex items-start justify-between">
                                                    <div className="flex-1">
                                                        <div className="flex items-center space-x-2 mb-1">
                                                            {index === 0 && (
                                                                <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs font-bold rounded-full">
                                                                    AI Recommended
                                                                </span>
                                                            )}
                                                            <h3 className="font-bold text-gray-900">{ngo.organization_name}</h3>
                                                        </div>
                                                        <div className="flex items-center space-x-3 mt-2 text-xs text-gray-500">
                                                            {ngo.distance !== null && (
                                                                <span className="flex items-center">
                                                                    <MapPin className="w-3 h-3 mr-1" />
                                                                    {ngo.distance} km
                                                                </span>
                                                            )}
                                                            {ngo.category_match && (
                                                                <span className="flex items-center text-green-600">
                                                                    ✓ Category Match
                                                                </span>
                                                            )}
                                                            {ngo.urgency && (
                                                                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${ngo.urgency === 'CRITICAL' ? 'bg-red-100 text-red-700' :
                                                                    ngo.urgency === 'HIGH' ? 'bg-orange-100 text-orange-700' :
                                                                        ngo.urgency === 'MEDIUM' ? 'bg-yellow-100 text-yellow-700' :
                                                                            'bg-gray-100 text-gray-600'
                                                                    }`}>
                                                                    {ngo.urgency} Urgency
                                                                </span>
                                                            )}
                                                            {ngo.has_pickup_capability && (
                                                                <span className="flex items-center text-blue-600">
                                                                    <Truck className="w-3 h-3 mr-1" /> Pickup Available
                                                                </span>
                                                            )}
                                                        </div>
                                                        <p className="text-xs text-gray-400 mt-1">{ngo.address}</p>
                                                    </div>
                                                    <div className={`px-3 py-1.5 rounded-lg text-sm font-bold ${getScoreColor(ngo.score)}`}>
                                                        {ngo.score}%
                                                    </div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>

                            <div className="flex space-x-4">
                                <button type="button" onClick={() => setStep(1)}
                                    className="flex-1 px-6 py-3 border-2 border-gray-300 text-gray-700 rounded-xl font-semibold hover:bg-gray-50 transition">
                                    ← Back
                                </button>
                                <button type="button" onClick={() => setStep(3)}
                                    className="flex-1 btn-primary">
                                    Continue to Delivery →
                                </button>
                            </div>
                        </div>
                    )}

                    {/* Step 3: Delivery & Schedule */}
                    {step === 3 && (
                        <div className="space-y-6 animate-fadeIn">
                            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
                                <h2 className="text-xl font-bold text-gray-900 mb-6">Delivery & Schedule</h2>

                                {/* Delivery Method */}
                                <div className="mb-6">
                                    <label className="block text-sm font-semibold text-gray-700 mb-3">Delivery Method</label>
                                    <div className="space-y-3">
                                        {DELIVERY_METHODS.map((method) => {
                                            const Icon = method.icon;
                                            return (
                                                <div
                                                    key={method.value}
                                                    onClick={() => setFormData({ ...formData, delivery_method: method.value })}
                                                    className={`p-4 rounded-xl border-2 cursor-pointer transition-all duration-200 flex items-center space-x-4 ${formData.delivery_method === method.value
                                                        ? 'border-green-600 bg-green-50'
                                                        : 'border-gray-200 hover:border-gray-300'
                                                        }`}
                                                >
                                                    <Icon className={`w-6 h-6 ${formData.delivery_method === method.value ? 'text-green-600' : 'text-gray-400'}`} />
                                                    <div>
                                                        <div className="font-semibold text-gray-900">{method.label}</div>
                                                        <div className="text-xs text-gray-500">{method.desc}</div>
                                                    </div>
                                                </div>
                                            );
                                        })}
                                    </div>
                                </div>

                                {/* Provider selection for platform logistics */}
                                {formData.delivery_method === 'PLATFORM_LOGISTICS' && (
                                    <div className="mb-6 p-4 bg-blue-50 rounded-xl border border-blue-200">
                                        <label className="block text-sm font-semibold text-blue-800 mb-3">Choose Provider</label>
                                        <div className="grid grid-cols-3 gap-3">
                                            {['PORTER', 'RAPIDO', 'UBER'].map((provider) => (
                                                <button
                                                    key={provider}
                                                    type="button"
                                                    onClick={() => setFormData({ ...formData, logistics_provider_choice: provider })}
                                                    className={`p-3 rounded-lg border-2 text-sm font-semibold transition ${formData.logistics_provider_choice === provider
                                                        ? 'border-blue-600 bg-blue-100 text-blue-800'
                                                        : 'border-gray-200 bg-white text-gray-600 hover:border-gray-300'
                                                        }`}
                                                >
                                                    {provider}
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {/* Priority Toggle */}
                                <div className="flex items-center justify-between p-4 bg-orange-50 rounded-xl border border-orange-200 mb-6">
                                    <div className="flex items-center space-x-3">
                                        <Zap className="w-5 h-5 text-orange-600" />
                                        <div>
                                            <div className="font-semibold text-gray-900">Priority Donation</div>
                                            <div className="text-xs text-gray-500">Faster pickup within 2 hours</div>
                                        </div>
                                    </div>
                                    <label className="relative inline-flex items-center cursor-pointer">
                                        <input
                                            type="checkbox"
                                            checked={formData.is_priority}
                                            onChange={(e) => setFormData({ ...formData, is_priority: e.target.checked })}
                                            className="sr-only peer"
                                        />
                                        <div className="w-11 h-6 bg-gray-200 peer-focus:ring-2 peer-focus:ring-orange-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:bg-orange-500 after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all"></div>
                                    </label>
                                </div>

                                {/* NGO Selected Summary */}
                                {selectedNGO && (
                                    <div className="p-4 bg-green-50 rounded-xl border border-green-200">
                                        <div className="flex items-center space-x-2 mb-1">
                                            <Star className="w-4 h-4 text-green-600" />
                                            <span className="text-sm font-semibold text-green-800">Selected NGO</span>
                                        </div>
                                        <p className="font-bold text-gray-900">{selectedNGO.organization_name}</p>
                                        <p className="text-xs text-gray-500">{selectedNGO.address}</p>
                                    </div>
                                )}
                            </div>

                            {/* Deadline & Pickup Window */}
                            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
                                <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center space-x-2">
                                    <Calendar className="w-5 h-5 text-purple-600" />
                                    <span>Schedule</span>
                                </h3>
                                <div className="space-y-4">
                                    <div>
                                        <label className="block text-sm font-semibold text-gray-700 mb-2">Donation Deadline</label>
                                        <input
                                            type="date"
                                            className="input-field"
                                            value={formData.donation_deadline || ''}
                                            onChange={(e) => setFormData({ ...formData, donation_deadline: e.target.value })}
                                            min={new Date().toISOString().split('T')[0]}
                                        />
                                        <p className="text-xs text-gray-400 mt-1">If no NGO accepts by this date, waste fallback will be triggered</p>
                                    </div>
                                    <div className="grid grid-cols-2 gap-4">
                                        <div>
                                            <label className="block text-sm font-semibold text-gray-700 mb-2">Preferred Pickup Start</label>
                                            <input
                                                type="datetime-local"
                                                className="input-field"
                                                value={formData.preferred_pickup_start || ''}
                                                onChange={(e) => setFormData({ ...formData, preferred_pickup_start: e.target.value })}
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-sm font-semibold text-gray-700 mb-2">Preferred Pickup End</label>
                                            <input
                                                type="datetime-local"
                                                className="input-field"
                                                value={formData.preferred_pickup_end || ''}
                                                onChange={(e) => setFormData({ ...formData, preferred_pickup_end: e.target.value })}
                                            />
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div className="flex space-x-4">
                                <button type="button" onClick={() => setStep(2)}
                                    className="flex-1 px-6 py-3 border-2 border-gray-300 text-gray-700 rounded-xl font-semibold hover:bg-gray-50 transition">
                                    ← Back
                                </button>
                                <button
                                    type="submit"
                                    disabled={loading}
                                    className="flex-1 btn-primary flex items-center justify-center space-x-2"
                                >
                                    {loading ? (
                                        <>
                                            <Loader2 className="w-5 h-5 animate-spin" />
                                            <span>Creating...</span>
                                        </>
                                    ) : (
                                        <span>🎉 Create Donation</span>
                                    )}
                                </button>
                            </div>
                        </div>
                    )}
                </form>
            </div>
        </div>
    );
}
