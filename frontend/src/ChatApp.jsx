import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import './App.css';

const categoryTree = {
  "الرئيسية": [
    "الدخول والحسابات",
    "الشؤون الأكاديمية",
    "مشكلة تقنية عامة"
  ],
  
  // Level 2: Sub-categories
  "الدخول والحسابات": [
    "تسجيل الدخول واسم النظام",
    "كلمة المرور",
    "مشاكل الحساب والبيانات"
  ],
  "الشؤون الأكاديمية": [
    "المقررات",
    "الحذف والإضافة",
    "الدرجات"
  ],
  "مشكلة تقنية عامة": [
    "رسائل الخطأ",
    "رفع وتحميل الملفات",
    "أخرى (اكتب مشكلتك)"
  ],

  // Level 3: Pre-made Questions (Leaf Nodes)
  "تسجيل الدخول واسم النظام": [
    "كيف أسجل دخولي للنظام؟",
    "ما هو الرابط الصحيح لنظام البلاك بورد؟"
  ],
  "كلمة المرور": [
    "نسيت كلمة السر",
    "كلمة السر صحيحة ولكن النظام لا يعمل",
    "كيف أغير كلمة المرور؟"
  ],
  "مشاكل الحساب والبيانات": [
    "كيف أقوم بتحديث بياناتي الشخصية؟",
    "حسابي مقفل أو غير مفعل"
  ],
  "المقررات": [
    "أين أجد مقرراتي الدراسية؟",
    "محتوى المقرر أو المحاضرات لا تفتح",
    "كيف أتواصل مع أستاذ المقرر؟"
  ],
  "الحذف والإضافة": [
    "أضفت مقرر في البوابة ولم يظهر في البلاك بورد",
    "حذفت مقرر وما زال يظهر لي",
    "متى تتحدث المقررات في النظام؟"
  ],
  "الدرجات": [
    "أين أجد درجاتي للواجبات والاختبارات؟",
    "الدرجة غير ظاهرة لي",
    "كيف أعرف تفاصيل الدرجة والملاحظات؟"
  ],
  "رسائل الخطأ": [
    "يظهر لي (Access Denied)",
    "النظام معلق أو الصفحة لا تفتح"
  ],
  "رفع وتحميل الملفات": [
    "لا أستطيع رفع الواجب أو الاختبار",
    "الملف المرفق حجمه كبير جداً",
    "لا أستطيع تحميل ملفات المقرر"
  ]
};

const API_BASE = 'http://localhost:8000';

function ChatApp() {
  const [messages, setMessages] = useState([
    {
      role: 'bot',
      senderType: 'ai',
      content: "Hello! I am the KSU Blackboard Support Assistant. How can I help you today?\n\nمرحباً! أنا مساعد الدعم الفني لنظام بلاك بورد بجامعة الملك سعود. يرجى اختيار الفئة المناسبة لمشكلتك أو كتابة سؤالك مباشرة.",
      feedback: null
      // Note: no `id` on this message — it's a static greeting, never sent to
      // the backend, so there's nothing to attach feedback to.
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [currentOptions, setCurrentOptions] = useState(categoryTree["الرئيسية"]);
  // conversation_id ties every message in this browser session to one thread
  // server-side, so the assistant can recall earlier turns. It starts null
  // (brand-new conversation) and gets set from the first API response.
  const [conversationId, setConversationId] = useState(null);

  const handleOptionClick = (option) => {
    // If the option exists as a key in the tree, show its children
    if (categoryTree[option]) {
      setCurrentOptions(categoryTree[option]);
    } else {
      // If it has no children, it's a final question. Send it to the bot.
      let textToSend = option === "أخرى (اكتب مشكلتك)" ? "مشكلة أخرى" : option;
      sendUserText(textToSend);
      setCurrentOptions([]); 
    }
  };

  const resetMenu = () => {
    setCurrentOptions(categoryTree["الرئيسية"]);
  };

  const handleFeedback = async (index, type) => {
    const message = messages[index];
    // Only real assistant replies (persisted server-side) have an `id`.
    // The static greeting and any client-only error bubbles don't, so
    // there's nothing valid to log feedback against.
    if (!message?.id) return;

    setMessages((prev) => prev.map((msg, i) =>
      i === index ? { ...msg, feedback: type } : msg
    ));

    try {
      await fetch(`${API_BASE}/api/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message_id: message.id, rating: type }),
      });
    } catch (error) {
      console.error('Feedback submit failed:', error);
      // Feedback is best-effort UI sugar — a failed network call here
      // shouldn't interrupt the chat, so we just log it.
    }
  };

  const sendUserText = async (text) => {
    if (!text.trim()) return;

    const userMessage = { role: 'user', content: text, senderType: 'user' };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const headers = { 'Content-Type': 'application/json' };
      const sessionToken = localStorage.getItem('user_session');
      if (sessionToken) {
        headers['x-session-token'] = sessionToken;
      }

      const response = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ question: text, conversation_id: conversationId }),
      });

      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

      const data = await response.json();
      setConversationId(data.conversation_id);
      setMessages((prev) => [
        ...prev,
        {
          id: data.message_id,
          role: 'bot',
          content: data.answer,
          senderType: 'ai',
          feedback: null,
        },
      ]);
    } catch (error) {
      console.error("Fetch error:", error);
      setMessages((prev) => [...prev, { role: 'bot', content: 'Connection error. Please try again.', senderType: 'system', feedback: null }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    sendUserText(input);
    setInput('');
    setCurrentOptions([]); 
  };

  return (
    <div className="chat-container">
      <header>
        <h2>KSU Blackboard Assistant</h2>
      </header>
      
      <div className="messages-area">
        {messages.map((msg, index) => (
          <div key={index} className={`message-wrapper ${msg.role}`}>
            {msg.role === 'bot' && (
              <div className="sender-icon" title={msg.senderType === 'human' ? 'Human Agent' : 'AI Assistant'}>
                {msg.senderType === 'human' ? '🎧' : '🤖'}
              </div>
            )}
            <div className="message" dir="auto">
              {msg.role === 'bot' ? (
                <ReactMarkdown>{msg.content}</ReactMarkdown>
              ) : (
                msg.content
              )}
              
              {msg.role === 'bot' && msg.id && (
                <div className="feedback-container">
                  <span className="feedback-text">هل كان هذا الرد مفيداً؟</span>
                  <button 
                    className={`feedback-btn ${msg.feedback === 'up' ? 'active' : ''}`}
                    onClick={() => handleFeedback(index, 'up')}
                    disabled={msg.feedback !== null}
                  >👍</button>
                  <button 
                    className={`feedback-btn ${msg.feedback === 'down' ? 'active' : ''}`}
                    onClick={() => handleFeedback(index, 'down')}
                    disabled={msg.feedback !== null}
                  >👎</button>
                </div>
              )}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="message-wrapper bot">
             <div className="sender-icon">🤖</div>
             <div className="message">Typing...</div>
          </div>
        )}
      </div>

      <div className="options-container" dir="rtl">
        {currentOptions.length > 0 ? (
          <>
            {currentOptions !== categoryTree["الرئيسية"] && (
              <button type="button" className="option-chip back-btn" onClick={resetMenu}>
                ↩ القائمة الرئيسية
              </button>
            )}
            {currentOptions.map((opt, i) => (
              <button key={i} type="button" className="option-chip" onClick={() => handleOptionClick(opt)}>
                {opt}
              </button>
            ))}
          </>
        ) : (
          <button type="button" className="option-chip restart-btn" onClick={resetMenu}>
            🏠 العودة للقائمة الرئيسية
          </button>
        )}
      </div>

      <form onSubmit={handleSubmit} className="input-area">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question..."
          disabled={isLoading}
        />
        <button type="submit" disabled={isLoading}>Send</button>
      </form>
    </div>
  );
}

export default ChatApp;