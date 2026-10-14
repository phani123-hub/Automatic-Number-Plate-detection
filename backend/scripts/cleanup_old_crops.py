"""
Cleanup Old Crop Folders
Moves session folders from data/crops/{session_id}/ to data/crops/preview/{session_id}/
Run this once to organize existing crops.
"""
import shutil
from pathlib import Path

def cleanup_crops():
    crops_dir = Path('data/crops')
    
    if not crops_dir.exists():
        print("❌ data/crops directory not found")
        return
    
    moved_count = 0
    
    # Find all session folders (start with 'session_')
    for item in crops_dir.iterdir():
        if item.is_dir() and item.name.startswith('session_'):
            # This is an old session folder, move to preview/
            preview_dir = crops_dir / 'preview'
            preview_dir.mkdir(exist_ok=True)
            
            destination = preview_dir / item.name
            
            try:
                shutil.move(str(item), str(destination))
                print(f"✓ Moved: {item.name} → preview/{item.name}")
                moved_count += 1
            except Exception as e:
                print(f"❌ Failed to move {item.name}: {e}")
    
    if moved_count > 0:
        print(f"\n✅ Successfully moved {moved_count} session folder(s) to preview/")
    else:
        print("\n✓ No old session folders found. Already organized!")
    
    # Show current structure
    print("\n📁 Current crops structure:")
    if (crops_dir / 'preview').exists():
        preview_sessions = list((crops_dir / 'preview').iterdir())
        print(f"  - preview/: {len(preview_sessions)} session(s)")
    
    if (crops_dir / 'manual_review').exists():
        review_sessions = list((crops_dir / 'manual_review').iterdir())
        print(f"  - manual_review/: {len(review_sessions)} session(s)")

if __name__ == "__main__":
    print("🔄 Cleaning up old crop folders...\n")
    cleanup_crops()
