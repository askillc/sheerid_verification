"""
iOS Configuration Profile Generator with Certificate + DNS
Generates mobileconfig profiles that include both Root CA certificate and DNS settings
"""
from flask import Blueprint, Response, request
import plistlib
import uuid
import os

ios_cert_profile_bp = Blueprint('ios_cert_profile', __name__)

@ios_cert_profile_bp.route('/api/ios-profile/certificate-dns', methods=['GET'])
def generate_certificate_dns_profile():
    """
    Generate iOS mobileconfig profile with:
    1. Root CA Certificate (for SSL pinning)
    2. DNS over HTTPS configuration
    
    This combined profile provides better protection against detection
    """
    
    try:
        # Get DoH URL from query params or use default Cloudflare
        doh_url = request.args.get('doh_url', 'https://cyulluiykn.cloudflare-gateway.com/dns-query')
        
        # Read certificate file
        cert_path = 'locket_root_ca.crt'
        if not os.path.exists(cert_path):
            return Response(
                "Certificate file not found. Please generate certificate first.",
                status=500
            )
        
        with open(cert_path, 'rb') as f:
            cert_data = f.read()
        
        # Generate unique IDs for this profile
        profile_uuid = str(uuid.uuid4())
        cert_uuid = str(uuid.uuid4())
        dns_uuid = str(uuid.uuid4())
        
        # Create profile structure
        profile = {
            'PayloadContent': [
                # Certificate Payload
                {
                    'PayloadType': 'com.apple.security.root',
                    'PayloadVersion': 1,
                    'PayloadIdentifier': f'com.locketgold.cert.{cert_uuid}',
                    'PayloadUUID': cert_uuid,
                    'PayloadDisplayName': 'Locket Gold Root Certificate',
                    'PayloadDescription': 'Root certificate for Locket Gold DNS protection',
                    'PayloadCertificateFileName': 'locket_root_ca.crt',
                    'PayloadContent': cert_data
                },
                # DNS Payload
                {
                    'PayloadType': 'com.apple.dnsSettings.managed',
                    'PayloadVersion': 1,
                    'PayloadIdentifier': f'com.locketgold.dns.{dns_uuid}',
                    'PayloadUUID': dns_uuid,
                    'PayloadDisplayName': 'Locket Gold DNS',
                    'PayloadDescription': 'Secure DNS configuration for Locket Gold',
                    'DNSSettings': {
                        'DNSProtocol': 'HTTPS',
                        'ServerURL': doh_url
                    }
                }
            ],
            'PayloadType': 'Configuration',
            'PayloadVersion': 1,
            'PayloadIdentifier': f'com.locketgold.profile.{profile_uuid}',
            'PayloadUUID': profile_uuid,
            'PayloadDisplayName': 'Locket Gold Complete Profile',
            'PayloadDescription': 'Certificate + DNS configuration for Locket Gold service. This profile protects your DNS settings and ensures Gold retention.',
            'PayloadRemovalDisallowed': False,
            'PayloadOrganization': 'Locket Gold Service'
        }
        
        # Convert to plist
        plist_data = plistlib.dumps(profile)
        
        return Response(
            plist_data,
            mimetype='application/x-apple-aspen-config',
            headers={
                'Content-Disposition': 'attachment; filename=locket-gold-complete.mobileconfig'
            }
        )
        
    except Exception as e:
        print(f"❌ Error generating certificate profile: {e}")
        import traceback
        traceback.print_exc()
        return Response(
            f"Error generating profile: {str(e)}",
            status=500
        )

@ios_cert_profile_bp.route('/api/ios-profile/certificate-only', methods=['GET'])
def generate_certificate_only_profile():
    """
    Generate iOS profile with only the certificate (for testing)
    """
    
    try:
        # Read certificate file
        cert_path = 'locket_root_ca.crt'
        if not os.path.exists(cert_path):
            return Response(
                "Certificate file not found",
                status=500
            )
        
        with open(cert_path, 'rb') as f:
            cert_data = f.read()
        
        profile_uuid = str(uuid.uuid4())
        cert_uuid = str(uuid.uuid4())
        
        profile = {
            'PayloadContent': [
                {
                    'PayloadType': 'com.apple.security.root',
                    'PayloadVersion': 1,
                    'PayloadIdentifier': f'com.locketgold.cert.{cert_uuid}',
                    'PayloadUUID': cert_uuid,
                    'PayloadDisplayName': 'Locket Gold Root Certificate',
                    'PayloadDescription': 'Root certificate for Locket Gold',
                    'PayloadCertificateFileName': 'locket_root_ca.crt',
                    'PayloadContent': cert_data
                }
            ],
            'PayloadType': 'Configuration',
            'PayloadVersion': 1,
            'PayloadIdentifier': f'com.locketgold.cert.profile.{profile_uuid}',
            'PayloadUUID': profile_uuid,
            'PayloadDisplayName': 'Locket Gold Certificate',
            'PayloadDescription': 'Root certificate for Locket Gold service',
            'PayloadRemovalDisallowed': False
        }
        
        plist_data = plistlib.dumps(profile)
        
        return Response(
            plist_data,
            mimetype='application/x-apple-aspen-config',
            headers={
                'Content-Disposition': 'attachment; filename=locket-gold-certificate.mobileconfig'
            }
        )
        
    except Exception as e:
        print(f"❌ Error generating certificate-only profile: {e}")
        return Response(
            f"Error: {str(e)}",
            status=500
        )
