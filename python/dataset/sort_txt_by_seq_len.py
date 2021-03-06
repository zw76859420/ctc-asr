"""
Sort a train.txt like file by its audio files sequence length.
"""

import os
import sys

from multiprocessing import Pool, Lock, cpu_count
from tqdm import tqdm

from python.util import storage
from python.load_sample import load_sample
from python.util.matplotlib_helper import pyplot_display
from python.dataset.config import CORPUS_DIR, TXT_DIR


def sort_txt_by_seq_len(txt_path, num_buckets=64, max_length=1700):
    """Sort a train.txt like file by it's audio files sequence length.
    Additionally outputs longer than `max_length` are being discarded from the given TXT file.
    Also it prints out optimal bucket sizes after computation.

    Args:
        txt_path (str): Path to the `train.txt`.
        num_buckets (int): Number ob buckets to split the input into.
        max_length (int): Positive integer. Max length for a feature vector to keep.
            Set to `0` to keep everything.

    Returns:
        Tuple[List[int], float]: A tuple containing the boundary array and the total corpus length
        in seconds.
    """
    # Read train.txt file.
    with open(txt_path, 'r') as f:
        lines = f.readlines()

        # Setup thread pool.
        lock = Lock()
        buffer = []   # Output buffer.

        with Pool(processes=cpu_count()) as pool:
            for result in tqdm(pool.imap_unordered(_feature_length, lines, chunksize=4),
                               desc='Reading audio samples', total=len(lines), file=sys.stdout,
                               unit='samples', dynamic_ncols=True):
                lock.acquire()
                buffer.append(result)
                lock.release()

        # Sort by sequence length.
        buffer = sorted(buffer, key=lambda x: x[0])

        # Remove samples longer than `max_length` points.
        if max_length > 0:
            original_length = len(buffer)
            buffer = [s for s in buffer if s[0] < max_length]
            print('Removed {:,d} samples from training.'.format(original_length - len(buffer)))

        # Calculate optimal bucket sizes.
        lengths = [l[0] for l in buffer]
        step = len(lengths) // num_buckets
        buckets = set()
        for i in range(step, len(lengths), step):
            buckets.add(lengths[i])
        buckets = list(buckets)
        buckets.sort()
        print('Suggested buckets: ', buckets)

        # Plot histogram of feature vector length distribution.
        _plot_sequence_lengths(lengths)

        # Determine total corpus length in seconds.
        total_length = sum(map(lambda x: x[0], buffer)) / 0.1

        # Remove sequence length.
        buffer = ['{} {}'.format(p, l) for _, p, l in buffer]

    # Write back to file.
    storage.delete_file_if_exists(txt_path)
    with open(txt_path, 'w') as f:
        f.writelines(buffer)

    with open(txt_path, 'r') as f:
        print('Successfully sorted {} lines of {}'.format(len(f.readlines()), txt_path))

    return buckets[: -1], total_length


def _feature_length(line):
    # Python multiprocessing helper method.
    wav_path, label = line.split(' ', 1)
    length = int(load_sample(os.path.join(CORPUS_DIR, wav_path))[1])
    return length, wav_path, label


@pyplot_display
def _plot_sequence_lengths(plt, lengths):
    # Plot histogram of feature vector length distribution.
    fig = plt.figure()
    plt.hist(lengths, bins=50, facecolor='green', alpha=0.75, edgecolor='black', linewidth=0.9)
    plt.title('Sequence Length\'s Histogram')
    plt.ylabel('Count')
    plt.xlabel('Length')
    plt.grid(True)

    return fig


if __name__ == '__main__':
    # Path to `train.txt` file.
    _txt_path = os.path.join(TXT_DIR, 'train.txt')

    # Display dataset stats.
    sort_txt_by_seq_len(_txt_path)
