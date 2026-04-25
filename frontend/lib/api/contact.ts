const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface ContactMessageParams {
  subject: string;
  message: string;
  senderName: string;
  senderEmail: string;
  senderInstitution: string;
  pdfBlob?: Blob;
}

export async function sendContactMessage(params: ContactMessageParams): Promise<void> {
  const formData = new FormData();
  formData.append('subject', params.subject);
  formData.append('message', params.message);
  formData.append('sender_name', params.senderName);
  formData.append('sender_email', params.senderEmail);
  formData.append('sender_institution', params.senderInstitution);
  if (params.pdfBlob) {
    formData.append('pdf_attachment', params.pdfBlob, 'analysis_report.pdf');
  }
  const response = await fetch(`${API_BASE_URL}/api/v1/contact`, {
    method: 'POST',
    body: formData,
  });
  if (!response.ok) {
    throw new Error(`Contact failed: ${response.status}`);
  }
}
