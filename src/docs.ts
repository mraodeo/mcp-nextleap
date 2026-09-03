import { google } from 'googleapis';


/**
 * Appends content to a Google Doc.
 */
export async function appendToDoc(auth: any, documentId: string, content: string) {
  const docs = google.docs({ version: 'v1', auth });

  try {
    // 1. Get the document to find the end index
    const doc = await docs.documents.get({ documentId });
    const bodyElements = doc.data.body?.content;
    
    if (!bodyElements) {
      throw new Error('Document body is empty or inaccessible.');
    }

    // The end of the document is the end index of the last element, minus 1
    const lastElement = bodyElements[bodyElements.length - 1];
    const endIndex = lastElement.endIndex ? lastElement.endIndex - 1 : 1;

    // 2. Append the text at the end index
    const requests = [
      {
        insertText: {
          location: {
            index: endIndex,
          },
          text: '\n' + content,
        }
      }
    ];

    await docs.documents.batchUpdate({
      documentId,
      requestBody: {
        requests,
      }
    });

    return `Successfully appended content to Google Doc: ${documentId}`;
  } catch (error: any) {
    throw new Error(`Failed to append to Google Doc: ${error.message}`);
  }
}
