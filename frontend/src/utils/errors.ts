/**
 * Normalize FastAPI / axios errors into a single readable string.
 *
 * FastAPI 422 → { detail: [{ type, loc, msg, input, ctx }, ...] }
 * Our AppException → { detail: "Invalid email or password", error_code: "..." }
 * OAuth error → { error: "invalid_grant", error_description: "..." }
 */
export function extractErrorMessage(err: any, fallback = 'Something went wrong'): string {
  const data = err?.response?.data;
  if (!data) return err?.message || fallback;

  // OAuth-style error
  if (data.error_description) return data.error_description;
  if (data.error && typeof data.error === 'string' && !data.detail) return data.error;

  const detail = data.detail;
  if (!detail) return fallback;

  // Plain string detail (from our AppException)
  if (typeof detail === 'string') return detail;

  // Array of validation errors (FastAPI 422)
  if (Array.isArray(detail)) {
    return detail
      .map((e) => {
        const field = Array.isArray(e.loc) ? e.loc.slice(1).join('.') : '';
        return field ? `${field}: ${e.msg}` : e.msg;
      })
      .filter(Boolean)
      .join('; ');
  }

  // Some object — stringify safely
  if (typeof detail === 'object') {
    return detail.msg || JSON.stringify(detail);
  }

  return String(detail);
}
