import sys, traceback, os, json
sys.path.insert(0, r'C:\Users\Zwmar\.openclaw\workspace\projects\time')
from research_evolver.src.core.baseline_genome import get_baseline_genome
from research_evolver.src.execution.data_loader import load_train
from research_evolver.src.execution.trainer import train
from pathlib import Path

ROOT = Path(r'C:\Users\Zwmar\.openclaw\workspace\projects\time')
data_dir = ROOT / 'research_evolver' / 'data'
train_data = load_train(data_dir)
genome = get_baseline_genome()
out_dir = ROOT / 'test_train'

try:
    result = train(genome, train_data, out_dir, max_steps=2)
    with open(ROOT / 'train_result.json', 'w') as f:
        json.dump({'success': True, 'result': result}, f)
    print('SUCCESS:', result)
except Exception as e:
    err_file = ROOT / 'train_error.txt'
    with open(err_file, 'w') as f:
        f.write(str(e) + '\n')
        traceback.print_exc(file=f)
    print('ERROR:', e)
    sys.exit(1)
