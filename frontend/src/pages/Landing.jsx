import { Link } from 'react-router-dom';
import { Leaf, ArrowRight, Recycle, Heart, MapPin, Shield, Zap, Globe } from 'lucide-react';

export default function Landing() {
    return (
        <div className="min-h-screen bg-gradient-to-br from-gray-950 via-gray-900 to-emerald-950" style={{ fontFamily: "'Inter', sans-serif" }}>
            {/* Navbar */}
            <nav className="container mx-auto px-6 py-6 flex items-center justify-between">
                <div className="flex items-center space-x-2">
                    <div className="bg-gradient-to-r from-green-500 to-emerald-400 p-2 rounded-xl">
                        <Leaf className="w-6 h-6 text-white" />
                    </div>
                    <span className="text-2xl font-bold text-white">ReLoop</span>
                </div>
                <div className="flex items-center space-x-4">
                    <Link to="/login" className="text-gray-300 hover:text-white transition font-medium px-4 py-2">Login</Link>
                    <Link to="/register" className="bg-gradient-to-r from-green-500 to-emerald-500 text-white px-6 py-2.5 rounded-xl font-semibold hover:opacity-90 transition shadow-lg shadow-green-500/20">
                        Get Started
                    </Link>
                </div>
            </nav>

            {/* Hero */}
            <section className="container mx-auto px-6 pt-20 pb-32 text-center relative">
                {/* Glow effects */}
                <div className="absolute top-10 left-1/2 -translate-x-1/2 w-[600px] h-[300px] bg-gradient-to-r from-green-500/20 to-emerald-500/20 blur-3xl rounded-full pointer-events-none" />

                <div className="relative z-10">
                    <div className="inline-flex items-center space-x-2 bg-white/10 backdrop-blur-lg text-green-400 px-4 py-2 rounded-full text-sm font-medium mb-8 border border-white/10">
                        <Recycle className="w-4 h-4" />
                        <span>AI-Powered Circular Economy Platform</span>
                    </div>

                    <h1 className="text-5xl md:text-7xl font-bold text-white mb-6 leading-tight">
                        Donate Smarter.
                        <br />
                        <span className="bg-gradient-to-r from-green-400 to-emerald-400 bg-clip-text text-transparent">
                            Impact Greater.
                        </span>
                    </h1>

                    <p className="text-xl text-gray-400 max-w-2xl mx-auto mb-10 leading-relaxed">
                        ReLoop connects donors with the right NGOs using AI matching.
                        Your donations reach where they're needed most — zero waste, maximum impact.
                    </p>

                    <div className="flex items-center justify-center space-x-4">
                        <Link to="/register?role=donor" className="bg-gradient-to-r from-green-500 to-emerald-500 text-white px-8 py-4 rounded-2xl font-bold text-lg hover:opacity-90 transition shadow-xl shadow-green-500/30 flex items-center space-x-2">
                            <span>Start Donating</span>
                            <ArrowRight className="w-5 h-5" />
                        </Link>
                        <Link to="/register?role=acceptor" className="bg-white/10 backdrop-blur-lg text-white px-8 py-4 rounded-2xl font-bold text-lg hover:bg-white/20 transition border border-white/10">
                            Register as NGO
                        </Link>
                    </div>
                </div>
            </section>

            {/* Feature Grid */}
            <section className="container mx-auto px-6 pb-24">
                <div className="grid md:grid-cols-3 gap-6">
                    {[
                        {
                            icon: Heart,
                            title: 'AI-Powered Matching',
                            desc: 'Our AI ranks NGOs by distance, urgency, and category match to ensure your donation reaches the right place.',
                            color: 'from-pink-500 to-rose-500',
                        },
                        {
                            icon: MapPin,
                            title: 'Location-Based',
                            desc: 'Find NGOs near you with real-time distance calculations. Choose from AI suggestions or select manually.',
                            color: 'from-blue-500 to-cyan-500',
                        },
                        {
                            icon: Shield,
                            title: 'Waste Fallback',
                            desc: 'If no NGO accepts your donation, we automatically match it with waste management for fair compensation.',
                            color: 'from-amber-500 to-orange-500',
                        },
                        {
                            icon: Zap,
                            title: 'Priority Pickup',
                            desc: 'Need urgent pickup? Use Priority mode for 2-hour scheduling with major logistics partners.',
                            color: 'from-purple-500 to-violet-500',
                        },
                        {
                            icon: Globe,
                            title: 'Impact Tracking',
                            desc: 'Track your waste diverted, carbon offset, and impact level with real-time interactive metrics.',
                            color: 'from-teal-500 to-emerald-500',
                        },
                        {
                            icon: Recycle,
                            title: 'Circular Economy',
                            desc: 'Every item gets a second life. ReLoop ensures nothing goes to waste in the donation ecosystem.',
                            color: 'from-green-500 to-lime-500',
                        },
                    ].map((feature, i) => {
                        const Icon = feature.icon;
                        return (
                            <div key={i} className="bg-white/5 backdrop-blur-lg rounded-2xl p-6 border border-white/10 hover:bg-white/10 transition group">
                                <div className={`w-12 h-12 rounded-xl bg-gradient-to-r ${feature.color} flex items-center justify-center mb-4 group-hover:scale-110 transition-transform`}>
                                    <Icon className="w-6 h-6 text-white" />
                                </div>
                                <h3 className="text-lg font-bold text-white mb-2">{feature.title}</h3>
                                <p className="text-gray-400 text-sm leading-relaxed">{feature.desc}</p>
                            </div>
                        );
                    })}
                </div>
            </section>

            {/* Stats */}
            <section className="container mx-auto px-6 pb-24">
                <div className="bg-gradient-to-r from-green-600 to-emerald-600 rounded-3xl p-10 text-center">
                    <h2 className="text-3xl font-bold text-white mb-8">Platform Impact</h2>
                    <div className="grid md:grid-cols-4 gap-8">
                        {[
                            { value: '1,200+', label: 'Items Donated' },
                            { value: '350 kg', label: 'Waste Diverted' },
                            { value: '45+', label: 'NGOs Connected' },
                            { value: '98%', label: 'Fulfillment Rate' },
                        ].map((stat, i) => (
                            <div key={i}>
                                <div className="text-4xl font-bold text-white mb-1">{stat.value}</div>
                                <div className="text-green-200 text-sm">{stat.label}</div>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Footer */}
            <footer className="container mx-auto px-6 py-8 border-t border-white/10">
                <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                        <Leaf className="w-5 h-5 text-green-500" />
                        <span className="text-gray-400 text-sm">ReLoop © 2025. Closing the loop on waste.</span>
                    </div>
                    <div className="flex items-center space-x-6 text-sm text-gray-500">
                        <span>About</span>
                        <span>Privacy</span>
                        <span>Terms</span>
                    </div>
                </div>
            </footer>
        </div>
    );
}
