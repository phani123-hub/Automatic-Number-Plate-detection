"""
Check what fields exist in detection documents
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.mongodb_client import mongodb_client

def check_detection_fields():
    """Check the fields in the latest detection documents."""
    collection = mongodb_client.detections
    
    print("=" * 60)
    print("CHECKING DETECTION FIELDS IN DATABASE")
    print("=" * 60)
    
    # Get the latest 3 detections
    detections = list(collection.find().sort('timestamp', -1).limit(3))
    
    if not detections:
        print("\n❌ No detections found in database!")
        return
    
    print(f"\n✓ Found {len(detections)} recent detections\n")
    
    for i, det in enumerate(detections, 1):
        print(f"\n{'='*60}")
        print(f"Detection #{i}")
        print(f"{'='*60}")
        print(f"ID: {det.get('_id')}")
        print(f"Plate Text: {det.get('plate_text')}")
        print(f"Timestamp: {det.get('timestamp')}")
        print(f"\nFIELD CHECK:")
        print(f"  ├─ crop field exists: {('crop' in det)} {'✓' if 'crop' in det else '❌'}")
        print(f"  ├─ crop has data: {(det.get('crop') is not None)} {'✓' if det.get('crop') else '❌'}")
        print(f"  ├─ bbox field exists: {('bbox' in det)} {'✓' if 'bbox' in det else '❌'}")
        print(f"  ├─ bbox value: {det.get('bbox')}")
        print(f"  ├─ track_id field exists: {('track_id' in det)} {'✓' if 'track_id' in det else '❌'}")
        print(f"  ├─ track_id value: {det.get('track_id')}")
        print(f"  └─ frame_number: {det.get('frame_number')}")
        
        # Check legacy format
        vehicle_info = det.get('vehicle_info', {})
        if vehicle_info:
            print(f"\nLEGACY vehicle_info structure:")
            print(f"  ├─ bbox: {vehicle_info.get('bbox')}")
            print(f"  ├─ tracking_id: {vehicle_info.get('tracking_id')}")
            print(f"  └─ frame_number: {vehicle_info.get('frame_number')}")
        
        # Check crop image format
        if det.get('crop'):
            crop_str = str(det.get('crop'))[:50]
            print(f"\nCrop data preview: {crop_str}...")
            print(f"Crop length: {len(det.get('crop'))} characters")
    
    print("\n" + "="*60)
    print("FIELD SUMMARY")
    print("="*60)
    
    # Summary statistics
    total = len(detections)
    with_crop = sum(1 for d in detections if d.get('crop'))
    with_bbox = sum(1 for d in detections if d.get('bbox'))
    with_track = sum(1 for d in detections if d.get('track_id') is not None)
    
    print(f"\nOut of {total} detections:")
    print(f"  ├─ {with_crop} have crop field ({with_crop/total*100:.0f}%)")
    print(f"  ├─ {with_bbox} have bbox field ({with_bbox/total*100:.0f}%)")
    print(f"  └─ {with_track} have track_id field ({with_track/total*100:.0f}%)")
    
    print("\n" + "="*60)

if __name__ == '__main__':
    check_detection_fields()
