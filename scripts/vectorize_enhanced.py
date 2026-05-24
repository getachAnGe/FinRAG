import os, sys, json
import numpy as np
import tempfile
import shutil

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from core.indexer.embedder import Embedder

print('Loading enhanced chunks...')
with open('data/chunks/all_chunks_enhanced.json', 'r', encoding='utf-8') as f:
    all_chunks = json.load(f)

print(f'Total chunks: {len(all_chunks)}')

model_name = 'BAAI/bge-m3'
embedder = Embedder(model_name=model_name, device='cpu')
print(f'Model: {model_name}, Dimension: {embedder.dimension}')

batch_size = 500
total_batches = (len(all_chunks) + batch_size - 1) // batch_size
print(f'Batch size: {batch_size}, Total batches: {total_batches}')

temp_dir = 'data/.tmp_vectors_enhanced'
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
print(f'Merged: {len(all_ids)} vectors, shape: {all_vectors.shape}')

from core.retriever.vector_search import VectorRetriever
vs = VectorRetriever(dimension=all_vectors.shape[1])
vs.add_documents(all_ids, all_vectors, all_chunks)

tmp_file = os.path.join(tempfile.gettempdir(), "faiss_enhanced_tmp.index")
vs.index_path = tmp_file
vs.save(tmp_file)
shutil.move(tmp_file + ".index", 'data/vector_store/faiss_index.index')
shutil.move(tmp_file + ".ids", 'data/vector_store/faiss_index.ids')
shutil.move(tmp_file + ".store.json", 'data/vector_store/faiss_index.store.json')

doc_store = {c['id']: c for c in all_chunks}
with open('data/vector_store/doc_store.json', 'w', encoding='utf-8') as f:
    json.dump(doc_store, f, ensure_ascii=False)

shutil.rmtree(temp_dir)
print('Done!')
