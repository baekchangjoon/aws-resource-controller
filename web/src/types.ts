export interface AddressResponse {
  address: string;
  expires_at: string;
}

export interface AttachmentSummary {
  aid: string;
  filename: string;
  size: number;
  content_type: string;
}

export interface MessageRow {
  id: string;
  from: string;
  subject: string;
  received_at: number;
  body_text: string;
  body_html_safe: string;
  attachments: AttachmentSummary[];
}

export interface ListMessagesResponse {
  items: MessageRow[];
  next_after: string | null;
}
