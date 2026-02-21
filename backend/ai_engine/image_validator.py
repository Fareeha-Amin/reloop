"""
Image validation for donation uploads.
"""
from django.conf import settings
from PIL import Image
import os


def validate_image_size(image_file):
    """Validate image file size."""
    if image_file.size > settings.MAX_UPLOAD_SIZE:
        return False, f"Image size exceeds {settings.MAX_UPLOAD_SIZE / 1024 / 1024}MB limit"
    return True, "Valid size"


def validate_image_type(image_file):
    """Validate image file type."""
    if image_file.content_type not in settings.ALLOWED_IMAGE_TYPES:
        return False, f"Invalid image type. Allowed: {', '.join(settings.ALLOWED_IMAGE_TYPES)}"
    return True, "Valid type"


def validate_image_content(image_file):
    """
    Basic image content validation.
    In production, this could use OpenAI Vision API for advanced validation.
    """
    try:
        # Open and verify it's a valid image
        img = Image.open(image_file)
        img.verify()
        
        # Check dimensions (minimum size)
        if img.width < 100 or img.height < 100:
            return False, "Image dimensions too small (minimum 100x100)"
        
        return True, "Valid image"
    except Exception as e:
        return False, f"Invalid image file: {str(e)}"


def validate_donation_image(image_file):
    """
    Complete validation for donation images.
    Returns (is_valid, message).
    """
    # Check size
    is_valid, message = validate_image_size(image_file)
    if not is_valid:
        return is_valid, message
    
    # Check type
    is_valid, message = validate_image_type(image_file)
    if not is_valid:
        return is_valid, message
    
    # Check content
    is_valid, message = validate_image_content(image_file)
    if not is_valid:
        return is_valid, message
    
    return True, "Image validated successfully"


# Optional: OpenAI Vision API integration for advanced validation
def validate_with_ai(image_file, category):
    """
    Use OpenAI Vision API to validate if image matches donation category.
    This is optional and requires OPENAI_API_KEY.
    """
    if not settings.OPENAI_API_KEY:
        return True, "AI validation skipped (no API key)"
    
    # TODO: Implement OpenAI Vision API call
    # For MVP, we'll skip this advanced feature
    return True, "AI validation not implemented in MVP"
