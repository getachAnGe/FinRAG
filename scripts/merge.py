import os, sys, json
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

print('Loading all chunks...')
with open('data/chunks/all_chunks.json', 'r', encoding='utf-8') as f:
    all_chunks = json.load(f)
print(f'Total chunks: {len(all_chunks)}')

temp_dir = 'data/.tmp_vectors'
total_batches = (len(all_chunks) + 499) // 500
print(f'Total batches: {total_batches}')

print('Merging all batches...')
all_vectors = []
all_ids = []
for batch_idx in range(total_batches):
    vectors = np.load(f'{temp_dir}/batch_{batch_idx}.npy')
    all_vectors.append(vectors)
    with open(f'{temp_dir}/batch_{batch_idx}_ids.txt', 'r', encoding='utf-8') as f:
        all_ids.extend([line.strip() for line in f])

all_vectors = np.vstack(all_vectors)
print(f'Merged: {len(all_ids)} vectors, shape: {all_vectors.shape}')

from core.retriever.vector_search import VectorRetriever
vs = VectorRetriever(dimension=all_vectors.shape[1])
vs.add_documents(all_ids, all_vectors, all_chunks)
vs.save('data/vector_store/faiss_index')
print('FAISS index saved')

doc_store = {c['id']: c for c in all_chunks}
with open('data/vector_store/doc_store.json', 'w', encoding='utf-8') as f:
    json.dump(doc_store, f, ensure_ascii=False)
print('doc_store saved')

import shutil
shutil.rmtree(temp_dir)
print('Temp dir cleaned')
print('Done!')
