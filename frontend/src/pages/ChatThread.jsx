import { useState, useEffect, useRef } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Send, Loader2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

export default function ChatThread() {
    const { donationId } = useParams();
    const { token, user } = useAuth();
    const navigate = useNavigate();
    const [messages, setMessages] = useState([]);
    const [newMessage, setNewMessage] = useState('');
    const [loading, setLoading] = useState(true);
    const [sending, setSending] = useState(false);
    const messagesEndRef = useRef(null);
    const pollRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    const loadMessages = async () => {
        try {
            const data = await api.getMessages(token, donationId);
            setMessages(Array.isArray(data) ? data : []);
        } catch (err) {
            console.error('Failed to load messages:', err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadMessages();
        // Poll every 5 seconds
        pollRef.current = setInterval(loadMessages, 5000);
        return () => clearInterval(pollRef.current);
    }, [donationId]);

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const handleSend = async (e) => {
        e.preventDefault();
        if (!newMessage.trim()) return;
        setSending(true);
        try {
            await api.sendMessage(token, donationId, newMessage.trim());
            setNewMessage('');
            await loadMessages();
        } catch (err) {
            console.error('Failed to send message:', err);
        } finally {
            setSending(false);
        }
    };

    const formatTime = (dateStr) => {
        const d = new Date(dateStr);
        return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    };

    const formatDate = (dateStr) => {
        const d = new Date(dateStr);
        return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
    };

    return (
        <div className="min-h-screen bg-gray-50 flex flex-col" style={{ fontFamily: "'Inter', sans-serif" }}>
            {/* Header */}
            <nav className="bg-white shadow-sm sticky top-0 z-50">
                <div className="container mx-auto px-6 py-4 flex items-center space-x-4">
                    <button onClick={() => navigate(-1)} className="text-gray-600 hover:text-gray-800">
                        <ArrowLeft className="w-5 h-5" />
                    </button>
                    <div>
                        <h1 className="font-bold text-gray-900">Donation Chat</h1>
                        <p className="text-xs text-gray-500">Donation #{donationId}</p>
                    </div>
                </div>
            </nav>

            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto px-6 py-4 space-y-3">
                {loading ? (
                    <div className="flex items-center justify-center py-12">
                        <Loader2 className="w-8 h-8 text-green-600 animate-spin" />
                    </div>
                ) : messages.length === 0 ? (
                    <div className="text-center py-12 text-gray-400">
                        <p className="text-lg">No messages yet</p>
                        <p className="text-sm">Start the conversation about this donation</p>
                    </div>
                ) : (
                    messages.map((msg, index) => {
                        const isOwn = msg.sender === user?.id;
                        const showDate = index === 0 || formatDate(messages[index - 1]?.created_at) !== formatDate(msg.created_at);
                        return (
                            <div key={msg.id}>
                                {showDate && (
                                    <div className="text-center my-4">
                                        <span className="text-xs bg-gray-200 text-gray-600 px-3 py-1 rounded-full">
                                            {formatDate(msg.created_at)}
                                        </span>
                                    </div>
                                )}
                                <div className={`flex ${isOwn ? 'justify-end' : 'justify-start'}`}>
                                    <div className={`max-w-xs lg:max-w-md px-4 py-2.5 rounded-2xl ${isOwn
                                            ? 'bg-green-600 text-white rounded-br-md'
                                            : 'bg-white shadow-sm border border-gray-100 text-gray-900 rounded-bl-md'
                                        }`}>
                                        {!isOwn && (
                                            <p className="text-xs font-semibold text-green-600 mb-1">
                                                {msg.sender_name} • {msg.sender_role}
                                            </p>
                                        )}
                                        <p className="text-sm">{msg.content}</p>
                                        <p className={`text-xs mt-1 ${isOwn ? 'text-green-200' : 'text-gray-400'}`}>
                                            {formatTime(msg.created_at)}
                                        </p>
                                    </div>
                                </div>
                            </div>
                        );
                    })
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="bg-white border-t border-gray-200 px-6 py-4">
                <form onSubmit={handleSend} className="flex items-center space-x-3">
                    <input
                        type="text"
                        value={newMessage}
                        onChange={(e) => setNewMessage(e.target.value)}
                        placeholder="Type a message..."
                        className="flex-1 input-field"
                        disabled={sending}
                    />
                    <button
                        type="submit"
                        disabled={sending || !newMessage.trim()}
                        className="p-3 bg-green-600 text-white rounded-xl hover:bg-green-700 transition disabled:opacity-50"
                    >
                        {sending ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
                    </button>
                </form>
            </div>
        </div>
    );
}
