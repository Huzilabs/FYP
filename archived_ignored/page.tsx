'use client';

import { useState } from 'react';
import { register, RegisterData } from '@/lib/api';
import CameraCapture from '@/components/CameraCapture';
import getSupabaseClient from '@/lib/supabaseClient';

export default function RegisterPage() {
  const [step, setStep] = useState<'form' | 'camera' | 'success'>('form');
  const [capturedImage, setCapturedImage] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const [userId, setUserId] = useState<string>('');
  
  const [formData, setFormData] = useState<RegisterData>({
    display_name: '',
    username: '',
    consent_terms: false,
    email: '',
    phone: '',
    date_of_birth: '',
    emergency_contact: '',
    medications: [],
    allergies: [],
    accessibility_needs: '',
    preferred_language: 'English',
  });

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target;
    
    if (type === 'checkbox') {
      setFormData(prev => ({
        ...prev,
        [name]: (e.target as HTMLInputElement).checked,
      }));
    } else if (name === 'medications' || name === 'allergies') {
      setFormData(prev => ({
        ...prev,
        [name]: value.split(',').map(item => item.trim()).filter(Boolean),
      }));
    } else {
      setFormData(prev => ({
        ...prev,
        [name]: value,
      }));
    }
  };

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!formData.display_name || !formData.username) {
      setError('Display name and username are required');
      return;
    }
    
    if (!formData.consent_terms) {
      setError('You must agree to the terms and conditions');
      return;
    }
    
    setError('');
    setStep('camera');
  };

  const handleCapture = (dataUrl: string) => {
    setCapturedImage(dataUrl);
  };

  const handleRegister = async () => {
    if (!capturedImage) {
      setError('Please capture your face image');
      return;
    }

    setLoading(true);
    setError('');

    try {
      // Upload captured image to Supabase Storage under face_oftheusers/Registration/
      let response: any = null;
      try {
        const res = await fetch(capturedImage);
        const blob = await res.blob();
        const filename = `Registration/${Date.now()}_${Math.random().toString(36).slice(2,10)}.jpg`;
        // create supabase client at runtime
        const supabase = getSupabaseClient();
        const { data, error: uploadError } = await supabase.storage
          .from('face_oftheusers')
          .upload(filename, blob, { contentType: 'image/jpeg' });

        if (uploadError) {
          // fallback: send base64 image directly to backend
          console.warn('Supabase upload failed, falling back to direct upload', uploadError);
          response = await register({
            ...formData,
            face_image: capturedImage,
          });
        } else {
          // On success, send storage path as temp_storage_path to backend
          response = await register({
            ...formData,
            temp_storage_path: filename,
          });
        }
      } catch (uploadErr: any) {
        console.warn('Upload attempt threw, falling back to direct upload', uploadErr);
        response = await register({
          ...formData,
          face_image: capturedImage,
        });
      }

      if (response && response.ok && response.user_id) {
        setUserId(response.user_id);
        setStep('success');
      } else {
        setError((response && response.error) || 'Registration failed');
      }
    } catch (err: any) {
      setError(`Error: ${err?.message || err}`);
    } finally {
      setLoading(false);
    }
  };

  if (step === 'success') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-green-50 to-emerald-100 flex items-center justify-center px-4">
        <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md w-full text-center">
          <div className="mb-6">
            <div className="w-20 h-20 bg-green-500 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-12 h-12 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h2 className="text-3xl font-bold text-gray-800">Registration Successful!</h2>
          </div>
          
          <div className="space-y-3 text-left mb-6 bg-gray-50 p-4 rounded-lg">
            <p className="text-gray-700"><strong>User ID:</strong> {userId}</p>
            <p className="text-gray-700"><strong>Name:</strong> {formData.display_name}</p>
            <p className="text-gray-700"><strong>Username:</strong> {formData.username}</p>
          </div>
          
          <p className="text-gray-600 mb-6">
            Your account has been created successfully. You can now use face recognition to log in.
          </p>
          
          <a
            href="/login"
            className="inline-block px-8 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-semibold"
          >
            Go to Login
          </a>
        </div>
      </div>
    );
  }

  if (step === 'camera') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-50 to-pink-100 py-12 px-4">
        <div className="max-w-4xl mx-auto">
          <div className="bg-white rounded-2xl shadow-xl p-8">
            <h2 className="text-3xl font-bold text-center mb-2 text-gray-800">
              Capture Your Face
            </h2>
            <p className="text-center text-gray-600 mb-8">
              This will be used for face recognition authentication
            </p>

            {!capturedImage ? (
              <CameraCapture onCapture={handleCapture} onError={setError} />
            ) : (
              <div className="space-y-6">
                <div className="flex flex-col items-center">
                  <h3 className="text-lg font-semibold mb-3 text-gray-700">Preview</h3>
                  <img
                    src={capturedImage}
                    alt="Captured face"
                    className="max-w-full h-auto rounded-lg border-4 border-gray-200"
                    style={{ maxWidth: '400px' }}
                  />
                </div>

                {error && (
                  <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
                    {error}
                  </div>
                )}

                <div className="flex gap-3 justify-center">
                  <button
                    onClick={handleRegister}
                    disabled={loading}
                    className="px-8 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition disabled:bg-gray-400 font-semibold"
                  >
                    {loading ? 'Registering...' : 'Complete Registration'}
                  </button>
                  <button
                    onClick={() => setCapturedImage('')}
                    className="px-8 py-3 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition font-semibold"
                  >
                    Retake Photo
                  </button>
                  <button
                    onClick={() => setStep('form')}
                    className="px-8 py-3 bg-gray-400 text-white rounded-lg hover:bg-gray-500 transition font-semibold"
                  >
                    Back to Form
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 to-purple-100 py-12 px-4">
      <div className="max-w-2xl mx-auto">
        <div className="bg-white rounded-2xl shadow-xl p-8">
          <h1 className="text-4xl font-bold text-center mb-2 text-gray-800">
            Create Account
          </h1>
          <p className="text-center text-gray-600 mb-8">
            Register with face recognition for secure authentication
          </p>

          {error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
              {error}
            </div>
          )}

          <form onSubmit={handleFormSubmit} className="space-y-6">
            {/* Required Fields */}
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-gray-700">Required Information</h3>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Display Name *
                </label>
                <input
                  type="text"
                  name="display_name"
                  value={formData.display_name}
                  onChange={handleInputChange}
                  required
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="John Doe"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Username *
                </label>
                <input
                  type="text"
                  name="username"
                  value={formData.username}
                  onChange={handleInputChange}
                  required
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="johndoe123"
                />
              </div>
            </div>

            {/* Optional Fields */}
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-gray-700">Optional Information</h3>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Email
                  </label>
                  <input
                    type="email"
                    name="email"
                    value={formData.email}
                    onChange={handleInputChange}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="john@example.com"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Phone
                  </label>
                  <input
                    type="tel"
                    name="phone"
                    value={formData.phone}
                    onChange={handleInputChange}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="+1234567890"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Date of Birth
                </label>
                <input
                  type="date"
                  name="date_of_birth"
                  value={formData.date_of_birth}
                  onChange={handleInputChange}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Emergency Contact
                </label>
                <input
                  type="text"
                  name="emergency_contact"
                  value={formData.emergency_contact}
                  onChange={handleInputChange}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Jane Doe: +1234567890"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Medications (comma-separated)
                </label>
                <input
                  type="text"
                  name="medications"
                  value={formData.medications?.join(', ')}
                  onChange={handleInputChange}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="aspirin, ibuprofen"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Allergies (comma-separated)
                </label>
                <input
                  type="text"
                  name="allergies"
                  value={formData.allergies?.join(', ')}
                  onChange={handleInputChange}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="peanuts, penicillin"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Accessibility Needs
                </label>
                <textarea
                  name="accessibility_needs"
                  value={formData.accessibility_needs}
                  onChange={handleInputChange}
                  rows={3}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Any accessibility requirements..."
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Preferred Language
                </label>
                <select
                  name="preferred_language"
                  value={formData.preferred_language}
                  onChange={handleInputChange}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="English">English</option>
                  <option value="Spanish">Spanish</option>
                  <option value="French">French</option>
                  <option value="German">German</option>
                  <option value="Chinese">Chinese</option>
                  <option value="Arabic">Arabic</option>
                </select>
              </div>
            </div>

            {/* Terms and Conditions */}
            <div className="flex items-start gap-3 p-4 bg-gray-50 rounded-lg">
              <input
                type="checkbox"
                name="consent_terms"
                checked={formData.consent_terms}
                onChange={handleInputChange}
                required
                className="mt-1 w-5 h-5 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
              />
              <label className="text-sm text-gray-700">
                I agree to the terms and conditions and consent to the collection and processing 
                of my biometric data (facial recognition) for authentication purposes. *
              </label>
            </div>

            <button
              type="submit"
              className="w-full px-8 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-semibold text-lg"
            >
              Continue to Face Capture
            </button>
          </form>

          <div className="mt-6 text-center">
            <p className="text-gray-600">
              Already have an account?{' '}
              <a href="/login" className="text-blue-600 hover:text-blue-800 font-semibold">
                Login here
              </a>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
