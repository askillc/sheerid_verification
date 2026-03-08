"""
Teacher Verification with Browserless.io
Bypasses SheerID fraud detection using cloud browser
"""
import os
import json
import asyncio
from flask import Blueprint, request, jsonify

teacher_browserless_bp = Blueprint('teacher_browserless', __name__)

# Import browserless client
try:
    from .browserless_client import (
        bypass_and_get_upload_url,
        upload_document_after_bypass,
        full_teacher_verification,
        BROWSERLESS_API_KEYS,  # Use the list of keys
        get_browserless_url
    )
    BROWSERLESS_AVAILABLE = len(BROWSERLESS_API_KEYS) > 0
    print(f"✅ Browserless configured with {len(BROWSERLESS_API_KEYS)} API keys")
except ImportError:
    BROWSERLESS_AVAILABLE = False
    BROWSERLESS_API_KEYS = []
    print("⚠️ Browserless client not available")


@teacher_browserless_bp.route('/api/teacher-verify-browserless', methods=['POST'])
def teacher_verify_browserless():
    """
    Teacher verification using Browserless.io to bypass fraud detection
    
    Request body:
    {
        "verification_url": "https://services.sheerid.com/verify/...",
        "school_name": "Pasadena Independent School District",  // optional
        "document_base64": "base64_encoded_image"  // optional, for full flow
    }
    
    Response:
    {
        "success": true/false,
        "verification_id": "...",
        "user_data": {...},
        "message": "..."
    }
    """
    if not BROWSERLESS_AVAILABLE:
        return jsonify({
            "success": False,
            "error": "Browserless not configured. Set BROWSERLESS_API_KEY environment variable."
        }), 500
    
    try:
        data = request.get_json() or {}
        verification_url = data.get('verification_url')
        school_name = data.get('school_name', 'Pasadena Independent School District')
        document_base64 = data.get('document_base64')
        
        if not verification_url:
            return jsonify({
                "success": False,
                "error": "verification_url is required"
            }), 400
        
        # Run async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            if document_base64:
                # Full flow: bypass + upload
                result = loop.run_until_complete(
                    full_teacher_verification(verification_url, document_base64, school_name)
                )
            else:
                # Just bypass fraud detection
                result = loop.run_until_complete(
                    bypass_and_get_upload_url(verification_url, school_name)
                )
        finally:
            loop.close()
        
        if result.get('success'):
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        print(f"❌ Teacher browserless error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@teacher_browserless_bp.route('/api/teacher-upload-doc', methods=['POST'])
def teacher_upload_document():
    """
    Upload document after fraud bypass
    
    Request body:
    {
        "verification_id": "...",
        "document_base64": "base64_encoded_image",
        "document_type": "image/png"  // optional
    }
    """
    if not BROWSERLESS_AVAILABLE:
        return jsonify({
            "success": False,
            "error": "Browserless not configured"
        }), 500
    
    try:
        data = request.get_json() or {}
        verification_id = data.get('verification_id')
        document_base64 = data.get('document_base64')
        document_type = data.get('document_type', 'image/png')
        
        if not verification_id or not document_base64:
            return jsonify({
                "success": False,
                "error": "verification_id and document_base64 are required"
            }), 400
        
        # Run async upload
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                upload_document_after_bypass(verification_id, document_base64, document_type)
            )
        finally:
            loop.close()
        
        if result.get('success'):
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        print(f"❌ Teacher upload error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@teacher_browserless_bp.route('/api/teacher-browserless-status', methods=['GET'])
def teacher_browserless_status():
    """Check if Browserless is configured and available"""
    return jsonify({
        "available": BROWSERLESS_AVAILABLE,
        "api_key_set": bool(os.environ.get('BROWSERLESS_API_KEY')),
        "message": "Browserless ready" if BROWSERLESS_AVAILABLE else "BROWSERLESS_API_KEY not set"
    })
