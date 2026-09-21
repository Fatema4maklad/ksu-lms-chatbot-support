import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import './AgentDashboard.css';

const API_BASE = 'http://localhost:8000';
const WS_BASE = API_BASE.replace(/^http/, 'ws');

const mapBackendMessage = (m) => ({
  id: m.id,
  role: m.role, // "user" | "assistant" | "agent"
  content: m.content,
  created_at: m.created_at,
});

function AgentDashboard() {
  const navigate = useNavigate();
  const agentName = localStorage.getItem('agent_name');
  const agentId = localStorage.getItem('agent_id');
  const sessionToken = localStorage.getItem('agent_session');

  const [queue, setQueue] = useState([]);
  const [selectedConversationId, setSelectedConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');

  const presenceWsRef = useRef(null);
  const queueWsRef = useRef(null);
  const chatWsRef = useRef(null);

  // Redirect to login if there's no session at all — this page requires
  // an authenticated agent.
  useEffect(() => {
    if (!sessionToken || !agentId) {
      navigate('/agent/login');
    }
  }, [sessionToken, agentId, navigate]);

  // Load the current queue once on mount.
  useEffect(() => {
    if (!sessionToken) return;
    fetch(`${API_BASE}/agent/queue`, {
      headers: { 'x-session-token': sessionToken },
    })
      .then((res) => {
        if (!res.ok) throw new Error('Failed to load queue');
        return res.json();
      })
      .then((data) => setQueue(data))
      .catch((err) => console.error('Queue fetch failed:', err));
  }, [sessionToken]);

  // Presence socket — keeps this agent marked "online" for as long as the
  // dashboard tab stays open, and automatically flips to "offline" server-side
  // the moment this connection drops (tab closed, network lost, etc.).
  useEffect(() => {
    if (!agentId) return;
    const ws = new WebSocket(`${WS_BASE}/ws/agent/${agentId}`);
    presenceWsRef.current = ws;
    return () => ws.close();
  }, [agentId]);

  // Queue socket — receives a live push the instant a new conversation
  // escalates, so the sidebar updates without a manual refresh.
  useEffect(() => {
    const ws = new WebSocket(`${WS_BASE}/ws/agent/queue`);
    queueWsRef.current = ws;

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'new_escalation') {
        setQueue((prev) => {
          // Avoid duplicates if this conversation is already listed.
          if (prev.some((c) => c.conversation_id === data.conversation.conversation_id)) {
            return prev;
          }
          return [data.conversation, ...prev];
        });
      }
    };

    return () => ws.close();
  }, []);

  // Chat socket for whichever conversation is currently open. Reconnects
  // whenever the agent selects a different conversation from the queue.
  useEffect(() => {
    if (!selectedConversationId) return;

    const ws = new WebSocket(`${WS_BASE}/ws/chat/${selectedConversationId}`);
    chatWsRef.current = ws;
    setMessages([]);

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'history') {
        setMessages(data.messages.map(mapBackendMessage));
      } else if (data.type === 'message') {
        setMessages((prev) => {
          if (prev.some((m) => m.id === data.message.id)) return prev;
          return [...prev, mapBackendMessage(data.message)];
        });
      }
    };

    return () => {
      ws.close();
      chatWsRef.current = null;
    };
  }, [selectedConversationId]);

  const handleSelectConversation = (conversationId) => {
    setSelectedConversationId(conversationId);
  };

  const handleSend = (e) => {
    e.preventDefault();
    if (!input.trim() || !chatWsRef.current || chatWsRef.current.readyState !== WebSocket.OPEN) return;

    chatWsRef.current.send(JSON.stringify({
      role: 'agent',
      content: input,
      agent_id: Number(agentId),
    }));
    setInput('');
  };

  const handleLogout = () => {
    localStorage.removeItem('agent_session');
    localStorage.removeItem('agent_name');
    localStorage.removeItem('agent_id');
    navigate('/agent/login');
  };

  return (
    <div className="dashboard-container" dir="rtl">
      <div className="dashboard-main">
        {selectedConversationId ? (
          <>
            <div className="dashboard-chat-header">
              محادثة: {selectedConversationId.slice(0, 8)}
            </div>
            <div className="dashboard-messages-area">
              {messages.map((msg) => (
                <div key={msg.id} className={`dashboard-message-wrapper ${msg.role}`}>
                  <div className="dashboard-message" dir="auto">
                    {msg.role === 'assistant' ? (
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    ) : (
                      msg.content
                    )}
                  </div>
                </div>
              ))}
            </div>
            <form onSubmit={handleSend} className="dashboard-input-area">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="اكتب ردك..."
              />
              <button type="submit">إرسال</button>
            </form>
          </>
        ) : (
          <div className="dashboard-empty-state">اختر محادثة من القائمة للبدء</div>
        )}
      </div>

      <div className="dashboard-sidebar">
        <div className="dashboard-sidebar-header">
          <span>{agentName}</span>
          <button onClick={handleLogout} className="dashboard-logout-btn">تسجيل الخروج</button>
        </div>
        <div className="dashboard-sidebar-title">لوحة التحكم</div>
        <div className="dashboard-queue-list">
          {queue.length === 0 && (
            <div className="dashboard-empty-queue">لا توجد محادثات بانتظار الرد</div>
          )}
          {queue.map((c) => (
            <button
              key={c.conversation_id}
              className={`dashboard-queue-item ${selectedConversationId === c.conversation_id ? 'active' : ''}`}
              onClick={() => handleSelectConversation(c.conversation_id)}
            >
              <span className="dashboard-queue-dot" />
              <span className="dashboard-queue-label">{c.conversation_id.slice(0, 8)}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

export default AgentDashboard;