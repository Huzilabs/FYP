import Link from 'next/link';

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50">
      {/* Hero Section */}
      <div className="container mx-auto px-4 py-20">
        <div className="max-w-4xl mx-auto text-center">
          <h1 className="text-6xl font-bold mb-6 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
            Face Recognition Authentication
          </h1>
          <p className="text-xl text-gray-700 mb-12 max-w-2xl mx-auto">
            Secure, fast, and convenient authentication using facial recognition technology. 
            Say goodbye to passwords and hello to seamless access.
          </p>
          
          <div className="flex gap-6 justify-center flex-wrap">
            <Link
              href="/register"
              className="px-8 py-4 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition text-lg font-semibold shadow-lg hover:shadow-xl transform hover:-translate-y-1 duration-200"
            >
              Create Account
            </Link>
            <Link
              href="/login"
              className="px-8 py-4 bg-white text-blue-600 border-2 border-blue-600 rounded-xl hover:bg-blue-50 transition text-lg font-semibold shadow-lg hover:shadow-xl transform hover:-translate-y-1 duration-200"
            >
              Login with Face
            </Link>
          </div>
        </div>
      </div>

      {/* Features Section */}
      <div className="container mx-auto px-4 py-16">
        <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto">
          <div className="bg-white p-8 rounded-2xl shadow-lg hover:shadow-xl transition">
            <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mb-4">
              <svg className="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
            </div>
            <h3 className="text-2xl font-bold mb-3 text-gray-800">Secure</h3>
            <p className="text-gray-600">
              Advanced facial recognition technology ensures your account is protected with biometric security.
            </p>
          </div>

          <div className="bg-white p-8 rounded-2xl shadow-lg hover:shadow-xl transition">
            <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mb-4">
              <svg className="w-8 h-8 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <h3 className="text-2xl font-bold mb-3 text-gray-800">Fast</h3>
            <p className="text-gray-600">
              Log in instantly with just your face. No more typing passwords or waiting for OTPs.
            </p>
          </div>

          <div className="bg-white p-8 rounded-2xl shadow-lg hover:shadow-xl transition">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mb-4">
              <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.828 14.828a4 4 0 01-5.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h3 className="text-2xl font-bold mb-3 text-gray-800">Convenient</h3>
            <p className="text-gray-600">
              No need to remember complex passwords. Your face is all you need for authentication.
            </p>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="container mx-auto px-4 py-8 text-center text-gray-600">
        <p>© 2025 Face Recognition Auth. Built with Flask & Next.js</p>
      </footer>
    </div>
  );
}
