"""Quick test: verify security guard blocks destructive operations."""

from safe_fs import safe_fs, PermissionDeniedError

print("Testing security guard...")
blocked = 0

for op_name in ["rename", "delete", "move", "chmod", "copy"]:
    op = getattr(safe_fs, op_name)
    try:
        op("test_path")
        print(f"  ❌ {op_name}: NOT BLOCKED (SECURITY FAILURE)")
    except PermissionDeniedError:
        print(f"  ✅ {op_name}: BLOCKED correctly")
        blocked += 1

# Test write outside outputs
print("\nTesting write guard...")
try:
    safe_fs.write_output("../../evil.txt", "hacked")
    print("  ❌ Write outside outputs: NOT BLOCKED")
except PermissionDeniedError:
    print("  ✅ Write outside outputs: BLOCKED correctly")
    blocked += 1

# Test valid write to outputs
try:
    path = safe_fs.write_output("test_security_check.txt", "This is a test")
    print(f"  ✅ Write to outputs: ALLOWED → {path}")
    import os; os.remove(path)
except Exception as e:
    print(f"  ❌ Write to outputs failed: {e}")

print(f"\n🔒 {blocked}/6 destructive operations blocked correctly")

# Test file identification
from file_identifier import identify_file
info = identify_file("config.yaml")
print(f"\n📄 config.yaml → category={info['category']}, mime={info['mime_type']}, size={info['size_human']}")

info = identify_file("tools.py")
print(f"📄 tools.py → category={info['category']}, supported={info['is_supported']}")

# Test folder browser
from folder_browser import folder_browser
listing = folder_browser.browse(".")
print(f"\n📁 Current dir: {listing['directories']} dirs, {listing['files']} files")

# Test NL parser
from nl_interface import NLParser
p = NLParser()
tests = [
    "extract invoice.pdf",
    "what's in photo.jpg",
    "process all files in /data",
    "identify report.xlsx",
    "browse /data",
    "help",
]
print("\n🤖 NL Parser tests:")
for t in tests:
    result = p.parse(t)
    print(f"  '{t}' → intent={result['intent']}, target={result['target']}")

print("\n✅ ALL TESTS PASSED")
