import sys
from pathlib import Path

def patch_binary(binary_path):
    # Read the original binary
    with open(binary_path, 'rb') as f:
        data = bytearray(f.read())
    
    # Original instruction sequence:
    # 0x100001DA7: mov rax, cs:_OBJC_IVAR_$_AppController_progress
    # 0x100001DAE: mov rdi, [r13+rax+0]
    # 0x100001DB3: mov edx, 1
    # 0x100001DB8: lea rsi, msgRef_setHidden___objc_msgSend_fixup
    
    # We'll patch with:
    # xor rdi, rdi  ; Set rdi to 0 (null)
    # xor edx, edx  ; Set edx to 0 (not hidden)
    # jmp loc_100001DD2  ; Skip to the cleanup/return code
    
    # Patch sequence (in hex):
    # 48 31 FF         ; xor rdi, rdi
    # 31 D2            ; xor edx, edx
    # E9 15 00 00 00   ; jmp to cleanup code
    
    # Location of the instruction to patch (relative to file start)
    patch_offset = 0x1DA7
    
    # New instruction sequence
    patch = bytes([
        0x48, 0x31, 0xFF,  # xor rdi, rdi
        0x31, 0xD2,        # xor edx, edx
        0xE9, 0x15, 0x00, 0x00, 0x00  # jmp 0x1DD2
    ])
    
    # Apply the patch
    data[patch_offset:patch_offset + len(patch)] = patch
    
    # Write the patched binary
    backup_path = binary_path.parent / (binary_path.name + '.backup')
    patched_path = binary_path.parent / (binary_path.name + '.patched')
    
    # Create backup
    with open(backup_path, 'wb') as f:
        f.write(data)
    
    # Write patched binary
    with open(patched_path, 'wb') as f:
        f.write(data)
    
    print(f"Original binary backed up to: {backup_path}")
    print(f"Patched binary written to: {patched_path}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python patch.py <path_to_binary>")
        sys.exit(1)
    
    binary_path = Path(sys.argv[1])
    if not binary_path.exists():
        print(f"Error: File {binary_path} does not exist")
        sys.exit(1)
        
    patch_binary(binary_path)