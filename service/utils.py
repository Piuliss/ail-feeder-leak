import os
import shutil
import string
import unicodedata

import magic
import patoolib

# Characters authorized in filenames
WHITELISTED_FILENAME_CHARS = f"-() {string.ascii_letters}{string.digits}"


def if_binary_move(file_full_path, unprocessed_dir):
    """
    Check if file is binary and move it to unprocessed folder
    Returns True if file was moved (binary), False if it's text
    """
    result = False
    try:
        mime = magic.Magic(mime=True)
        mimetype = mime.from_file(file_full_path)
        
        # Check if it's a binary application file (not text)
        if mimetype.rsplit('/', 1)[0] == "application":
            print(f"[BINARY] {os.path.basename(file_full_path)} ({mimetype}) -> moving to unprocessed")
            if os.path.exists(file_full_path):
                shutil.move(file_full_path, unprocessed_dir)
            result = True  # File was moved
        else:
            # It's text or other processable format
            print(f"[TEXT] {os.path.basename(file_full_path)} ({mimetype}) -> will process")
            result = False  # File stays for processing
    except Exception as e:
        print(f"[ERROR] Checking file type: {e}")
        result = False
    
    return result


def clean_filename(filename):
    """
    Render a valid filename for the feeder 
    """
    # Remove whitespaces
    cleaned_filename = filename.replace(' ', '-')
    # Keep only valid ascii chars
    cleaned_filename = unicodedata.normalize('NFKD', cleaned_filename).encode('ASCII', 'ignore').decode()
    # Keep only whitelisted chars
    cleaned = ''.join(c for c in cleaned_filename if c in WHITELISTED_FILENAME_CHARS)
    return cleaned if cleaned else filename  # Fallback to original if empty


def is_compressed_file_ext(filename):
    """
    Check if filename extension is in the list of allowed compressed file format
    """    
    return filename.lower().endswith(patoolib.ArchiveFormats)


def get_list_of_files(leaks_dir, unprocessed_dir):
    """
    Render a list of leak files
    Uncompress compressed files, sanitize filenames, move unprocessable files 
    
    Args:
        leaks_dir: Absolute path to directory containing leaks to process
        unprocessed_dir: Absolute path to directory for unprocessable files
    
    Returns:
        List of filenames ready to process
    """
    print(f"[DEBUG] Scanning leaks_dir: {leaks_dir}")
    print(f"[DEBUG] unprocessed_dir: {unprocessed_dir}")
    
    # Validate directories exist
    if not os.path.exists(leaks_dir):
        print(f"[ERROR] leaks_dir does not exist: {leaks_dir}")
        return []
    
    if not os.path.exists(unprocessed_dir):
        print(f"[WARNING] Creating unprocessed_dir: {unprocessed_dir}")
        os.makedirs(unprocessed_dir, exist_ok=True)
    
    # Get initial list of files (not directories)
    try:
        all_items = os.listdir(leaks_dir)
    except Exception as e:
        print(f"[ERROR] Cannot list directory {leaks_dir}: {e}")
        return []
    
    list_of_files = sorted([f for f in all_items if os.path.isfile(os.path.join(leaks_dir, f))])
    print(f"[DEBUG] Initial files found: {list_of_files}")
    
    # Process each file
    for cur_file in list_of_files[:]:  # Copy list to avoid modification during iteration
        full_path = os.path.join(leaks_dir, cur_file)
        
        # Skip if file no longer exists (may have been processed)
        if not os.path.exists(full_path):
            continue
        
        # Extract compressed files
        if is_compressed_file_ext(cur_file):
            print(f"[COMPRESSED] Extracting: {cur_file}")
            try:
                patoolib.extract_archive(full_path, verbosity=0, outdir=leaks_dir, interactive=False)
                if os.path.exists(full_path):
                    os.unlink(full_path)
                print(f"[OK] Extracted and removed: {cur_file}")
            except Exception as e:
                print(f"[ERROR] Failed to extract {cur_file}: {e}")
            continue
        
        # Check if binary and move if needed (using unprocessed_dir parameter)
        if if_binary_move(full_path, unprocessed_dir):
            # File was moved, skip to next
            continue

    # Move directories to unprocessed folder
    # Only keep flattened uncompressed files
    try:
        all_items = os.listdir(leaks_dir)
    except Exception as e:
        print(f"[ERROR] Cannot list directory after extraction: {e}")
        return []
    
    list_of_directories = sorted([d for d in all_items if os.path.isdir(os.path.join(leaks_dir, d))])
    
    for cur_dir in list_of_directories:
        source_dir = os.path.join(leaks_dir, cur_dir)
        print(f"[DIR] Moving directory to unprocessed: {cur_dir}")
        try:
            dest_path = os.path.join(unprocessed_dir, cur_dir)
            if os.path.exists(dest_path):
                print(f"[WARNING] Destination exists, merging: {dest_path}")
                shutil.rmtree(dest_path)
            shutil.move(source_dir, unprocessed_dir)
        except Exception as e:
            print(f"[ERROR] Failed to move directory {cur_dir}: {e}")

    # Sanitize filenames of remaining files
    try:
        all_items = os.listdir(leaks_dir)
    except Exception as e:
        print(f"[ERROR] Cannot list directory for sanitization: {e}")
        return []
    
    list_of_files = sorted([f for f in all_items if os.path.isfile(os.path.join(leaks_dir, f))])
    
    for cur_file in list_of_files:
        sanitized = clean_filename(cur_file)
        if sanitized != cur_file:
            print(f"[SANITIZE] {cur_file} -> {sanitized}")
            old_path = os.path.join(leaks_dir, cur_file)
            new_path = os.path.join(leaks_dir, sanitized)
            try:
                if os.path.exists(new_path):
                    print(f"[WARNING] Sanitized name exists, skipping: {sanitized}")
                    continue
                os.rename(old_path, new_path)
            except Exception as e:
                print(f"[ERROR] Failed to rename {cur_file}: {e}")

    # Get final list of files to process
    try:
        all_items = os.listdir(leaks_dir)
    except Exception as e:
        print(f"[ERROR] Cannot list directory for final list: {e}")
        return []
    
    final_files = sorted([f for f in all_items if os.path.isfile(os.path.join(leaks_dir, f))])
    print(f"[DEBUG] Final files to process: {final_files}")
    
    return final_files


if __name__ == "__main__":
    # zip gunzip, rar, tar
    print("Supported archive formats:")
    print(patoolib.ArchiveFormats)