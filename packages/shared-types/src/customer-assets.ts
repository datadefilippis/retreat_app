/**
 * Customer-portal "asset" surfaces — Track E Step 2.4.6
 *
 * Lightweight views per il widget Lit customer-portal del widget embed:
 *   - Downloads (digital products acquistati)
 *   - Bookings (service products con slot riservato)
 *   - Reservations (rental products con date)
 *   - Courses (videocorsi con progress) — Release 4 R-4 already implemented
 *
 * Mirror dei modelli Pydantic IssuedDownload / IssuedBooking /
 * IssuedReservation (backend/models/issued_*.py). Solo i campi safe-to-
 * expose nel customer portal (whitelist projection).
 *
 * Endpoint backend di provenienza:
 *   GET /api/customer/downloads
 *   GET /api/customer/bookings
 *   GET /api/customer/reservations
 *   GET /api/customer/courses   (already exists)
 */

// ── Downloads ────────────────────────────────────────────────────────

export interface CustomerDownload {
  id: string;
  code: string;
  order_id?: string | null;
  product_id: string;
  product_name: string;
  status?: string | null;     // "issued" | "downloaded" | "expired" | etc.
  access_token?: string | null;
  access_token_expires_at?: string | null;
  max_downloads?: number | null;
  downloads_count?: number;
  created_at?: string | null;
  expires_at?: string | null;
}

export interface CustomerDownloadsResponse {
  downloads: CustomerDownload[];
  total: number;
}

// ── Bookings (service products con slot) ─────────────────────────────

export interface CustomerBooking {
  id: string;
  code: string;
  order_id?: string | null;
  product_id: string;
  product_name: string;
  booking_date: string;            // YYYY-MM-DD
  booking_start_time?: string | null;  // HH:MM
  booking_end_time?: string | null;
  booking_end_date?: string | null;
  status?: string | null;          // "confirmed" | "pending" | "cancelled" | etc.
  service_option_id?: string | null;
  service_option_label?: string | null;
  location?: string | null;
  notes?: string | null;
  created_at?: string | null;
  /** Track E Step 5.2 — token per /api/public/bookings/{token}/ics download. */
  access_token?: string | null;
}

export interface CustomerBookingsResponse {
  bookings: CustomerBooking[];
  total: number;
}

// ── Reservations (rental products) ───────────────────────────────────

export interface CustomerReservation {
  id: string;
  code: string;
  order_id?: string | null;
  product_id: string;
  product_name: string;
  // Range flavor (date-only)
  rental_date_from?: string | null;
  rental_date_to?: string | null;
  // Slot flavor (date + time)
  booking_date?: string | null;
  booking_start_time?: string | null;
  booking_end_time?: string | null;
  booking_end_date?: string | null;
  status?: string | null;
  approval_status?: string | null; // "pending" | "approved" | "rejected"
  rental_notes?: string | null;
  created_at?: string | null;
  /** Track E Step 5.2 — token per /api/public/reservations/{token}/ics download. */
  access_token?: string | null;
}

export interface CustomerReservationsResponse {
  reservations: CustomerReservation[];
  total: number;
}

// ── Courses (videocorsi) ─────────────────────────────────────────────
// Esistente endpoint /api/customer/courses (Release 4 R-4).
// Shape mirror del Pydantic response.

export interface CustomerCourseSummary {
  /** Enrollment id (compound key con order line). */
  enrollment: {
    id: string;
    customer_account_id: string;
    course_id: string;
    order_id?: string | null;
    issued_at: string;
    expires_at?: string | null;
    revoked_at?: string | null;
  };
  /** Snapshot del corso al momento dell'enrollment. */
  course: {
    id: string;
    title: string;
    description?: string | null;
    cover_image_url?: string | null;
    lessons_count?: number | null;
    duration_seconds?: number | null;
    access_policy?: string | null;
  };
  progress_stats?: {
    lessons_completed: number;
    lessons_total: number;
    percent: number;
  };
}

export interface CustomerCoursesResponse {
  courses: CustomerCourseSummary[];
  total: number;
}

export interface CustomerCourseDetail {
  enrollment: CustomerCourseSummary['enrollment'];
  course: CustomerCourseSummary['course'] & {
    modules?: Array<{
      id: string;
      title: string;
      sort_order?: number;
      lessons: Array<{
        id: string;
        title: string;
        duration_seconds?: number;
        sort_order?: number;
        watched_seconds?: number;
        completed_at?: string | null;
      }>;
    }>;
  };
  progress?: Record<string, unknown>;
  progress_stats?: CustomerCourseSummary['progress_stats'];
}

export interface CustomerCoursePlayUrlResponse {
  play_url: string;
  expires_at: string;
  watermark_text?: string | null;
}

export interface CustomerCourseProgressUpdate {
  lesson_id: string;
  watched_seconds: number;
  completed?: boolean;
}
