import { useEffect, useState } from 'react'

function App() {
  const [status, setStatus] = useState('جاري الاتصال بالخادم...')
  const [isSuccess, setIsSuccess] = useState(false)

  useEffect(() => {
    fetch('http://localhost:8000/api/test')
      .then(res => {
        if (!res.ok) throw new Error('Network error')
        return res.json()
      })
      .then(data => {
        setStatus(data.message)
        setIsSuccess(true)
      })
      .catch(() => {
        setStatus('فشل الاتصال بالخادم (تأكد من تشغيل FastAPI على المنفذ 8000)')
        setIsSuccess(false)
      })
  }, [])

  return (
    <div className="min-h-screen bg-slate-100 flex items-center justify-center p-4">
      <div className="bg-white p-8 rounded-xl shadow-md max-w-md w-full text-center">
        <h1 className="text-xl font-bold text-slate-800 mb-4">
          نظام دعم Blackboard — KSU
        </h1>
        <div
          className={`p-4 rounded-lg font-medium ${
            isSuccess ? 'bg-green-50 text-green-700' : 'bg-amber-50 text-amber-800'
          }`}
        >
          {status}
        </div>
      </div>
    </div>
  )
}

export default App