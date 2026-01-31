# Medication Management API Documentation

**Production Base URL:** `https://fyp2-production-2479.up.railway.app`

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Endpoints](#endpoints)
4. [Request/Response Examples](#requestresponse-examples)
5. [Error Handling](#error-handling)
6. [Frontend Implementation Guide](#frontend-implementation-guide)

---

## Overview

The Medication API allows users to manage their medications (create, read, update, delete). All endpoints require the user ID in the URL path. For write operations (POST, PUT, DELETE), you must also provide the `X-User-Id` header for security verification.

**Base URL:** `https://fyp2-production-2479.up.railway.app`

---

## Authentication

### X-User-Id Header

All write operations (CREATE, UPDATE, DELETE) require the `X-User-Id` header:

```
X-User-Id: {user_id}
```

This header verifies that the user making the request matches the user being modified (security check to prevent users from modifying other users' data).

**Example:**

```
X-User-Id: a3dc85bd-94e3-419b-89b9-5364e398649a
```

---

## Endpoints

### 1. GET - List All Medications

**Retrieve all medications for a specific user.**

**Endpoint:**

```
GET /api/users/{user_id}/medications
```

**Headers:**

```
Content-Type: application/json
```

**Path Parameters:**

- `user_id` (required): UUID of the user

**Request Body:** None

**Response (200 OK):**

```json
{
  "ok": true,
  "count": 2,
  "items": [
    {
      "id": "d30b345b-c2a4-491c-bcc5-b10347d0c3cf",
      "name": "aspirin",
      "dosage": null,
      "frequency": null,
      "time": null,
      "instructions": null,
      "created_at": "2026-01-06T21:52:47.997877+00:00",
      "updated_at": "2026-01-06T21:52:47.997877+00:00"
    },
    {
      "id": "6b387d3f-8715-46cc-9d63-225c26c3cbc7",
      "name": "panadaol",
      "dosage": null,
      "frequency": null,
      "time": null,
      "instructions": null,
      "created_at": "2026-01-06T21:52:47.997877+00:00",
      "updated_at": "2026-01-06T21:52:47.997877+00:00"
    }
  ]
}
```

**Error Response (500):**

```json
{
  "ok": false,
  "error": "db_error",
  "detail": "database connection failed"
}
```

---

### 2. POST - Create New Medication

**Add a new medication for a user.**

**Endpoint:**

```
POST /api/users/{user_id}/medications
```

**Headers:**

```
Content-Type: application/json
X-User-Id: {user_id}
```

**Path Parameters:**

- `user_id` (required): UUID of the user

**Request Body:**

```json
{
  "name": "ibuprofen",
  "dosage": "400mg",
  "frequency": "twice daily",
  "time": "morning, evening",
  "instructions": "take with food"
}
```

**Body Fields:**

- `name` (required): Medication name (string)
- `dosage` (optional): Dosage amount (string, e.g., "400mg")
- `frequency` (optional): How often to take (string, e.g., "twice daily")
- `time` (optional): When to take (string, e.g., "morning, evening")
- `instructions` (optional): Additional instructions (string)

**Response (201 Created):**

```json
{
  "ok": true,
  "medication": {
    "id": "eabf2abe-2677-4866-8be0-ef3ee64f5fdf",
    "user_id": "a3dc85bd-94e3-419b-89b9-5364e398649a",
    "name": "ibuprofen",
    "dosage": "400mg",
    "frequency": "twice daily",
    "time": "morning, evening",
    "instructions": "take with food",
    "created_at": "2026-01-07T22:25:09.916133+00:00",
    "updated_at": "2026-01-07T22:25:09.916133+00:00"
  }
}
```

**Error Responses:**

Missing medication name (400):

```json
{
  "ok": false,
  "error": "missing_name"
}
```

Forbidden - X-User-Id mismatch (403):

```json
{
  "ok": false,
  "error": "forbidden",
  "detail": "actor must match user_id"
}
```

Database error (500):

```json
{
  "ok": false,
  "error": "db_error",
  "detail": "duplicate key value..."
}
```

---

### 3. PUT - Update Medication

**Update an existing medication.**

**Endpoint:**

```
PUT /api/users/{user_id}/medications/{med_id}
```

**Headers:**

```
Content-Type: application/json
X-User-Id: {user_id}
```

**Path Parameters:**

- `user_id` (required): UUID of the user
- `med_id` (required): UUID of the medication to update

**Request Body (send only fields you want to update):**

```json
{
  "dosage": "600mg",
  "frequency": "three times daily"
}
```

**Allowed Fields to Update:**

- `name`
- `dosage`
- `frequency`
- `time`
- `instructions`

**Response (200 OK):**

```json
{
  "ok": true,
  "medication": {
    "id": "eabf2abe-2677-4866-8be0-ef3ee64f5fdf",
    "name": "ibuprofen",
    "dosage": "600mg",
    "frequency": "three times daily",
    "time": "morning, evening",
    "instructions": "take with food",
    "updated_at": "2026-01-07T22:25:21.903994+00:00"
  }
}
```

**Error Responses:**

Medication not found (404):

```json
{
  "ok": false,
  "error": "medication_missing"
}
```

No updates provided (400):

```json
{
  "ok": false,
  "error": "no_updates"
}
```

Forbidden - X-User-Id mismatch (403):

```json
{
  "ok": false,
  "error": "forbidden",
  "detail": "actor must match user_id"
}
```

---

### 4. DELETE - Remove Medication

**Delete a medication.**

**Endpoint:**

```
DELETE /api/users/{user_id}/medications/{med_id}
```

**Headers:**

```
X-User-Id: {user_id}
```

**Path Parameters:**

- `user_id` (required): UUID of the user
- `med_id` (required): UUID of the medication to delete

**Request Body:** None

**Response (200 OK):**

```json
{
  "ok": true
}
```

**Error Responses:**

Medication not found (404):

```json
{
  "ok": false,
  "error": "medication_missing"
}
```

Forbidden - X-User-Id mismatch (403):

```json
{
  "ok": false,
  "error": "forbidden",
  "detail": "actor must match user_id"
}
```

---

## Request/Response Examples

### JavaScript/Fetch API Examples

#### Get All Medications

```javascript
const userId = "a3dc85bd-94e3-419b-89b9-5364e398649a";

fetch(
  `https://fyp2-production-2479.up.railway.app/api/users/${userId}/medications`,
  {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  }
)
  .then((response) => response.json())
  .then((data) => {
    console.log("Medications:", data.items);
    console.log("Count:", data.count);
  })
  .catch((error) => console.error("Error:", error));
```

#### Create Medication

```javascript
const userId = "a3dc85bd-94e3-419b-89b9-5364e398649a";

const medicationData = {
  name: "ibuprofen",
  dosage: "400mg",
  frequency: "twice daily",
  time: "morning, evening",
  instructions: "take with food",
};

fetch(
  `https://fyp2-production-2479.up.railway.app/api/users/${userId}/medications`,
  {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-User-Id": userId,
    },
    body: JSON.stringify(medicationData),
  }
)
  .then((response) => response.json())
  .then((data) => {
    if (data.ok) {
      console.log("Medication created with ID:", data.medication.id);
    } else {
      console.error("Error:", data.error);
    }
  })
  .catch((error) => console.error("Error:", error));
```

#### Update Medication

```javascript
const userId = "a3dc85bd-94e3-419b-89b9-5364e398649a";
const medId = "eabf2abe-2677-4866-8be0-ef3ee64f5fdf";

const updates = {
  dosage: "600mg",
  frequency: "three times daily",
};

fetch(
  `https://fyp2-production-2479.up.railway.app/api/users/${userId}/medications/${medId}`,
  {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      "X-User-Id": userId,
    },
    body: JSON.stringify(updates),
  }
)
  .then((response) => response.json())
  .then((data) => {
    if (data.ok) {
      console.log("Medication updated:", data.medication);
    } else {
      console.error("Error:", data.error);
    }
  })
  .catch((error) => console.error("Error:", error));
```

#### Delete Medication

```javascript
const userId = "a3dc85bd-94e3-419b-89b9-5364e398649a";
const medId = "eabf2abe-2677-4866-8be0-ef3ee64f5fdf";

fetch(
  `https://fyp2-production-2479.up.railway.app/api/users/${userId}/medications/${medId}`,
  {
    method: "DELETE",
    headers: {
      "X-User-Id": userId,
    },
  }
)
  .then((response) => response.json())
  .then((data) => {
    if (data.ok) {
      console.log("Medication deleted successfully");
    } else {
      console.error("Error:", data.error);
    }
  })
  .catch((error) => console.error("Error:", error));
```

---

## Error Handling

### Common HTTP Status Codes

| Status | Meaning                       | Example                  |
| ------ | ----------------------------- | ------------------------ |
| 200    | OK - Request succeeded        | GET list, UPDATE success |
| 201    | Created - Resource created    | POST new medication      |
| 400    | Bad Request - Invalid input   | Missing required field   |
| 403    | Forbidden - Access denied     | X-User-Id doesn't match  |
| 404    | Not Found - Resource missing  | Medication doesn't exist |
| 500    | Server Error - Database issue | DB connection failed     |

### Error Response Format

All errors follow this format:

```json
{
  "ok": false,
  "error": "error_code",
  "detail": "Human-readable error message"
}
```

### How to Handle Errors in Frontend

```javascript
fetch(url, options)
  .then((response) => {
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  })
  .then((data) => {
    if (!data.ok) {
      // Handle API error
      console.error("API Error:", data.error, data.detail);
      // Show user-friendly message
      showError(`Failed: ${data.detail}`);
    } else {
      // Handle success
      console.log("Success:", data);
    }
  })
  .catch((error) => {
    // Handle network or parsing error
    console.error("Network Error:", error);
    showError("Unable to connect to server");
  });
```

---

## Frontend Implementation Guide

### Step 1: Setup API Service (TypeScript Example)

Create `lib/medicationApi.ts`:

```typescript
const BASE_URL = "https://fyp2-production-2479.up.railway.app";

interface Medication {
  id: string;
  name: string;
  dosage?: string;
  frequency?: string;
  time?: string;
  instructions?: string;
  created_at: string;
  updated_at: string;
}

interface ApiResponse {
  ok: boolean;
  error?: string;
  detail?: string;
}

interface MedicationResponse extends ApiResponse {
  medication?: Medication;
}

interface MedicationListResponse extends ApiResponse {
  count: number;
  items: Medication[];
}

export const medicationApi = {
  // Get all medications for a user
  async getMedications(userId: string): Promise<Medication[]> {
    const response = await fetch(
      `${BASE_URL}/api/users/${userId}/medications`,
      {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
        },
      }
    );
    const data: MedicationListResponse = await response.json();
    if (!data.ok) throw new Error(data.detail || data.error);
    return data.items;
  },

  // Create a new medication
  async createMedication(
    userId: string,
    medication: Partial<Medication>
  ): Promise<Medication> {
    const response = await fetch(
      `${BASE_URL}/api/users/${userId}/medications`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-User-Id": userId,
        },
        body: JSON.stringify(medication),
      }
    );
    const data: MedicationResponse = await response.json();
    if (!data.ok) throw new Error(data.detail || data.error);
    return data.medication!;
  },

  // Update a medication
  async updateMedication(
    userId: string,
    medId: string,
    updates: Partial<Medication>
  ): Promise<Medication> {
    const response = await fetch(
      `${BASE_URL}/api/users/${userId}/medications/${medId}`,
      {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          "X-User-Id": userId,
        },
        body: JSON.stringify(updates),
      }
    );
    const data: MedicationResponse = await response.json();
    if (!data.ok) throw new Error(data.detail || data.error);
    return data.medication!;
  },

  // Delete a medication
  async deleteMedication(userId: string, medId: string): Promise<void> {
    const response = await fetch(
      `${BASE_URL}/api/users/${userId}/medications/${medId}`,
      {
        method: "DELETE",
        headers: {
          "X-User-Id": userId,
        },
      }
    );
    const data: ApiResponse = await response.json();
    if (!data.ok) throw new Error(data.detail || data.error);
  },
};
```

### Step 2: Use in React Component

```typescript
import { useState, useEffect } from "react";
import { medicationApi } from "@/lib/medicationApi";

export function MedicationManager({ userId }: { userId: string }) {
  const [medications, setMedications] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Load medications on mount
  useEffect(() => {
    loadMedications();
  }, [userId]);

  const loadMedications = async () => {
    setLoading(true);
    try {
      const meds = await medicationApi.getMedications(userId);
      setMedications(meds);
      setError("");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleAdd = async (name: string, dosage: string) => {
    try {
      const newMed = await medicationApi.createMedication(userId, {
        name,
        dosage,
      });
      setMedications([...medications, newMed]);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleUpdate = async (medId: string, updates: any) => {
    try {
      const updated = await medicationApi.updateMedication(
        userId,
        medId,
        updates
      );
      setMedications(medications.map((m) => (m.id === medId ? updated : m)));
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDelete = async (medId: string) => {
    try {
      await medicationApi.deleteMedication(userId, medId);
      setMedications(medications.filter((m) => m.id !== medId));
    } catch (err) {
      setError(err.message);
    }
  };

  if (loading) return <div>Loading medications...</div>;
  if (error) return <div style={{ color: "red" }}>Error: {error}</div>;

  return (
    <div>
      <h2>Your Medications ({medications.length})</h2>
      {medications.map((med) => (
        <div key={med.id} style={{ padding: "10px", border: "1px solid #ccc" }}>
          <h3>{med.name}</h3>
          <p>Dosage: {med.dosage || "Not specified"}</p>
          <p>Frequency: {med.frequency || "Not specified"}</p>
          <button onClick={() => handleDelete(med.id)}>Delete</button>
        </div>
      ))}
    </div>
  );
}
```

---

## Testing the API

### Using curl (Command Line)

```bash
# Get medications
curl -X GET "https://fyp2-production-2479.up.railway.app/api/users/a3dc85bd-94e3-419b-89b9-5364e398649a/medications"

# Create medication
curl -X POST "https://fyp2-production-2479.up.railway.app/api/users/a3dc85bd-94e3-419b-89b9-5364e398649a/medications" \
  -H "Content-Type: application/json" \
  -H "X-User-Id: a3dc85bd-94e3-419b-89b9-5364e398649a" \
  -d '{"name":"aspirin","dosage":"500mg"}'

# Update medication
curl -X PUT "https://fyp2-production-2479.up.railway.app/api/users/a3dc85bd-94e3-419b-89b9-5364e398649a/medications/{med_id}" \
  -H "Content-Type: application/json" \
  -H "X-User-Id: a3dc85bd-94e3-419b-89b9-5364e398649a" \
  -d '{"dosage":"600mg"}'

# Delete medication
curl -X DELETE "https://fyp2-production-2479.up.railway.app/api/users/a3dc85bd-94e3-419b-89b9-5364e398649a/medications/{med_id}" \
  -H "X-User-Id: a3dc85bd-94e3-419b-89b9-5364e398649a"
```

---

## Summary Checklist

✅ Always include `X-User-Id` header for POST, PUT, DELETE operations
✅ Always include `Content-Type: application/json` for requests with a body
✅ The `user_id` in URL must match the `X-User-Id` header
✅ Check `data.ok` field to determine if request succeeded
✅ Handle error responses with `data.error` and `data.detail`
✅ Medication name is required when creating
✅ Optional fields (dosage, frequency, time, instructions) can be null or omitted

---

**Last Updated:** January 8, 2026  
**API Status:** ✅ Production Ready
