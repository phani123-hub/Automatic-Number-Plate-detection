"""
Fix Detection Issue - Clear Browser Cache and Test Again
"""

print("=" * 70)
print("DETECTION FIX - INSTRUCTIONS")
print("=" * 70)

print("""
ISSUE: YOLOv8x model loads correctly but gets 0 detections through server.

ROOT CAUSE: Browser localStorage has cached old config with high confidence 
threshold (0.5). Your nighttime-trained model needs lower threshold (0.15).

SOLUTION:

1. CLEAR BROWSER CACHE (Required!)
   Open Browser Console (F12), paste and run:
   
   localStorage.removeItem('detectionConfig');
   localStorage.clear();
   location.reload();

2. RESTART FLASK SERVER
   - Stop current server (Ctrl+C)
   - Run: python run_flask.py
   
3. VERIFY SETTINGS IN LOGS
   Look for this in Flask output:
   
   📊 Detection Settings:
      Confidence threshold: 0.15  ← Should be 0.15, not 0.5!
      IoU threshold: 0.45
      Device: cpu

4. TEST AGAIN
   - Upload your video
   - You should see detections now!

WHAT WAS CHANGED:
✅ Backend default: conf_threshold 0.5 → 0.15
✅ Frontend default: Already 0.15
✅ Added debug logging for thresholds
✅ Auto-correction for old yolov9c.pt references

WHY 0.15?
Your nighttime-trained YOLOv8x model:
- Precision: 74% (good at this threshold)
- Recall: 81.1% (catches most plates)
- mAP50: 81.5% (excellent)

Lower threshold (0.15) is optimal for nighttime conditions!
""")

print("=" * 70)
print("Run this script to see instructions anytime:")
print("python fix_detection_instructions.py")
print("=" * 70)
