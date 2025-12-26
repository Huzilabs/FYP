const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:5000';

export interface ApiResponse<T = any> {
  ok: boolean;
  error?: string;
  detail?: string;
  [key: string]: any;
}

export interface User {
  id: string;
  display_name: string;
  username: string;
  email?: string;
  phone?: string;
  date_of_birth?: string;
  emergency_contact?: string;
  medications?: string[];
  allergies?: string[];
  accessibility_needs?: string;
  preferred_language?: string;
}

export interface FaceLocation {
  top: number;
  right: number;
  bottom: number;
  left: number;
}

// Helper to convert file/blob to data URL
export const fileToDataURL = (file: File | Blob): Promise<string> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
};

// POST /api/detect_face
export const detectFace = async (imageDataUrl: string): Promise<ApiResponse<{ faces: FaceLocation[] }>> => {
  const response = await fetch(`${API_URL}/api/detect_face`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ face_image: imageDataUrl }),
  });
  return response.json();
};

// POST /api/upload_face_temp
export const uploadFaceTemp = async (imageDataUrl: string): Promise<ApiResponse> => {
  const response = await fetch(`${API_URL}/api/upload_face_temp`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ face_image: imageDataUrl }),
  });
  return response.json();
};

// POST /api/capture_face
export const captureFace = async (imageDataUrl: string, userId?: string): Promise<ApiResponse> => {
  const body: any = { face_image: imageDataUrl };
  if (userId) body.user_id = userId;
  
  const response = await fetch(`${API_URL}/api/capture_face`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return response.json();
};

// POST /api/register
export interface RegisterData {
  display_name: string;
  username: string;
  consent_terms: boolean;
  email?: string;
  phone?: string;
  date_of_birth?: string;
  emergency_contact?: string;
  medications?: string[];
  allergies?: string[];
  accessibility_needs?: string;
  preferred_language?: string;
  face_image?: string;
  temp_storage_path?: string;
}

export const register = async (data: RegisterData): Promise<ApiResponse<{ user_id: string }>> => {
  const response = await fetch(`${API_URL}/api/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return response.json();
};

// POST /api/attach_image
export const attachImage = async (userId: string, imageDataUrl?: string, tempPath?: string): Promise<ApiResponse> => {
  const body: any = { user_id: userId };
  if (imageDataUrl) body.face_image = imageDataUrl;
  if (tempPath) body.temp_storage_path = tempPath;
  
  const response = await fetch(`${API_URL}/api/attach_image`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return response.json();
};

// POST /api/login_face
export const loginFace = async (
  imageDataUrl: string,
  threshold: number = 0.5,
  limit: number = 1
): Promise<ApiResponse<{ user: User; distance: number }>> => {
  const response = await fetch(`${API_URL}/api/login_face`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ face_image: imageDataUrl, threshold, limit }),
  });
  return response.json();
};

// GET /api/users/<user_id>
export const getUser = async (userId: string, actorUserId: string): Promise<ApiResponse<{ user: User }>> => {
  const response = await fetch(`${API_URL}/api/users/${userId}`, {
    method: 'GET',
    headers: { 'X-User-Id': actorUserId },
  });
  return response.json();
};

// PUT /api/users/<user_id>
export const updateUser = async (userId: string, actorUserId: string, data: Partial<User>): Promise<ApiResponse> => {
  const response = await fetch(`${API_URL}/api/users/${userId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      'X-User-Id': actorUserId,
    },
    body: JSON.stringify(data),
  });
  return response.json();
};

// DELETE /api/users/<user_id>
export const deleteUser = async (userId: string, actorUserId: string): Promise<ApiResponse> => {
  const response = await fetch(`${API_URL}/api/users/${userId}`, {
    method: 'DELETE',
    headers: { 'X-User-Id': actorUserId },
  });
  return response.json();
};

// DELETE /api/user_images/<image_id>
export const deleteImage = async (imageId: string, actorUserId: string): Promise<ApiResponse> => {
  const response = await fetch(`${API_URL}/api/user_images/${imageId}`, {
    method: 'DELETE',
    headers: { 'X-User-Id': actorUserId },
  });
  return response.json();
};
