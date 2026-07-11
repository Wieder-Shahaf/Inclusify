const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface ContactMessageParams {
  subject: string;
  message: string;
  token: string;
  pdfBlob?: Blob;
}

// Sender identity (name/email/institution) is derived server-side from the
// authenticated user — auth is required, guests are rejected with 401.
export async function sendContactMessage(params: ContactMessageParams): Promise<void> {
  const formData = new FormData();
  formData.append('subject', params.subject);
  formData.append('message', params.message);
  if (params.pdfBlob) {
    formData.append('pdf_attachment', params.pdfBlob, 'analysis_report.pdf');
  }
  const response = await fetch(`${API_BASE_URL}/api/v1/contact`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${params.token}` },
    body: formData,
  });
  if (!response.ok) {
    throw new Error(`Contact failed: ${response.status}`);
  }
}
