"""
API endpoint to fix maintenance configuration immediately
Endpoint API để sửa cấu hình bảo trì ngay lập tức

Access: https://dqsheerid.vercel.app/fix-maintenance-now
"""

from flask import jsonify
import os

def handler(request):
    """Fix maintenance configuration in database"""
    try:
        from .supabase_client import get_supabase_client
        
        supabase = get_supabase_client()
        if not supabase:
            return jsonify({
                'success': False,
                'error': 'Cannot connect to Supabase'
            }), 500
        
        results = []
        
        # Fix 1: Set maintenance_mode = false
        try:
            supabase.table('bot_config').update({
                'config_value': 'false'
            }).eq('config_key', 'maintenance_mode').execute()
            results.append('✅ maintenance_mode = false')
        except Exception as e:
            results.append(f'⚠️ maintenance_mode error: {e}')
        
        # Fix 2: Set verify_maintenance = false (CRITICAL!)
        try:
            supabase.table('bot_config').update({
                'config_value': 'false'
            }).eq('config_key', 'verify_maintenance').execute()
            results.append('✅ verify_maintenance = false (/verify ENABLED)')
        except Exception as e:
            results.append(f'⚠️ verify_maintenance error: {e}')
        
        # Fix 3: Set vc_maintenance = true
        try:
            # Check if exists
            check = supabase.table('bot_config').select('*').eq('config_key', 'vc_maintenance').execute()
            
            if check.data:
                supabase.table('bot_config').update({
                    'config_value': 'true'
                }).eq('config_key', 'vc_maintenance').execute()
                results.append('✅ vc_maintenance = true (updated) (/vc MAINTENANCE)')
            else:
                supabase.table('bot_config').insert({
                    'config_key': 'vc_maintenance',
                    'config_value': 'true'
                }).execute()
                results.append('✅ vc_maintenance = true (created) (/vc MAINTENANCE)')
        except Exception as e:
            results.append(f'⚠️ vc_maintenance error: {e}')
        
        # Verify changes
        configs = supabase.table('bot_config').select('*').in_('config_key', ['maintenance_mode', 'verify_maintenance', 'vc_maintenance']).execute()
        
        config_status = {}
        for config in configs.data:
            config_status[config.get('config_key')] = config.get('config_value')
        
        return jsonify({
            'success': True,
            'message': 'Maintenance configuration fixed',
            'results': results,
            'current_config': config_status,
            'expected': {
                'verify': 'ENABLED (user can use /verify)',
                'vc': 'MAINTENANCE (only admin can use /vc)'
            }
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500
