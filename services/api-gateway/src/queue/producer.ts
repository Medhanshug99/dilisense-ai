import { Queue } from 'bullmq';
import { config } from '../config';

const redisOptions = {
  host: config.redis.host,
  port: config.redis.port,
  maxRetriesPerRequest: null,
};

// Producer: API gateway enqueues; Python ingestion-worker dequeues
export const ingestionQueue = new Queue<{ document_id: string; storage_path: string }>(
  config.queue.ingestion,
  { connection: redisOptions }
);

export async function enqueueIngestion(document_id: string, storage_path: string) {
  const job = await ingestionQueue.add('ingest', { document_id, storage_path });
  console.log(`[QUEUE] Enqueued job ${job.id} → document ${document_id} at ${storage_path}`);
}

export async function closeQueue() {
  await ingestionQueue.close();
  console.log('[QUEUE] Closed ingestion queue');
}
