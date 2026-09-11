import { Request, Response, Router } from 'express';
import { pool } from '../db/pool';
import { enqueueIngestion } from '../queue/producer';
import { config } from '../config';
import path from 'path';
import fs from 'fs';
import crypto from 'crypto';

export const documentsRouter = Router();

documentsRouter.post('/upload', async (req, res) => {
  // @ts-ignore - multer sets req.file
  const file = req.file;
  if (!file) {
    res.status(400).json({ error: 'No PDF file provided (multipart field name: "file")' });
    return;
  }

  const documentId = crypto.randomUUID();
  const safeName = file.originalname.replace(/[^a-zA-Z0-9._-]/g, '_');
  const storagePath = path.join(config.storageDir, `${documentId}-${safeName}`);

  await fs.promises.mkdir(config.storageDir, { recursive: true });

  try {
    await fs.promises.rename(file.path, storagePath);
  } catch (e) {
    console.error('failed to move file:', e);
    res.status(500).json({ error: 'Failed to save file' });
    return;
  }

  await pool.query(
    `INSERT INTO documents (id, source_type, source_uri, title, status, created_at, updated_at)
     VALUES ($1, 'pdf', $2, $3, 'pending', NOW(), NOW())`,
    [documentId, `file://${storagePath}`, file.originalname]
  );

  await enqueueIngestion(documentId, storagePath);

  res.status(201).json({
    document_id: documentId,
    filename: file.originalname,
    storage_path: storagePath,
    status: 'pending',
  });
});

documentsRouter.get('/:id/status', async (req, res) => {
  const { id } = req.params;
  const result = await pool.query(
    'SELECT status, updated_at, error_msg FROM documents WHERE id = $1',
    [id]
  );
  if (result.rows.length === 0) {
    res.status(404).json({ error: 'Document not found' });
    return;
  }
  res.json({
    status: result.rows[0].status,
    updated_at: result.rows[0].updated_at,
    error_msg: result.rows[0].error_msg,
  });
});
