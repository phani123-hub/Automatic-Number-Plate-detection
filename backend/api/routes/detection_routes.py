"""
Detection Routes
Video processing and detection history endpoints
"""
from flask import Blueprint, request, jsonify
import sys
from pathlib import Path
import base64
import io
import json
import cv2
import numpy as np
from werkzeug.utils import secure_filename
import uuid
import os
import tempfile

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from auth.jwt_handler import JWTHandler
from api.services.detection_service import DetectionService
from database.detection_repository import DetectionRepository

detection_bp = Blueprint('detection', __name__)
detection_service = DetectionService()
models_loaded = False


def ensure_models_loaded(config):
    """Lazy load models on first request."""
    global models_loaded
    if not models_loaded:
        print("🔄 Loading detection models for the first time...")
        success = detection_service.load_models(config)
        if success:
            models_loaded = True
            print("✅ Models loaded successfully!")
        else:
            print("❌ Failed to load models!")
        return success
    return True


@detection_bp.route('/start-session', methods=['POST'])
def start_session():
    """Start a new detection session and clear cache."""
    try:
        user_info, error, status = get_user_from_request()
        if error:
            return error, status
        
        data = request.get_json() or {}
        session_id = data.get('session_id', str(uuid.uuid4()))
        
        # Clear the session cache to prevent duplicates
        detection_service.reset_session(session_id)
        
        return {
            'message': 'Session started successfully',
            'session_id': session_id
        }, 200
        
    except Exception as e:
        return {'error': f'Failed to start session: {str(e)}'}, 500


def get_user_from_request():
    """Extract and validate user from request token."""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    if not token:
        return None, {'error': 'Authorization token required'}, 401
    
    user_info = JWTHandler.get_user_from_token(token)
    if not user_info:
        return None, {'error': 'Invalid or expired token'}, 401
    
    return user_info, None, None


@detection_bp.route('/process-frame', methods=['POST'])
def process_frame():
    """
    Process a single video frame and detect license plates.
    
    Request JSON:
    {
        "frame_base64": "base64_encoded_image",
        "config": {
            "enable_preprocessing": true,
            "enable_clahe": true,
            "clip_limit": 2.0,
            ...
        },
        "session_id": "uuid"
    }
    """
    try:
        user_info, error, status = get_user_from_request()
        if error:
            return error, status
        
        data = request.get_json()
        if not data or 'frame_base64' not in data:
            return {'error': 'frame_base64 is required'}, 400
        
        # Decode base64 frame
        try:
            frame_bytes = base64.b64decode(data['frame_base64'])
            nparr = np.frombuffer(frame_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is None:
                return {'error': 'Invalid image data'}, 400
            
            print(f"📥 Received frame: shape={frame.shape}, dtype={frame.dtype}, min={frame.min()}, max={frame.max()}")
            
            # Save first frame for debugging
            if not hasattr(detection_service, '_saved_debug_frame'):
                debug_path = 'data/debug_frame_react.jpg'
                cv2.imwrite(debug_path, frame)
                print(f"💾 Saved first React frame to: {debug_path}")
                detection_service._saved_debug_frame = True
                
        except Exception as e:
            return {'error': f'Failed to decode frame: {str(e)}'}, 400
        
        # Parse config if it's a JSON string
        config = data.get('config', {})
        if isinstance(config, str):
            try:
                config = json.loads(config)
            except json.JSONDecodeError:
                config = {}
        
        session_id = data.get('session_id', str(uuid.uuid4()))
        
        # Load models if not already loaded
        if not ensure_models_loaded(config):
            return {'error': 'Failed to load detection models'}, 500
        
        # Process frame
        annotated_frame, results = detection_service.process_frame(
            frame=frame,
            config=config,
            user_id=user_info['user_id'],
            username=user_info['username'],
            session_id=session_id
        )
        
        # Encode annotated frame to base64
        _, buffer = cv2.imencode('.jpg', annotated_frame)
        annotated_base64 = base64.b64encode(buffer).decode('utf-8')
        
        return {
            'message': 'Frame processed successfully',
            'annotated_frame': annotated_base64,
            'results': results,
            'frame_count': detection_service.get_frame_count(),
            'detection_count': len(results)
        }, 200
        
    except Exception as e:
        return {'error': f'Frame processing failed: {str(e)}'}, 500


@detection_bp.route('/process-video', methods=['POST'])
def process_video():
    """
    Process entire video file and return detection results.
    
    Request: multipart/form-data with video file and config
    """
    try:
        user_info, error, status = get_user_from_request()
        if error:
            return error, status
        
        if 'video' not in request.files:
            return {'error': 'Video file is required'}, 400
        
        video_file = request.files['video']
        
        # Parse config if it's a JSON string
        config = request.form.get('config', '{}')
        if isinstance(config, str):
            try:
                config = json.loads(config)
            except json.JSONDecodeError:
                config = {}
        
        session_id = request.form.get('session_id', str(uuid.uuid4()))
        
        if video_file.filename == '':
            return {'error': 'No video file selected'}, 400
        
        # Save temporary video file to a cross-platform temp directory
        filename = secure_filename(video_file.filename)
        # prepend session id/uuid to avoid collisions
        tmp_filename = f"{session_id}_{uuid.uuid4().hex}_{filename}"
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, tmp_filename)

        try:
            video_file.save(temp_path)
        except Exception as e:
            return {'error': f'Failed to save uploaded video: {str(e)}'}, 500
        
        try:
            # Process video
            results, stats = detection_service.process_video(
                video_path=temp_path,
                config=config,
                user_id=user_info['user_id'],
                username=user_info['username'],
                session_id=session_id
            )
            
            return {
                'message': 'Video processed successfully',
                'results': results,
                'statistics': stats
            }, 200
            
        finally:
            # Cleanup temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    except Exception as e:
        return {'error': f'Video processing failed: {str(e)}'}, 500


@detection_bp.route('/history', methods=['GET'])
def get_detection_history():
    """Get user's detection history."""
    try:
        user_info, error, status = get_user_from_request()
        if error:
            return error, status
        
        limit = request.args.get('limit', 50, type=int)
        skip = request.args.get('skip', 0, type=int)
        
        detection_repo = DetectionRepository()
        detections = detection_repo.get_user_detections(
            user_id=user_info['user_id'],
            limit=limit,
            skip=skip
        )
        
        return {
            'message': 'Detection history retrieved',
            'detections': detections,
            'count': len(detections)
        }, 200
        
    except Exception as e:
        return {'error': f'Failed to fetch history: {str(e)}'}, 500


@detection_bp.route('/session/<session_id>', methods=['GET'])
def get_session_detections(session_id):
    """Get all detections for a specific session."""
    try:
        user_info, error, status = get_user_from_request()
        if error:
            return error, status
        
        detection_repo = DetectionRepository()
        detections = detection_repo.get_session_detections(
            user_id=user_info['user_id'],
            session_id=session_id
        )
        
        return {
            'message': 'Session detections retrieved',
            'detections': detections,
            'count': len(detections)
        }, 200
        
    except Exception as e:
        return {'error': f'Failed to fetch session: {str(e)}'}, 500


@detection_bp.route('/preview/<session_id>', methods=['GET'])
def get_preview_detections(session_id):
    """
    Get preview detections for validation display.
    Returns top 2 detected plates with their best crop images.
    """
    try:
        user_info, error, status = get_user_from_request()
        if error:
            return error, status
        
        # Get preview detections from service
        previews = detection_service.get_preview_detections(session_id)
        
        return {
            'message': 'Preview detections retrieved',
            'previews': previews,
            'count': len(previews)
        }, 200
        
    except Exception as e:
        return {'error': f'Failed to fetch previews: {str(e)}'}, 500


@detection_bp.route('/confirm-detections', methods=['POST'])
def confirm_detections():
    """
    Confirm and save preview detections to database.
    Request: { "session_id": "...", "detection_ids": [track_ids to confirm] }
    """
    try:
        user_info, error, status = get_user_from_request()
        if error:
            return error, status
        
        data = request.get_json()
        session_id = data.get('session_id')
        track_ids = data.get('track_ids', [])  # List of track IDs to confirm
        
        if not session_id:
            return {'error': 'session_id required'}, 400
        
        # Get preview detections
        previews = detection_service.preview_buffer.get(session_id, [])
        
        saved_count = 0
        detection_repo = DetectionRepository()
        
        for preview in previews:
            # If track_ids specified, only save those
            if track_ids and preview['track_id'] not in track_ids:
                continue
            
            try:
                # Read crop image
                crop_path = Path(preview['crop_path'])
                if crop_path.exists():
                    crop_img = cv2.imread(str(crop_path))
                    
                    # Save to database
                    detection_id = detection_repo.save_detection(
                        user_id=user_info['user_id'],
                        username=user_info['username'],
                        plate_text=preview['plate_text'],
                        confidence=preview['confidence'],
                        cropped_plate=crop_img,
                        bbox=preview['bbox'],
                        track_id=preview['track_id'],
                        frame_number=preview['frame_num'],
                        is_valid=True,
                        session_id=session_id
                    )
                    saved_count += 1
                    print(f"✓ Confirmed and saved: {preview['plate_text']} (ID={detection_id})")
            except Exception as e:
                print(f"  Warning: Failed to save preview detection: {e}")
                continue
        
        return {
            'message': f'Successfully saved {saved_count} detections',
            'saved_count': saved_count
        }, 200
        
    except Exception as e:
        return {'error': f'Failed to confirm detections: {str(e)}'}, 500


@detection_bp.route('/manual-review/<session_id>', methods=['GET'])
def get_manual_review_crops(session_id):
    """
    Get manual review crops (OCR < 10%) for human validation.
    Returns the best crop image from each low-confidence track.
    """
    try:
        user_info, error, status = get_user_from_request()
        if error:
            return error, status
        
        # Get manual review crops from service
        crops = detection_service.get_manual_review_crops(session_id)
        
        return {
            'message': 'Manual review crops retrieved',
            'crops': crops,
            'count': len(crops)
        }, 200
        
    except Exception as e:
        return {'error': f'Failed to fetch manual review crops: {str(e)}'}, 500


@detection_bp.route('/confirm-manual-review', methods=['POST'])
def confirm_manual_review():
    """
    Confirm and save manual review crops with user-entered plate text.
    Request: { 
        "session_id": "...", 
        "crops": [
            {
                "track_id": 1, 
                "plate_text": "MH 02 FU 9779", 
                "confidence": 0.92,
                "frame_num": 46,
                "crop_path": "path/to/crop.jpg"
            }
        ]
    }
    """
    try:
        user_info, error, status = get_user_from_request()
        if error:
            return error, status
        
        data = request.get_json()
        session_id = data.get('session_id')
        crops_to_save = data.get('crops', [])
        
        if not session_id:
            return {'error': 'session_id required'}, 400
        
        if not crops_to_save:
            return {'error': 'No crops provided'}, 400
        
        saved_count = 0
        detection_repo = DetectionRepository()
        
        for crop_data in crops_to_save:
            try:
                # Read crop image from disk
                crop_path = Path(crop_data['crop_path'])
                if crop_path.exists():
                    crop_img = cv2.imread(str(crop_path))
                    
                    # Get bbox from image dimensions (approximate)
                    h, w = crop_img.shape[:2]
                    bbox = [0, 0, w, h]  # x, y, width, height
                    
                    # Save to database with user-entered plate text
                    detection_id = detection_repo.save_detection(
                        user_id=user_info['user_id'],
                        username=user_info['username'],
                        plate_text=crop_data['plate_text'],
                        confidence=crop_data['confidence'],
                        cropped_plate=crop_img,
                        bbox=bbox,
                        track_id=crop_data['track_id'],
                        frame_number=crop_data['frame_num'],
                        is_valid=True,
                        session_id=session_id
                    )
                    saved_count += 1
                    print(f"✓ Manual review saved: {crop_data['plate_text']} (Track {crop_data['track_id']}, ID={detection_id})")
            except Exception as e:
                print(f"  Warning: Failed to save manual review crop: {e}")
                continue
        
        return {
            'message': f'Successfully saved {saved_count} manual review detections',
            'saved_count': saved_count
        }, 200
        
    except Exception as e:
        return {'error': f'Failed to confirm manual review: {str(e)}'}, 500


@detection_bp.route('/statistics', methods=['GET'])
def get_statistics():
    """Get detection statistics for user."""
    try:
        user_info, error, status = get_user_from_request()
        if error:
            return error, status
        
        detection_repo = DetectionRepository()
        stats = detection_repo.get_detection_stats(user_info['user_id'])
        
        return {
            'message': 'Statistics retrieved',
            'statistics': stats
        }, 200
        
    except Exception as e:
        return {'error': f'Failed to fetch statistics: {str(e)}'}, 500


@detection_bp.route('/<detection_id>', methods=['GET'])
def get_detection(detection_id):
    """Get single detection details."""
    try:
        user_info, error, status = get_user_from_request()
        if error:
            return error, status
        
        detection_repo = DetectionRepository()
        detection = detection_repo.get_detection_by_id(detection_id)
        
        if not detection or detection.get('user_id') != user_info['user_id']:
            return {'error': 'Detection not found'}, 404
        
        return {
            'message': 'Detection retrieved',
            'detection': detection
        }, 200
        
    except Exception as e:
        return {'error': f'Failed to fetch detection: {str(e)}'}, 500


@detection_bp.route('/<detection_id>', methods=['DELETE'])
def delete_detection(detection_id):
    """Delete a detection record."""
    try:
        user_info, error, status = get_user_from_request()
        if error:
            return error, status
        
        detection_repo = DetectionRepository()
        
        if detection_repo.delete_detection(detection_id, user_info['user_id']):
            return {'message': 'Detection deleted successfully'}, 200
        else:
            return {'error': 'Failed to delete detection'}, 500
            
    except Exception as e:
        return {'error': f'Deletion failed: {str(e)}'}, 500


# RTSP Stream Management
rtsp_streams = {}  # Store active RTSP streams per user


@detection_bp.route('/rtsp-stream', methods=['POST'])
def start_rtsp_stream():
    """Start processing an RTSP stream."""
    try:
        user_info, error, status = get_user_from_request()
        if error:
            return error, status
        
        data = request.get_json()
        rtsp_url = data.get('rtsp_url')
        
        if not rtsp_url:
            return {'error': 'RTSP URL is required'}, 400
        
        # Parse config
        config = data.get('config', {})
        session_id = data.get('session_id', str(uuid.uuid4()))
        user_id = user_info['user_id']
        
        # Stop existing stream for this user if any
        if user_id in rtsp_streams:
            try:
                rtsp_streams[user_id]['cap'].release()
            except Exception as e:
                print(f"Warning: Failed to release RTSP stream: {e}")
        
        # Open RTSP stream
        import cv2
        cap = cv2.VideoCapture(rtsp_url)
        
        if not cap.isOpened():
            return {'error': 'Failed to connect to RTSP stream'}, 400
        
        # Store stream info
        rtsp_streams[user_id] = {
            'cap': cap,
            'session_id': session_id,
            'config': config,
            'rtsp_url': rtsp_url
        }
        
        return {
            'message': 'RTSP stream started successfully',
            'session_id': session_id
        }, 200
        
    except Exception as e:
        return {'error': f'Failed to start RTSP stream: {str(e)}'}, 500


@detection_bp.route('/rtsp-frame', methods=['POST'])
def get_rtsp_frame():
    """Get a frame from the RTSP stream and process it."""
    try:
        user_info, error, status = get_user_from_request()
        if error:
            return error, status
        
        user_id = user_info['user_id']
        
        if user_id not in rtsp_streams:
            return {'error': 'No active RTSP stream. Start stream first.'}, 404
        
        stream_info = rtsp_streams[user_id]
        cap = stream_info['cap']
        config = stream_info['config']
        session_id = stream_info['session_id']
        
        # Read frame from stream
        ret, frame = cap.read()
        
        if not ret:
            # Stream ended or error
            cap.release()
            del rtsp_streams[user_id]
            return {'error': 'Failed to read frame from stream'}, 500
        
        # Process frame for detection
        annotated_frame, results = detection_service.process_frame(
            frame=frame,
            config=config,
            user_id=user_id,
            username=user_info['username'],
            session_id=session_id
        )
        
        # Encode frame to base64
        _, buffer = cv2.imencode('.jpg', annotated_frame)
        frame_base64 = base64.b64encode(buffer).decode('utf-8')
        
        return {
            'frame': frame_base64,
            'results': results,
            'session_id': session_id
        }, 200
        
    except Exception as e:
        return {'error': f'Frame processing failed: {str(e)}'}, 500


@detection_bp.route('/rtsp-stop', methods=['POST'])
def stop_rtsp_stream():
    """Stop the RTSP stream."""
    try:
        user_info, error, status = get_user_from_request()
        if error:
            return error, status
        
        user_id = user_info['user_id']
        
        if user_id in rtsp_streams:
            try:
                rtsp_streams[user_id]['cap'].release()
                del rtsp_streams[user_id]
            except Exception as e:
                print(f"Error stopping stream: {e}")
            
            return {'message': 'RTSP stream stopped successfully'}, 200
        else:
            return {'error': 'No active RTSP stream'}, 404
            
    except Exception as e:
        return {'error': f'Failed to stop stream: {str(e)}'}, 500
