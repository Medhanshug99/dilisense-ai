import express, { Request, Response, NextFunction } from 'express';
import multer from 'multer';
import { config } from './config';
import { documentsRouter } from './routes/documents';
import { closeQueue } from './queue/producer';

const app = express();

// Multer: stage uploaded PDFs to /tmp, then we rename to storage/raw
const upload = multer({
  dest: '/tmp/dilisense-uploads',
  limits: { fileSize: 100 * 1024 * 1024 },
  fileFilter: (_req, file, cb) => {
    if (file.mimetype === 'application/pdf') {
      cb(null, true);
    } else {
      cb(new Error('Only PDF files are accepted'));
    }
  },
});

app.use(express.json());
app.use(upload.single('file'));
app.use('/documents', documentsRouter);

app.get('/health', (_req, res) => res.json({ status: 'ok' }));

app.use((err: Error, _req: Request, res: Response, _next: NextFunction) => {
  console.error(err);
  res.status(500).json({ error: err.message });
});

process.on('SIGTERM', async () => {
  console.log('SIGTERM received, closing connections...');
  await closeQueue();
  process.exit(0);
});

app.listen(config.port, '0.0.0.0', () => {
  console.log(`[API] Listening on 0.0.0.0:${config.port}`);
});

export default app;
