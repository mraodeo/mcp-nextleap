import { google } from 'googleapis';


/**
 * Encodes an email message into a base64url string.
 */
function createEmailBase64(to: string, subject: string, body: string): string {
  const messageParts = [
    `To: ${to}`,
    `Subject: ${subject}`,
    'MIME-Version: 1.0',
    'Content-Type: text/plain; charset="UTF-8"',
    '',
    body
  ];
  
  const message = messageParts.join('\n');
  return Buffer.from(message)
    .toString('base64')
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');
}

/**
 * Creates an email draft.
 */
export async function draftEmail(auth: any, to: string, subject: string, body: string) {
  const gmail = google.gmail({ version: 'v1', auth });
  const raw = createEmailBase64(to, subject, body);
  
  try {
    const res = await gmail.users.drafts.create({
      userId: 'me',
      requestBody: {
        message: {
          raw: raw
        }
      }
    });
    return `Draft created successfully. Draft ID: ${res.data.id}`;
  } catch (error: any) {
    throw new Error(`Failed to create draft: ${error.message}`);
  }
}

/**
 * Sends an email directly.
 */
export async function sendEmail(auth: any, to: string, subject: string, body: string) {
  const gmail = google.gmail({ version: 'v1', auth });
  const raw = createEmailBase64(to, subject, body);

  try {
    const res = await gmail.users.messages.send({
      userId: 'me',
      requestBody: {
        raw: raw
      }
    });
    return `Email sent successfully. Message ID: ${res.data.id}`;
  } catch (error: any) {
    throw new Error(`Failed to send email: ${error.message}`);
  }
}
