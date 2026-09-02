import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import './App.css';

function App() {
  // Initialize state with a default bilingual greeting
  const [messages, setMessages] = useState([
    {
      role: 'bot',
      senderType: 'ai', // Can be 'ai' or 'human' for future implementation
      content: "Hello! I am the KSU Blackboard Support Assistant. How can I help you today?\n\nمرحباً! أنا مساعد الدعم الفني لنظام بلاك بورد بجامعة الملك سعود. كيف يمكنني مساعدتك اليوم؟"
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage = { role: 'user', content: input, senderType: 'user' };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: userMessage.content }), 
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      // Defaulting to 'ai', but your backend could eventually return a senderType flag
      setMessages((prev) => [...prev, { role: 'bot', content: data.answer, senderType: 'ai' }]);
    } catch (error) {
      console.error("Fetch error:", error);
      setMessages((prev) => [...prev, { role: 'bot', content: 'Connection error. Please try again.', senderType: 'system' }]);
    } finally {
      setIsLoading(false);
    }
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
            
            {/* dir="auto" stays ONLY here so the text aligns, not the bubble */}
            <div className="message" dir="auto">
              {msg.role === 'bot' ? (
                <ReactMarkdown>{msg.content}</ReactMarkdown>
              ) : (
                msg.content
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

      <form onSubmit={sendMessage} className="input-area">
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
  );}

export default App;