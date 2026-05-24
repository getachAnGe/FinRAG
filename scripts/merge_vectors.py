import os, sys, json, tempfile, shutil
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.retriever.vector_search import VectorRetriever

with open('data/chunks/all_chunks.json', 'r', encoding='utf-8') as f:
    all_chunks = json.load(f)
print(f'Chunks: {len(all_chunks)}')

temp_dir = 'data/.tmp_vectors_new'
total_batches = 57
for i in range(total_batches):
    if not os.path.exists(f'{temp_dir}/batch_{i}.npy'):
        print(f'Missing batch {i}')
        exit(1)
print('All 57 batches present, merging...')

all_vectors = []
all_ids = []
for batch_idx in range(total_batches):
    all_vectors.append(np.load(f'{temp_dir}/batch_{batch_idx}.npy'))
    with open(f'{temp_dir}/batch_{batch_idx}_ids.txt', 'r', encoding='utf-8') as f:
        all_ids.extend([line.strip() for line in f])

all_vectors = np.vstack(all_vectors)
print(f'Merged: {len(all_ids)} vectors, shape: {all_vectors.shape}')

vs = VectorRetriever(dimension=all_vectors.shape[1])
vs.add_documents(all_ids, all_vectors, all_chunks)

tmp_base = os.path.join(tempfile.gettempdir(), 'faiss_new_tmp')
vs.save(tmp_base)

vector_dir = 'data/vector_store'
# Only move files that exist
for ext in ['.index', '.store.json']:
    src = tmp_base + ext
    dst = os.path.join(vector_dir, f'faiss_index{ext}')
    if os.path.exists(dst):
        os.remove(dst)
    shutil.move(src, dst)

# Also save faiss_index.store.json for backwards compat
shutil.copy(os.path.join(vector_dir, 'faiss_index.store.json'),
            os.path.join(vector_dir, 'faiss_index.store_copy.json'))

doc_store = {c['id']: c for c in all_chunks}
with open(os.path.join(vector_dir, 'doc_store.json'), 'w', encoding='utf-8') as f:
    json.dump(doc_store, f, ensure_ascii=False)

shutil.rmtree(temp_dir)
print('Done!')
for f in ['faiss_index.index', 'faiss_index.store.json', 'doc_store.json', 'bm25_index.bm25.json']:
    p = os.path.join(vector_dir, f)
    if os.path.exists(p):
        print(f'  {f}: {os.path.getsize(p)/1024/1024:.1f}MB')
