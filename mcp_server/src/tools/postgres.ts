/**
 * PostgreSQL database tools
 */
import { Pool } from 'pg';

const pool = new Pool({
  connectionString: process.env.DATABASE_URL || 'postgresql://user:pass@localhost:5432/docguard',
  max: 10,
});

/**
 * PostgreSQL operations
 */
export const postgresTools = {
  /**
   * Execute SQL query
   */
  async query(sql: string, params: Record<string, any> = {}): Promise<{ rows: any[]; rowCount: number }> {
    const client = await pool.connect();

    try {
      // Convert named parameters to positional if needed
      const result = await client.query(sql, Object.values(params));

      return {
        rows: result.rows,
        rowCount: result.rowCount || 0,
      };
    } catch (error) {
      throw new Error(`Database query failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      client.release();
    }
  },
};
