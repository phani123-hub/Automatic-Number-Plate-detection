"""
Setup YOLOv8x Model - Quick Setup Script
Helps you place your trained best.pt file in the correct location
"""
import os
import shutil
from pathlib import Path

def setup_model():
    """Setup YOLOv8x model file."""
    
    print("=" * 60)
    print("YOLOv8x Model Setup")
    print("=" * 60)
    
    # Get paths
    backend_dir = Path(__file__).parent
    models_dir = backend_dir / "models"
    target_path = models_dir / "yolov8x.pt"
    
    # Create models directory if it doesn't exist
    models_dir.mkdir(exist_ok=True)
    print(f"✓ Models directory: {models_dir}")
    
    # Check if model already exists
    if target_path.exists():
        print(f"\n⚠️  Model already exists at: {target_path}")
        print(f"   Size: {target_path.stat().st_size / (1024*1024):.2f} MB")
        response = input("\n   Do you want to replace it? (y/n): ")
        if response.lower() != 'y':
            print("   Keeping existing model.")
            return
    
    # Ask for source file
    print("\n📂 Please provide the path to your trained best.pt file:")
    print("   (e.g., C:\\path\\to\\your\\best.pt)")
    source_path = input("\n   Path: ").strip().strip('"').strip("'")
    
    if not source_path:
        print("\n❌ No path provided. Exiting.")
        return
    
    source = Path(source_path)
    
    # Validate source file
    if not source.exists():
        print(f"\n❌ File not found: {source}")
        print("   Please check the path and try again.")
        return
    
    if not source.suffix == '.pt':
        print(f"\n⚠️  Warning: File doesn't have .pt extension")
        response = input("   Continue anyway? (y/n): ")
        if response.lower() != 'y':
            return
    
    # Show file size
    size_mb = source.stat().st_size / (1024 * 1024)
    print(f"\n📊 Source file: {source.name}")
    print(f"   Size: {size_mb:.2f} MB")
    
    # Confirm copy
    print(f"\n📋 Will copy to: {target_path}")
    response = input("   Proceed? (y/n): ")
    
    if response.lower() != 'y':
        print("   Cancelled.")
        return
    
    # Copy file
    try:
        print(f"\n🔄 Copying file...")
        shutil.copy2(source, target_path)
        print(f"✅ Model copied successfully!")
        print(f"   Location: {target_path}")
        print(f"   Size: {target_path.stat().st_size / (1024*1024):.2f} MB")
        
        # Verify by loading
        print("\n🔍 Verifying model can be loaded...")
        try:
            from ultralytics import YOLO
            model = YOLO(str(target_path))
            print("✅ Model loaded successfully!")
            print(f"   Model type: {type(model).__name__}")
            print(f"   Task: {model.task if hasattr(model, 'task') else 'N/A'}")
        except Exception as e:
            print(f"⚠️  Model copied but verification failed: {e}")
            print("   The file may still work, try running your application.")
        
        print("\n" + "=" * 60)
        print("✅ Setup Complete!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Restart your Flask application (if running)")
        print("2. Clear Python cache: rm -r __pycache__")
        print("3. Test detection with your video")
        print("\nThe system will now use your trained YOLOv8x model!")
        
    except Exception as e:
        print(f"\n❌ Error copying file: {e}")
        return

if __name__ == "__main__":
    setup_model()
