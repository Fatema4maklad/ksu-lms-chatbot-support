import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import './App.css';

const categoryTree = {
  "الرئيسية": [
    "الدخول والحسابات",
    "الشؤون الأكاديمية",
    "مشكلة تقنية عامة"
  ],
  "الدخول والحسابات": [
    "تسجيل الدخول",
    "كلمة المرور",
    "مشاكل الحساب والبيانات"
  ],
  "الشؤون الأكاديمية": [
    "المقررات",
    "الحذف والإضافة",
    "الدرجات"
  ],
  "مشكلة تقنية عامة": [
    "رسالة خطأ",
    "رفع أو تحميل الملفات",
    "أخرى (اكتب مشكلتك)"
  ]
};

function App() {
  const [messages, setMessages] = useState([
    {
      role: 'bot',
      senderType: 'ai',
      content: "Hello! I am the KSU Blackboard Support Assistant. How can I help you today?\n\nمرحباً! أنا مساعد الدعم الفني لنظام بلاك بورد بجامعة الملك سعود. يرجى اختيار الفئة المناسبة لمشكلتك أو كتابة سؤالك مباشرة.",
      feedback: null
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [currentOptions, setCurrentOptions] = useState(categoryTree["الرئيسية"]);

  const handleOptionClick = (option) => {
    if (categoryTree[option]) {
      setCurrentOptions(categoryTree[option]);
    } else {
      let textToSend = option === "أخرى (اكتب مشكلتك)" ? "مشكلة أخرى" : option;
      sendUserText(textToSend);
      setCurrentOptions([]); 
    }
  };

  const resetMenu = () => {
    setCurrentOptions(categoryTree["الرئيسية"]);
  };

  const handleFeedback = (index, type) => {
    // Update local state to show selection. In the future, send this to your FastAPI database.
    setMessages((prev) => prev.map((msg, i) => 
      i === index ? { ...msg, feedback: type } : msg
    ));
  };

  const sendUserText = async (text) => {
    if (!text.trim()) return;

    const userMessage = { role: 'user', content: text, senderType: 'user' };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: text }), 
      });

      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

      const data = await response.json();
      setMessages((prev) => [...prev, { role: 'bot', content: data.answer, senderType: 'ai', feedback: null }]);
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
              
              {/* Feedback Widget - Only show on Bot responses, skip the first greeting */}
              {msg.role === 'bot' && index !== 0 && (
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
                ↩ عودة
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

export default App;