export const config = {
  port: Number(process.env.PORT ?? 3000),
  storageDir: process.env.STORAGE_DIR ?? '/app/storage/raw',
  redis: {
    host: process.env.REDIS_HOST ?? 'redis',
    port: Number(process.env.REDIS_PORT ?? 6379),
    url: process.env.REDIS_URL ?? 'redis://redis:6379',
  },
  db: {
    host: process.env.DB_HOST ?? 'postgres',
    port: Number(process.env.DB_PORT ?? 5432),
    name: process.env.DB_NAME ?? 'diligence',
    user: process.env.DB_USER ?? 'diligence',
    password: process.env.DB_PASSWORD ?? 'diligence_secret',
  },
  queue: {
    ingestion: 'document-ingestion',
  },
} as const;