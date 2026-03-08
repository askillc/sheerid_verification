"""
iOS DNS Profile Generator
Generates .mobileconfig files for DNS over HTTPS (DoH) configuration
"""

import uuid
from flask import Blueprint, Response, request

ios_profile_bp = Blueprint('ios_profile', __name__)

def generate_doh_profile(doh_url, profile_name="Locket Gold DNS", organization="Locket Gold"):
    """
    Generate iOS mobileconfig for DNS over HTTPS
    
    Args:
        doh_url: DoH URL (e.g., https://cyulluiykn.cloudflare-gateway.com/dns-query)
        profile_name: Display name for the profile
        organization: Organization name
    
    Returns:
        str: XML content for .mobileconfig file
    """
    
    # Generate unique IDs
    profile_uuid = str(uuid.uuid4()).upper()
    payload_uuid = str(uuid.uuid4()).upper()
    
    # Extract server URL from DoH URL
    # https://cyulluiykn.cloudflare-gateway.com/dns-query -> cyulluiykn.cloudflare-gateway.com
    server_url = doh_url.replace('https://', '').replace('http://', '').split('/')[0]
    
    mobileconfig = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>PayloadContent</key>
    <array>
        <dict>
            <key>DNSSettings</key>
            <dict>
                <key>DNSProtocol</key>
                <string>HTTPS</string>
                <key>ServerURL</key>
                <string>{doh_url}</string>
                <key>ServerName</key>
                <string>{server_url}</string>
            </dict>
            <key>PayloadDescription</key>
            <string>Configures DNS over HTTPS for Locket Gold</string>
            <key>PayloadDisplayName</key>
            <string>{profile_name}</string>
            <key>PayloadIdentifier</key>
            <string>com.locketgold.dnsconfig.{payload_uuid}</string>
            <key>PayloadType</key>
            <string>com.apple.dnsSettings.managed</string>
            <key>PayloadUUID</key>
            <string>{payload_uuid}</string>
            <key>PayloadVersion</key>
            <integer>1</integer>
            <key>ProhibitDisablement</key>
            <false/>
        </dict>
    </array>
    <key>PayloadDescription</key>
    <string>Installs DNS over HTTPS configuration for Locket Gold ad blocking</string>
    <key>PayloadDisplayName</key>
    <string>{profile_name}</string>
    <key>PayloadIdentifier</key>
    <string>com.locketgold.profile.{profile_uuid}</string>
    <key>PayloadRemovalDisallowed</key>
    <false/>
    <key>PayloadType</key>
    <string>Configuration</string>
    <key>PayloadUUID</key>
    <string>{profile_uuid}</string>
    <key>PayloadVersion</key>
    <integer>1</integer>
    <key>PayloadOrganization</key>
    <string>{organization}</string>
</dict>
</plist>'''
    
    return mobileconfig

@ios_profile_bp.route('/api/ios-profile/cloudflare', methods=['GET'])
def get_cloudflare_profile():
    """
    Generate iOS mobileconfig for Cloudflare DoH
    
    Query params:
        - doh_url (optional): Custom DoH URL
        - name (optional): Profile display name
    """
    try:
        # Get DoH URL from query param or use default
        doh_url = request.args.get('doh_url', 'https://cyulluiykn.cloudflare-gateway.com/dns-query')
        profile_name = request.args.get('name', 'Locket Gold DNS (Cloudflare)')
        
        # Generate profile
        profile_content = generate_doh_profile(doh_url, profile_name)
        
        # Return as downloadable file
        response = Response(
            profile_content,
            mimetype='application/x-apple-aspen-config',
            headers={
                'Content-Disposition': 'attachment; filename=locket-gold-dns.mobileconfig',
                'Content-Type': 'application/x-apple-aspen-config'
            }
        )
        
        return response
        
    except Exception as e:
        print(f"❌ Error generating iOS profile: {e}")
        return Response(
            f"Error generating profile: {str(e)}",
            status=500,
            mimetype='text/plain'
        )

@ios_profile_bp.route('/api/ios-profile/nextdns/<profile_id>', methods=['GET'])
def get_nextdns_profile(profile_id):
    """
    Redirect to NextDNS profile download
    
    Args:
        profile_id: NextDNS profile ID
    """
    try:
        # NextDNS provides direct profile download
        nextdns_url = f"https://apple.nextdns.io/{profile_id}"
        
        from flask import redirect
        return redirect(nextdns_url, code=302)
        
    except Exception as e:
        print(f"❌ Error redirecting to NextDNS: {e}")
        return Response(
            f"Error: {str(e)}",
            status=500,
            mimetype='text/plain'
        )

@ios_profile_bp.route('/api/ios-profile/test', methods=['GET'])
def test_profile():
    """
    Test endpoint to verify profile generation
    """
    try:
        doh_url = 'https://cyulluiykn.cloudflare-gateway.com/dns-query'
        profile_content = generate_doh_profile(doh_url, "Test Profile")
        
        return Response(
            profile_content,
            mimetype='text/plain'
        )
        
    except Exception as e:
        return Response(
            f"Error: {str(e)}",
            status=500,
            mimetype='text/plain'
        )
