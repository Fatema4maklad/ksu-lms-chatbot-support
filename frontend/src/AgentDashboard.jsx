import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import './AgentDashboard.css';

const API_BASE = 'http://localhost:8000';
const WS_BASE = API_BASE.replace(/^http/, 'ws');

const TICKET_LABELS = {
  open: 'مفتوحة',
  in_progress: 'قيد المعالجة',
  resolved: 'تم الحل',
};

const mapBackendMessage = (m) => ({
  id: m.id,
  role: m.role, // "user" | "assistant" | "agent"
  content: m.content,
  created_at: m.created_at,
});

// Backend timestamps are naive UTC (datetime.utcnow), so append "Z" so the
// browser converts them to the agent's local time correctly.
const formatDate = (iso) =>
  new Date(iso + 'Z').toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' });

const formatDay = (isoDate) =>
  new Date(isoDate).toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric' });

function MessageBubble({ msg }) {
  return (
    <div className={`dashboard-message-wrapper ${msg.role}`}>
      <div className="dashboard-message" dir="auto">
        {msg.role === 'assistant' ? (
          <ReactMarkdown>{msg.content}</ReactMarkdown>
        ) : (
          msg.content
        )}
      </div>
    </div>
  );
}

function AnalyticsView({ sessionToken }) {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [faq, setFaq] = useState(null);
  const [faqLoading, setFaqLoading] = useState(false);
  const [faqError, setFaqError] = useState('');

  useEffect(() => {
    setLoading(true);
    setError('');
    fetch(`${API_BASE}/agent/analytics`, {
      headers: { 'x-session-token': sessionToken },
    })
      .then((res) => {
        if (!res.ok) throw new Error('Failed to load analytics');
        return res.json();
      })
      .then((data) => setStats(data))
      .catch(() => setError('تعذر تحميل الإحصائيات'))
      .finally(() => setLoading(false));
  }, [sessionToken]);

  const handleGenerateFaq = async () => {
    setFaqLoading(true);
    setFaqError('');
    setFaq(null);
    try {
      const res = await fetch(`${API_BASE}/agent/analytics/faq`, {
        method: 'POST',
        headers: { 'x-session-token': sessionToken },
      });
      if (!res.ok) throw new Error('Failed to generate FAQ');
      setFaq(await res.json());
    } catch (err) {
      console.error('FAQ generation failed:', err);
      setFaqError('تعذر إنشاء الأسئلة الشائعة');
    } finally {
      setFaqLoading(false);
    }
  };

  if (loading) return <div className="dashboard-empty-state">جارٍ تحميل الإحصائيات...</div>;
  if (error) return <div className="dashboard-empty-state">{error}</div>;
  if (!stats) return null;

  const maxTraffic = Math.max(1, ...stats.traffic.map((d) => d.count));
  const maxCategory = Math.max(1, ...stats.top_categories.map((c) => c.count));
  const totalFeedback = stats.feedback.up + stats.feedback.down;

  return (
    <div className="dashboard-analytics">
      <div className="dashboard-stats-row">
        <div className="dashboard-stat-card resolved">
          <div className="dashboard-stat-icon">✅</div>
          <div className="dashboard-stat-number">{stats.resolved_count}</div>
          <div className="dashboard-stat-label">محلولة</div>
        </div>
        <div className="dashboard-stat-card active">
          <div className="dashboard-stat-icon">🔄</div>
          <div className="dashboard-stat-number">{stats.active_count}</div>
          <div className="dashboard-stat-label">نشط</div>
        </div>
        <div className="dashboard-stat-card unresolved">
          <div className="dashboard-stat-icon">⏳</div>
          <div className="dashboard-stat-number">{stats.unresolved_count}</div>
          <div className="dashboard-stat-label">غير محلولة</div>
        </div>
      </div>

      <div className="dashboard-analytics-section">
        <div className="dashboard-analytics-title">الفئات الأكثر تكراراً</div>
        {stats.top_categories.length === 0 ? (
          <div className="dashboard-analytics-empty">لا توجد بيانات كافية بعد</div>
        ) : (
          <div className="dashboard-category-list">
            {stats.top_categories.map((c) => (
              <div key={c.category} className="dashboard-category-row">
                <span className="dashboard-category-count">{c.count}</span>
                <div className="dashboard-category-bar-track">
                  <div
                    className="dashboard-category-bar-fill"
                    style={{ width: `${(c.count / maxCategory) * 100}%` }}
                  />
                  <span className="dashboard-category-name">{c.category}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="dashboard-analytics-section">
        <div className="dashboard-analytics-title">حركة المحادثات (آخر 7 أيام)</div>
        <div className="dashboard-traffic-chart">
          {stats.traffic.map((d) => (
            <div key={d.date} className="dashboard-traffic-bar-wrapper">
              <span className="dashboard-traffic-value">{d.count}</span>
              <div
                className="dashboard-traffic-bar"
                style={{ height: `${Math.max(4, (d.count / maxTraffic) * 100)}%` }}
              />
              <span className="dashboard-traffic-day">{formatDay(d.date)}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="dashboard-analytics-section">
        <div className="dashboard-analytics-title">التقييمات</div>
        <div className="dashboard-feedback-row">
          <div className="dashboard-feedback-card up">
            <div className="dashboard-feedback-number">{stats.feedback.up}</div>
            <div className="dashboard-feedback-label">👍 إيجابي</div>
          </div>
          <div className="dashboard-feedback-card down">
            <div className="dashboard-feedback-number">{stats.feedback.down}</div>
            <div className="dashboard-feedback-label">👎 سلبي</div>
          </div>
          <div className="dashboard-feedback-card rate">
            <div className="dashboard-feedback-number">
              {totalFeedback > 0 ? `${stats.feedback.down_rate_percent}%` : '—'}
            </div>
            <div className="dashboard-feedback-label">نسبة السلبي</div>
          </div>
        </div>
      </div>

      <div className="dashboard-analytics-section">
        <div className="dashboard-analytics-title-row">
          <div className="dashboard-analytics-title">الأسئلة الشائعة (بالذكاء الاصطناعي)</div>
          <button
            className="dashboard-faq-btn"
            onClick={handleGenerateFaq}
            disabled={faqLoading}
          >
            {faqLoading ? 'جارٍ التحليل...' : '✨ إنشاء الأسئلة الشائعة'}
          </button>
        </div>
        {faqLoading && (
          <div className="dashboard-analytics-empty">
            قد يستغرق هذا بضع دقائق حسب عدد الأسئلة...
          </div>
        )}
        {faqError && <div className="dashboard-analytics-empty">{faqError}</div>}
        {faq && (
          <div className="dashboard-faq-result" dir="auto">
            <div className="dashboard-faq-meta">
              تم تحليل {faq.questions_analyzed} سؤال
            </div>
            <ReactMarkdown>{faq.faq}</ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  );
}

function UploadView({ sessionToken }) {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState('');
  const [log, setLog] = useState([]);
  const [uploading, setUploading] = useState(false);

  const handleFileChange = (e) => {
    setFile(e.target.files[0] || null);
    setStatus('');
    setLog([]);
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setStatus('جار الرفع...');
    setLog([]);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch(`${API_BASE}/admin/upload-doc`, {
        method: 'POST',
        headers: { 'x-session-token': sessionToken },
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'فشل الرفع');
      }

      const data = await res.json();
      setStatus('تم الانتهاء ');
      setLog(data.ingestion_result?.log || []);
    } catch (err) {
      console.error('Upload failed:', err);
      setStatus(`خطأ: ${err.message}`);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="dashboard-analytics">
      <div className="dashboard-analytics-section">
        <div className="dashboard-analytics-title">رفع ملف جديد لقاعدة المعرفة (PDF)</div>
        <input type="file" accept=".pdf" onChange={handleFileChange} />
        <button
          className="dashboard-faq-btn"
          onClick={handleUpload}
          disabled={!file || uploading}
        >
          {uploading ? 'جارٍ الرفع...' : ' رفع وفهرسة'}
        </button>

        {status && (
          <div className="dashboard-analytics-empty" dir="auto">{status}</div>
        )}

        {log.length > 0 && (
          <div className="dashboard-faq-result" dir="auto">
            {log.map((line, i) => (
              <div key={i}>{line}</div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function AgentDashboard() {
  const navigate = useNavigate();
  const agentName = localStorage.getItem('agent_name');
  const agentId = localStorage.getItem('agent_id');
  const sessionToken = localStorage.getItem('agent_session');

  const [activeTab, setActiveTab] = useState('queue'); // "queue" | "analytics"
  const [queue, setQueue] = useState([]);
  const [selectedConversationId, setSelectedConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [resolving, setResolving] = useState(false);

  // Beneficiary profile panel state
  const [showProfile, setShowProfile] = useState(false);
  const [profile, setProfile] = useState(null);
  const [profileLoading, setProfileLoading] = useState(false);
  const [profileError, setProfileError] = useState('');

  const presenceWsRef = useRef(null);
  const queueWsRef = useRef(null);
  const chatWsRef = useRef(null);

  const selectedConversation = queue.find((c) => c.conversation_id === selectedConversationId);

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
    setActiveTab('queue');
    setSelectedConversationId(conversationId);
    setShowProfile(false);
    setProfile(null);

    // Opening an "open" conversation claims it: move it to "in_progress".
    const conversation = queue.find((c) => c.conversation_id === conversationId);
    if (conversation && conversation.ticket_status === 'open') {
      fetch(`${API_BASE}/agent/conversation/${conversationId}/status`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'x-session-token': sessionToken,
        },
        body: JSON.stringify({ ticket_status: 'in_progress' }),
      })
        .then((res) => {
          if (!res.ok) throw new Error('Failed to mark in progress');
          setQueue((prev) =>
            prev.map((c) =>
              c.conversation_id === conversationId ? { ...c, ticket_status: 'in_progress' } : c
            )
          );
        })
        .catch((err) => console.error('In-progress update failed:', err));
    }
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

  const handleOpenProfile = async () => {
    if (!selectedConversation?.university_id) return;

    setShowProfile(true);
    setProfile(null);
    setProfileError('');
    setProfileLoading(true);

    try {
      const res = await fetch(
        `${API_BASE}/agent/beneficiary/${encodeURIComponent(selectedConversation.university_id)}`,
        { headers: { 'x-session-token': sessionToken } }
      );
      if (!res.ok) throw new Error('Failed to load profile');
      setProfile(await res.json());
    } catch (err) {
      console.error('Profile fetch failed:', err);
      setProfileError('تعذر تحميل ملف الطالب');
    } finally {
      setProfileLoading(false);
    }
  };

  const handleResolve = async () => {
    if (!selectedConversationId) return;
    setResolving(true);
    try {
      const res = await fetch(
        `${API_BASE}/agent/conversation/${selectedConversationId}/status`,
        {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            'x-session-token': sessionToken,
          },
          body: JSON.stringify({ ticket_status: 'resolved' }),
        }
      );
      if (!res.ok) throw new Error('Failed to resolve conversation');

      // Remove it from the local queue and close the open chat panel.
      setQueue((prev) => prev.filter((c) => c.conversation_id !== selectedConversationId));
      setSelectedConversationId(null);
      setMessages([]);
      setShowProfile(false);
      setProfile(null);
    } catch (err) {
      console.error('Resolve failed:', err);
    } finally {
      setResolving(false);
    }
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
        {activeTab === 'analytics' ? (
          <>
            <div className="dashboard-chat-header">
              <span>الإحصائيات</span>
            </div>
            <AnalyticsView sessionToken={sessionToken} />
          </>
        ) : activeTab === 'upload' ? (
          <>
            <div className="dashboard-chat-header">
              <span>قاعدة المعرفة</span>
            </div>
            <UploadView sessionToken={sessionToken} />
          </>
        ) : selectedConversationId ? (
          <>
            <div className="dashboard-chat-header">
              <span>
                {selectedConversation?.user_name
                  ? `${selectedConversation.user_name} (${selectedConversation.university_id})`
                  : `محادثة: ${selectedConversationId.slice(0, 8)}`}
              </span>
              <div className="dashboard-chat-header-actions">
                <button
                  className="dashboard-profile-btn"
                  onClick={handleOpenProfile}
                  disabled={!selectedConversation?.university_id}
                  title={
                    selectedConversation?.university_id
                      ? 'عرض سجل الطالب'
                      : 'محادثة مجهولة — لا يوجد ملف للطالب'
                  }
                >
                  👤 ملف الطالب
                </button>
                <button
                  className="dashboard-resolve-btn"
                  onClick={handleResolve}
                  disabled={resolving}
                >
                  {resolving ? '...' : '✓ إنهاء المحادثة'}
                </button>
              </div>
            </div>

            {showProfile ? (
              <div className="dashboard-profile">
                <div className="dashboard-profile-header">
                  <button className="dashboard-back-btn" onClick={() => setShowProfile(false)}>
                    ← العودة للمحادثة
                  </button>
                  {profile && (
                    <div className="dashboard-profile-info">
                      <div className="dashboard-profile-name">{profile.name}</div>
                      <div className="dashboard-profile-id">{profile.university_id}</div>
                    </div>
                  )}
                </div>

                {profileLoading && <div className="dashboard-empty-state">جارٍ التحميل...</div>}
                {profileError && <div className="dashboard-empty-state">{profileError}</div>}

                {profile && (
                  <div className="dashboard-profile-list">
                    <div className="dashboard-profile-count">
                      عدد المحادثات: {profile.conversations.length}
                    </div>
                    {profile.conversations.map((c) => (
                      <details
                        key={c.conversation_id}
                        className="dashboard-profile-conversation"
                        open={c.conversation_id === selectedConversationId}
                      >
                        <summary>
                          <span dir="ltr">{formatDate(c.created_at)}</span>
                          <span className={`dashboard-ticket-badge ${c.ticket_status}`}>
                            {TICKET_LABELS[c.ticket_status] || c.ticket_status}
                          </span>
                          {c.conversation_id === selectedConversationId && (
                            <span className="dashboard-current-tag">(الحالية)</span>
                          )}
                        </summary>
                        <div className="dashboard-profile-messages">
                          {c.messages.map((msg) => (
                            <MessageBubble key={msg.id} msg={msg} />
                          ))}
                        </div>
                      </details>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <>
                <div className="dashboard-messages-area">
                  {messages.map((msg) => (
                    <MessageBubble key={msg.id} msg={msg} />
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
            )}
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

        <button
          className={`dashboard-analytics-toggle ${activeTab === 'analytics' ? 'active' : ''}`}
          onClick={() => setActiveTab(activeTab === 'analytics' ? 'queue' : 'analytics')}
        >
          📊 الإحصائيات
        </button>

        <button
          className={`dashboard-analytics-toggle ${activeTab === 'upload' ? 'active' : ''}`}
          onClick={() => setActiveTab(activeTab === 'upload' ? 'queue' : 'upload')}
        >
          📄 رفع ملف
        </button>

        <div className="dashboard-queue-list">
          {queue.length === 0 && (
            <div className="dashboard-empty-queue">لا توجد محادثات بانتظار الرد</div>
          )}
          {queue.map((c) => (
            <button
              key={c.conversation_id}
              className={`dashboard-queue-item ${c.ticket_status} ${
                activeTab === 'queue' && selectedConversationId === c.conversation_id ? 'active' : ''
              }`}
              onClick={() => handleSelectConversation(c.conversation_id)}
            >
              <span className="dashboard-queue-dot" />
              <span className="dashboard-queue-label">
                {c.user_name || c.conversation_id.slice(0, 8)}
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

export default AgentDashboard;