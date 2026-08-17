"""Non-destructive LittleFS validation for the MRAM mounted at /mram.

The quick tests only use /mram/.mram_test/quick.  Persistence data uses
/mram/.mram_test/persistence.* so it survives quick-test cleanup.

Run this file normally for the quick test suite.  For reset persistence:

    prepare_persistence()
    # Perform a soft reset, hardware reset, or power cycle.
    # Run this file again, then call:
    verify_persistence()

Call verify_persistence(cleanup=True) after the final persistence check if the
test files are no longer needed.
"""

import os
import sys
import time


MOUNT_POINT = "/mram"
TEST_ROOT = MOUNT_POINT + "/.mram_test"
QUICK_DIR = TEST_ROOT + "/quick"
LAST_FAILURE = TEST_ROOT + "/last_failure.txt"

EXPECTED_BLOCK_COUNT = 512
EXPECTED_BLOCK_SIZE = 128
EXPECTED_CAPACITY = 64 * 1024
MAX_CLEANUP_BLOCK_DELTA = 8

PERSIST_DATA = TEST_ROOT + "/persistence.bin"
PERSIST_META = TEST_ROOT + "/persistence.meta"
PERSIST_SEED = 0x6D
PERSIST_SIZE = 8193


def _assert(condition, message):
    if not condition:
        raise AssertionError(message)


def _sync():
    # VfsLfs2 commits file data when the file is flushed or closed.  Some
    # MicroPython ports also expose os.sync(), so use it only when available.
    sync = getattr(os, "sync", None)
    if sync is not None:
        sync()


def _ensure_dir(path):
    try:
        os.mkdir(path)
    except OSError:
        # Do not hide errors such as an existing regular file at this path.
        os.listdir(path)


def _remove_tree(path):
    try:
        names = os.listdir(path)
    except OSError:
        try:
            os.remove(path)
        except OSError:
            pass
        return

    for name in names:
        child = path + "/" + name
        try:
            os.remove(child)
        except OSError:
            _remove_tree(child)
    os.rmdir(path)


def _pattern(size, seed):
    data = bytearray(size)
    value = seed & 0xFF
    for index in range(size):
        # A deterministic, non-uniform pattern that changes with byte offset.
        value = (value * 33 + index * 17 + 0x5B) & 0xFF
        data[index] = value ^ ((index >> 3) & 0xFF)
    return data


def _fnv1a(data):
    value = 0x811C9DC5
    for byte in data:
        value ^= byte
        value = (value * 0x01000193) & 0xFFFFFFFF
    return value


def _read_all(path):
    with open(path, "rb") as file:
        return file.read()


def _check_file(path, expected):
    actual = _read_all(path)
    _assert(len(actual) == len(expected), "%s: length %d != %d" % (path, len(actual), len(expected)))
    _assert(actual == expected, "%s: content mismatch, got 0x%08x expected 0x%08x" % (path, _fnv1a(actual), _fnv1a(expected)))


def _save_failure(case_name, error):
    try:
        with open(LAST_FAILURE, "w") as file:
            file.write("case=%s\n" % case_name)
            file.write("exception=%r\n" % error)
            sys.print_exception(error, file)
    except Exception:
        # Preserve the original test failure if recording the diagnostic fails.
        pass


def _free_blocks():
    info = os.statvfs(MOUNT_POINT)
    return info[3]


def _test_geometry():
    info = os.statvfs(MOUNT_POINT)
    block_size = info[0]
    fragment_size = info[1]
    block_count = info[2]
    free_blocks = info[3]

    print("  geometry: block_size=%d fragment_size=%d blocks=%d free=%d" % (block_size, fragment_size, block_count, free_blocks))
    _assert(block_size == EXPECTED_BLOCK_SIZE, "unexpected block size: %d" % block_size)
    _assert(fragment_size == EXPECTED_BLOCK_SIZE, "unexpected fragment size: %d" % fragment_size)
    _assert(block_count == EXPECTED_BLOCK_COUNT, "unexpected block count: %d" % block_count)
    _assert(block_size * block_count == EXPECTED_CAPACITY, "unexpected capacity: %d" % (block_size * block_count))
    _assert(0 < free_blocks < block_count, "invalid free block count: %d" % free_blocks)


def _test_boundary_lengths():
    path = QUICK_DIR + "/boundary.bin"
    lengths = (0, 1, 31, 32, 33, 127, 128, 129, 255, 256, 257, 511, 512, 513, 4095, 4096, 4097)

    for size in lengths:
        expected = _pattern(size, size ^ 0xA5)
        with open(path, "wb") as file:
            file.write(expected)
        _sync()
        _check_file(path, expected)
        os.remove(path)

    print("  boundary lengths:", lengths)


def _test_seek_overwrite_append():
    path = QUICK_DIR + "/seek.bin"
    expected = _pattern(2048, 0x31)

    with open(path, "wb") as file:
        file.write(expected)

    patches = (
        (0, 1, 0x10),
        (31, 3, 0x20),
        (127, 5, 0x30),
        (128, 33, 0x40),
        (255, 129, 0x50),
        (1000, 257, 0x60),
        (2015, 33, 0x70),
    )

    with open(path, "r+b") as file:
        for offset, size, seed in patches:
            patch = _pattern(size, seed)
            file.seek(offset)
            written = file.write(patch)
            _assert(written == size, "short overwrite at offset %d" % offset)
            expected[offset:offset + size] = patch

    appended = _pattern(257, 0xA7)
    with open(path, "ab") as file:
        written = file.write(appended)
        _assert(written == len(appended), "short append")
    expected.extend(appended)

    _sync()
    _check_file(path, expected)

    with open(path, "rb") as file:
        file.seek(127)
        actual = file.read(258)
    _assert(actual == expected[127:385], "seek/read boundary mismatch")


def _test_directories_and_rename():
    level1 = QUICK_DIR + "/dir_a"
    level2 = level1 + "/dir_b"
    _ensure_dir(level1)
    _ensure_dir(level2)

    source = level2 + "/source.bin"
    renamed = level2 + "/renamed.bin"
    expected = _pattern(333, 0x44)
    with open(source, "wb") as file:
        file.write(expected)
    os.rename(source, renamed)
    _check_file(renamed, expected)

    # With a 128-byte LittleFS metadata block, a single directory entry must
    # be small enough to survive metadata compaction/splitting.  A 100-byte
    # name can legitimately fail with ENAMETOOLONG even though LFS2_NAME_MAX
    # is 255, so use a 48-byte name for this device-health test.
    long_name = "n" * 44 + ".bin"
    long_path = level2 + "/" + long_name
    long_data = _pattern(129, 0x55)
    with open(long_path, "wb") as file:
        file.write(long_data)
    _check_file(long_path, long_data)

    names = os.listdir(level2)
    _assert("source.bin" not in names, "rename left the source entry")
    _assert("renamed.bin" in names, "renamed file is missing")
    _assert(long_name in names, "long filename is missing")
    print("  long filename length:", len(long_name))
    _sync()


def _test_many_small_files_and_reclaim():
    directory = QUICK_DIR + "/small"
    _ensure_dir(directory)
    count = 48

    for index in range(count):
        size = 1 + (index * 37) % 191
        data = _pattern(size, index + 1)
        with open(directory + "/f%03d.bin" % index, "wb") as file:
            file.write(data)
    _sync()

    for index in range(count):
        size = 1 + (index * 37) % 191
        _check_file(directory + "/f%03d.bin" % index, _pattern(size, index + 1))

    free_before_delete = _free_blocks()
    for index in range(0, count, 2):
        os.remove(directory + "/f%03d.bin" % index)
    _sync()
    free_after_delete = _free_blocks()

    for index in range(0, count, 2):
        data = _pattern(97 + index, 0x80 + index)
        with open(directory + "/r%03d.bin" % index, "wb") as file:
            file.write(data)
    _sync()

    for index in range(0, count, 2):
        _check_file(directory + "/r%03d.bin" % index, _pattern(97 + index, 0x80 + index))

    print("  small files: %d, free before delete=%d after delete=%d" % (count, free_before_delete, free_after_delete))


def _test_repeated_rewrite():
    path = QUICK_DIR + "/rewrite.bin"
    cycles = 16

    for cycle in range(cycles):
        size = 1024 + (cycle * 73) % 1024
        expected = _pattern(size, cycle ^ 0xC3)
        with open(path, "wb") as file:
            split = 1 + (cycle * 29) % 257
            offset = 0
            while offset < size:
                end = min(offset + split, size)
                written = file.write(expected[offset:end])
                _assert(written == end - offset, "short rewrite in cycle %d" % cycle)
                offset = end
        _sync()
        _check_file(path, expected)

    print("  rewrite cycles:", cycles)


def _run_case(name, function):
    start = time.ticks_ms()
    print("[RUN ]", name)
    try:
        function()
    except Exception as error:
        elapsed = time.ticks_diff(time.ticks_ms(), start)
        _save_failure(name, error)
        print("[FAIL]", name)
        print("  elapsed_ms:", elapsed)
        print("  exception:", repr(error))
        print("  details:", LAST_FAILURE)
        raise
    elapsed = time.ticks_diff(time.ticks_ms(), start)
    print("[PASS] %s (%d ms)" % (name, elapsed))


def run_quick_tests():
    print("=== MRAM LittleFS quick test ===")
    print("mount:", MOUNT_POINT)
    os.listdir(MOUNT_POINT)

    _ensure_dir(TEST_ROOT)
    try:
        os.remove(LAST_FAILURE)
    except OSError:
        pass
    _remove_tree(QUICK_DIR)
    _ensure_dir(QUICK_DIR)

    free_before = _free_blocks()
    try:
        _run_case("geometry", _test_geometry)
        _run_case("boundary lengths", _test_boundary_lengths)
        _run_case("seek/overwrite/append", _test_seek_overwrite_append)
        _run_case("directories/rename/long name", _test_directories_and_rename)
        _run_case("many small files/reclaim", _test_many_small_files_and_reclaim)
        _run_case("repeated rewrite", _test_repeated_rewrite)
    except Exception:
        print("Quick-test artifacts kept at", QUICK_DIR)
        raise

    _remove_tree(QUICK_DIR)
    _sync()
    free_after = _free_blocks()

    print("free blocks: before=%d after_cleanup=%d" % (free_before, free_after))
    _assert(free_after + MAX_CLEANUP_BLOCK_DELTA >= free_before,
        "cleanup lost too many blocks: before=%d after=%d" % (free_before, free_after))
    print("=== MRAM QUICK TEST PASS ===")
    print("For reset persistence, call prepare_persistence(), reset the board,")
    print("run this file again, then call verify_persistence().")


def prepare_persistence():
    print("=== Prepare MRAM persistence test ===")
    os.listdir(MOUNT_POINT)
    _ensure_dir(TEST_ROOT)

    for path in (PERSIST_DATA, PERSIST_META):
        try:
            os.remove(path)
        except OSError:
            pass

    expected = _pattern(PERSIST_SIZE, PERSIST_SEED)
    chunk_sizes = (1, 31, 32, 33, 127, 128, 129, 257, 511)
    with open(PERSIST_DATA, "wb") as file:
        offset = 0
        chunk_index = 0
        while offset < len(expected):
            size = chunk_sizes[chunk_index % len(chunk_sizes)]
            end = min(offset + size, len(expected))
            written = file.write(expected[offset:end])
            _assert(written == end - offset, "short persistence write")
            offset = end
            chunk_index += 1

    checksum = _fnv1a(expected)
    with open(PERSIST_META, "w") as file:
        file.write("%d %08x\n" % (len(expected), checksum))

    _sync()
    _check_file(PERSIST_DATA, expected)
    print("prepared: size=%d fnv1a=%08x" % (len(expected), checksum))
    print("Now perform a soft reset, hardware reset, or power cycle.")
    print("After reconnecting, run this file and call verify_persistence().")


def verify_persistence(cleanup=False):
    print("=== Verify MRAM persistence test ===")
    expected = _pattern(PERSIST_SIZE, PERSIST_SEED)
    expected_checksum = _fnv1a(expected)

    with open(PERSIST_META, "r") as file:
        fields = file.read().strip().split()
    _assert(len(fields) == 2, "invalid persistence metadata")
    recorded_size = int(fields[0])
    recorded_checksum = int(fields[1], 16)

    _assert(recorded_size == len(expected), "recorded persistence size mismatch")
    _assert(recorded_checksum == expected_checksum, "recorded persistence checksum mismatch")
    _check_file(PERSIST_DATA, expected)

    print("verified: size=%d fnv1a=%08x" % (recorded_size, recorded_checksum))
    print("=== MRAM PERSISTENCE TEST PASS ===")

    if cleanup:
        os.remove(PERSIST_DATA)
        os.remove(PERSIST_META)
        _sync()
        print("persistence test files removed")


if __name__ == "__main__":
    run_quick_tests()
    # prepare_persistence()
    # verify_persistence(True)
    pass
