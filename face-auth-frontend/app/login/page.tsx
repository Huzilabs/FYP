'use client';

import { useState } from 'react';
import { loginFace } from '@/lib/api';
import CameraCapture from '@/components/CameraCapture';
import Image from 'next/image';

export default function LoginPage() {
  const [capturedImage, setCapturedImage] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string>('');

  const handleCapture = (dataUrl: string) => {
    setCapturedImage(dataUrl);
    setError('');
    setResult(null);
  };

  const handleLogin = async () => {
    if (!capturedImage) {
      setError('Please capture an image first');
      return;
    }

    setLoading(true);
    setError('');
    setResult(null);

    try {
      const response = await loginFace(capturedImage);
      
      if (response.ok && response.user) {
        setResult({
          success: true,
          user: response.user,
          distance: response.distance,
        });
      } else {
        setError(response.error || 'Login failed');
      }
    } catch (err: any) {
      setError(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setCapturedImage('');
    setResult(null);
    setError('');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-12 px-4">
      <div className="max-w-4xl mx-auto">
        <div className="bg-white rounded-2xl shadow-xl p-8">
          <h1 className="text-4xl font-bold text-center mb-2 text-gray-800">
            Face Recognition Login
          </h1>
          <p className="text-center text-gray-600 mb-8">
            Use your face to authenticate and access your account
          </p>

          {!capturedImage ? (
            <CameraCapture onCapture={handleCapture} onError={setError} />
          ) : (
            <div className="space-y-6">
              <div className="flex flex-col items-center">
                <h3 className="text-lg font-semibold mb-3 text-gray-700">Captured Image</h3>
                <div className="relative rounded-lg overflow-hidden border-4 border-gray-200">
                  <img
                    src={capturedImage}
                    alt="Captured face"
                    className="max-w-full h-auto"
                    style={{ maxWidth: '400px' }}
                  />
                </div>
              </div>

              {error && (
                <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
                  <p className="font-semibold">Error:</p>
                  <p>{error}</p>
                </div>
              )}

              {result && result.success && (
                <div className="p-6 bg-green-50 border border-green-200 rounded-lg">
                  <h3 className="text-xl font-bold text-green-800 mb-3">✓ Login Successful!</h3>
                  <div className="space-y-2 text-gray-700">
                    <p><strong>User ID:</strong> {result.user.id}</p>
                    <p><strong>Name:</strong> {result.user.display_name}</p>
                    <p><strong>Username:</strong> {result.user.username}</p>
                    {result.user.email && <p><strong>Email:</strong> {result.user.email}</p>}
                    <p className="text-sm text-gray-500 mt-3">
                      Match confidence: {(1 - result.distance).toFixed(2)}
                    </p>
                  </div>
                </div>
              )}

              <div className="flex gap-3 justify-center">
                <button
                  onClick={handleLogin}
                  disabled={loading}
                  className="px-8 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:bg-gray-400 disabled:cursor-not-allowed font-semibold"
                >
                  {loading ? 'Authenticating...' : 'Login with Face'}
                </button>
                <button
                  onClick={handleReset}
                  className="px-8 py-3 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition font-semibold"
                >
                  Retake Photo
                </button>
              </div>
            </div>
          )}

          <div className="mt-8 text-center">
            <p className="text-gray-600">
              Don't have an account?{' '}
              <a href="/register" className="text-blue-600 hover:text-blue-800 font-semibold">
                Register here
              </a>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
