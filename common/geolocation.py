import requests
import logging

logger = logging.getLogger(__name__)

def get_client_ip(request):
    """Extract real IP from request headers"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def get_location_from_ip(ip_address):
    """
    Fetch location data from ipapi.co
    Returns dict with state and city or None if failed.
    """
    if not ip_address or ip_address == '127.0.0.1':
        return None
        
    try:
        response = requests.get(f'https://ipapi.co/{ip_address}/json/', timeout=5)
        if response.status_code == 200:
            data = response.json()
            if not data.get('error'):
                return {
                    'state': data.get('region', ''),
                    'city': data.get('city', '')
                }
    except Exception as e:
        logger.error(f"Error fetching geolocation for IP {ip_address}: {str(e)}")
        
    return None
