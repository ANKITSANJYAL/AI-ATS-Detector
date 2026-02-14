/**
 * Fetch tool for retrieving URL content
 */
import fetch from 'node-fetch';

/**
 * Fetch content from a URL
 */
export async function fetchTool(url: string): Promise<{ content: string; status: number }> {
  try {
    const response = await fetch(url);
    const content = await response.text();

    return {
      content,
      status: response.status,
    };
  } catch (error) {
    throw new Error(`Failed to fetch URL: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
}
