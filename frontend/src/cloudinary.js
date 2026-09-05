/**
 * cloudinary.js  –  PMS Cloudinary Upload Utility
 * =================================================
 * Uses an UNSIGNED upload preset — the API secret never touches the frontend.
 * Only VITE_CLOUDINARY_CLOUD_NAME and VITE_CLOUDINARY_UPLOAD_PRESET are needed here.
 *
 * Setup (one-time, in Cloudinary dashboard):
 *   Settings → Upload → Upload presets → Add unsigned preset
 *   Name it: pms_uploads   (or whatever VITE_CLOUDINARY_UPLOAD_PRESET is set to)
 *
 * Folder layout on Cloudinary:
 *   pms/avatars/   – user profile images
 *   pms/batch/     – uploaded batch telemetry files
 *   pms/reports/   – exported prediction reports (JSON)
 */

const CLOUD_NAME    = import.meta.env.VITE_CLOUDINARY_CLOUD_NAME;
const UPLOAD_PRESET = import.meta.env.VITE_CLOUDINARY_UPLOAD_PRESET;

if (!CLOUD_NAME || !UPLOAD_PRESET) {
  console.warn(
    '[PMS Cloudinary] VITE_CLOUDINARY_CLOUD_NAME or VITE_CLOUDINARY_UPLOAD_PRESET is not set. ' +
    'File uploads will be disabled until these are configured in .env'
  );
}

/**
 * Upload any file (image, raw, auto) to Cloudinary.
 *
 * @param {File|Blob|string} file  – A File object, Blob, or base64 data URI
 * @param {object} options
 * @param {string} options.folder   – Cloudinary folder (e.g. 'pms/avatars')
 * @param {string} options.resourceType – 'image' | 'raw' | 'auto' (default: 'auto')
 * @param {string} options.filename – Optional public_id override
 * @param {function} options.onProgress – (percent: number) => void
 *
 * @returns {Promise<CloudinaryUploadResult>}
 *   { secure_url, public_id, resource_type, format, bytes, width?, height? }
 */
export async function uploadToCloudinary(file, {
  folder = 'pms',
  resourceType = 'auto',
  filename = null,
  onProgress = null,
} = {}) {
  if (!CLOUD_NAME || !UPLOAD_PRESET) {
    throw new Error(
      'Cloudinary is not configured. Set VITE_CLOUDINARY_CLOUD_NAME and ' +
      'VITE_CLOUDINARY_UPLOAD_PRESET in your .env file.'
    );
  }

  const formData = new FormData();
  formData.append('file', file);
  formData.append('upload_preset', UPLOAD_PRESET);
  formData.append('folder', folder);
  if (filename) formData.append('public_id', filename);

  const endpoint = `https://api.cloudinary.com/v1_1/${CLOUD_NAME}/${resourceType}/upload`;

  // Use XMLHttpRequest for progress tracking support
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', endpoint);

    if (onProgress) {
      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) {
          onProgress(Math.round((e.loaded / e.total) * 100));
        }
      });
    }

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        const data = JSON.parse(xhr.responseText);
        resolve(data);
      } else {
        let errMsg = `Cloudinary upload failed (HTTP ${xhr.status})`;
        try {
          const errData = JSON.parse(xhr.responseText);
          errMsg = errData.error?.message || errMsg;
        } catch {}
        reject(new Error(errMsg));
      }
    };

    xhr.onerror = () => reject(new Error('Network error during Cloudinary upload'));
    xhr.send(formData);
  });
}

/**
 * Upload a profile image (JPEG/PNG/WebP) to pms/avatars/
 * Returns the secure_url string.
 */
export async function uploadAvatar(file, userId, onProgress) {
  const result = await uploadToCloudinary(file, {
    folder: 'pms/avatars',
    resourceType: 'image',
    filename: `avatar_${userId}`,
    onProgress,
  });
  return result.secure_url;
}

/**
 * Upload a raw telemetry batch file (CSV/JSON/XLSX/Parquet) to pms/batch/
 * Returns { secure_url, public_id, original_filename, bytes }.
 */
export async function uploadBatchFile(file, onProgress) {
  const ts = Date.now();
  const result = await uploadToCloudinary(file, {
    folder: 'pms/batch',
    resourceType: 'raw',
    filename: `batch_${ts}_${file.name.replace(/[^a-zA-Z0-9._-]/g, '_')}`,
    onProgress,
  });
  return {
    secure_url: result.secure_url,
    public_id:  result.public_id,
    bytes:       result.bytes,
    format:      result.format,
  };
}

/**
 * Upload a prediction report JSON blob to pms/reports/
 * @param {object} reportData – The prediction result object
 * @param {string} predictionId – Used for the filename
 * Returns the secure_url string.
 */
export async function uploadPredictionReport(reportData, predictionId) {
  const json = JSON.stringify(reportData, null, 2);
  const blob = new Blob([json], { type: 'application/json' });
  const file = new File([blob], `report_${predictionId || Date.now()}.json`, { type: 'application/json' });

  const result = await uploadToCloudinary(file, {
    folder: 'pms/reports',
    resourceType: 'raw',
    filename: `report_${predictionId || Date.now()}`,
  });
  return result.secure_url;
}

/** Returns true if Cloudinary is configured (env vars present) */
export function isCloudinaryConfigured() {
  return Boolean(CLOUD_NAME && UPLOAD_PRESET);
}
