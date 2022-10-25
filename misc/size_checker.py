import os
import sys


old_folder = sys.argv[1]
new_folder = sys.argv[2]
assert new_folder != old_folder
old_files = sorted(os.listdir(old_folder))
new_files = sorted(os.listdir(new_folder))
print(f'Old: {old_folder} ({len(old_files)} files)')
print(f'New: {new_folder} ({len(new_files)} files)')
assert new_files == old_files

for file in old_files:
    old_size = os.path.getsize(os.path.join(old_folder, file))
    new_size = os.path.getsize(os.path.join(new_folder, file))
    assert new_size <= old_size, f'{file} grew from {old_size:,} to {new_size:,}'

print(f'All {len(old_files)} files are equal or smaller.')
