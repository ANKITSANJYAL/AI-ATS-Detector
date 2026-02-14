/**
 * Filesystem tools for reading and writing files
 */
import { promises as fs } from 'fs';
import path from 'path';

/**
 * Filesystem operations
 */
export const filesystemTools = {
  /**
   * Read file contents
   */
  async read(filePath: string): Promise<{ content: string; path: string }> {
    try {
      const absolutePath = path.resolve(filePath);
      const content = await fs.readFile(absolutePath, 'utf-8');

      return {
        content,
        path: absolutePath,
      };
    } catch (error) {
      throw new Error(`Failed to read file: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  },

  /**
   * Write content to file
   */
  async write(filePath: string, content: string): Promise<{ path: string; bytes: number }> {
    try {
      const absolutePath = path.resolve(filePath);
      await fs.writeFile(absolutePath, content, 'utf-8');
      const stats = await fs.stat(absolutePath);

      return {
        path: absolutePath,
        bytes: stats.size,
      };
    } catch (error) {
      throw new Error(`Failed to write file: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  },
};
