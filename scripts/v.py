import os, sys, json
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from core.indexer.embedder import Embedder
from utils.file_helper import load_config

config = load_config('config/config.yaml')
model_name = config.get('embedding', {}).get('model_name', 'BAAI/bge-m3')

with open('data/chunks/all_chunks.json', 'r', encoding='utf-8') as f:
    all_chunks = json.load(f)

print(f'Total chunks: {len(all_chunks)}')
print(f'Model: {model_name}')

embedder = Embedder(model_name=model_name, device='cpu')
print(f'Dimension: {embedder.dimension}')

batch_size = 500
total_batches = (len(all_chunks) + batch_size - 1) // batch_size
print(f'Batch size: {batch_size}, Total batches: {total_batches}')

temp_dir = 'data/.tmp_vectors'
os.makedirs(temp_dir, exist_ok=True)

completed_batches = []
for f in os.listdir(temp_dir):
    if f.startswith('batch_') and f.endswith('.npy'):
        batch_idx = int(f.split('_')[1].split('.')[0])
        completed_batches.append(batch_idx)

if completed_batches:
    start_batch = max(completed_batches) + 1
    print(f'Resuming from batch {start_batch} ({len(completed_batches)} completed)')
else:
    start_batch = 0
    print('Starting from scratch')

for batch_idx in range(start_batch, total_batches):
    start_idx = batch_idx * batch_size
    end_idx = min((batch_idx + 1) * batch_size, len(all_chunks))
    print(f'\nBatch {batch_idx+1}/{total_batches} ({start_idx}-{end_idx})')
    
    texts = [c['text'] for c in all_chunks[start_idx:end_idx]]
    vectors = embedder.encode(texts, show_progress=True)
    
    np.save(f'{temp_dir}/batch_{batch_idx}.npy', vectors)
    with open(f'{temp_dir}/batch_{batch_idx}_ids.txt', 'w', encoding='utf-8') as f:
        for c in all_chunks[start_idx:end_idx]:
            f.write(c['id'] + '\n')
    print(f'Batch {batch_idx} saved')

print('\nMerging all batches...')
all_vectors = []
all_ids = []
for batch_idx in range(total_batches):
    vectors = np.load(f'{temp_dir}/batch_{batch_idx}.npy')
    all_vectors.append(vectors)
    with open(f'{temp_dir}/batch_{batch_idx}_ids.txt', 'r', encoding='utf-8') as f:
        all_ids.extend([line.strip() for line in f])

all_vectors = np.vstack(all_vectors)
print(f'Merged: {len(all_ids)} vectors')

from core.indexer.vector_store import VectorStore
vs = VectorStore(dimension=embedder.dimension)
vs.add_vectors(all_vectors, all_ids)
vs.save('data/vector_store/faiss_index')
print('FAISS index saved')

doc_store = {c['id']: c for c in all_chunks}
with open('data/vector_store/doc_store.json', 'w', encoding='utf-8') as f:
    json.dump(doc_store, f, ensure_ascii=False)
print('doc_store saved')

import shutil
shutil.rmtree(temp_dir)
print('Done!')
