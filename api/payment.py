#!/usr/bin/env python3
"""
Payment processing API for SheerID VIP Bot
"""

import os
import sqlite3
import json
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)

# Database path - same as other files
DB_PATH = "/tmp/sheerid_bot.db"

def update_user_coins(user_id, amount, transaction_type, description, job_id=None):
    """Update user coins and add transaction record"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Update user coins
        cursor.execute('UPDATE users SET coins = coins + ? WHERE id = ?', (amount, user_id))
        
        # Add transaction record
        cursor.execute('''
            INSERT INTO transactions (user_id, type, amount, description, job_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, transaction_type, amount, description, job_id, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating user coins: {e}")
        return False

def get_user_by_telegram_id(telegram_id):
    """Get user by telegram ID"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
        user = cursor.fetchone()
        conn.close()
        return user
    except Exception as e:
        print(f"Error getting user: {e}")
        return None

def send_telegram_message(chat_id, message):
    """Send message to Telegram"""
    try:
        import requests
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not bot_token:
            print("TELEGRAM_BOT_TOKEN not found")
            return False
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'Markdown'
        }
        
        response = requests.post(url, data=data, timeout=30)
        return response.status_code == 200
    except Exception as e:
        print(f"Error sending Telegram message: {e}")
        return False

@app.route('/process-payment', methods=['POST'])
def process_payment():
    """Process payment and add coins to user account"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['telegram_id', 'coins', 'amount', 'transaction_id']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing field: {field}'}), 400
        
        telegram_id = data['telegram_id']
        coins = int(data['coins'])
        amount = int(data['amount'])
        transaction_id = data['transaction_id']
        
        # Validate amounts
        if coins < 10 or coins > 1000:
            return jsonify({'success': False, 'error': 'Invalid coin amount'}), 400
        
        expected_amount = coins * 1000  # 1 xu = 1000 VNĐ
        if amount != expected_amount:
            return jsonify({'success': False, 'error': 'Amount mismatch'}), 400
        
        # Get user
        user = get_user_by_telegram_id(telegram_id)
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        # Check if transaction already processed
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) FROM transactions 
            WHERE description LIKE ? AND type = 'deposit'
        ''', (f'%{transaction_id}%',))
        
        if cursor.fetchone()[0] > 0:
            conn.close()
            return jsonify({'success': False, 'error': 'Transaction already processed'}), 400
        
        conn.close()
        
        # Add coins to user account
        success = update_user_coins(
            user[0], 
            coins, 
            'deposit', 
            f'Nạp {coins} xu - Transaction ID: {transaction_id}',
            None
        )
        
        if not success:
            return jsonify({'success': False, 'error': 'Failed to update coins'}), 500
        
        # Send confirmation message
        message = f"""
✅ **Nạp xu thành công!**

💰 **Số xu nạp:** {coins}
🪙 **Tổng xu:** {user[5] + coins}
🆔 **Transaction ID:** {transaction_id}

💡 Sử dụng /verify <URL> để xác minh SheerID
❓ **Hỗ trợ:** @meepzizhere
        """
        
        send_telegram_message(telegram_id, message)
        
        return jsonify({
            'success': True,
            'message': 'Payment processed successfully',
            'coins_added': coins,
            'new_balance': user[5] + coins
        })
        
    except Exception as e:
        print(f"Payment processing error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/check-payment', methods=['POST'])
def check_payment():
    """Check payment status (for manual verification)"""
    try:
        data = request.get_json()
        telegram_id = data.get('telegram_id')
        
        if not telegram_id:
            return jsonify({'success': False, 'error': 'Missing telegram_id'}), 400
        
        # Get user's recent transactions
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT amount, description, created_at 
            FROM transactions 
            WHERE user_id = (SELECT id FROM users WHERE telegram_id = ?) 
            AND type = 'deposit'
            ORDER BY created_at DESC 
            LIMIT 5
        ''', (telegram_id,))
        
        transactions = cursor.fetchall()
        conn.close()
        
        return jsonify({
            'success': True,
            'transactions': [
                {
                    'amount': t[0],
                    'description': t[1],
                    'created_at': t[2]
                } for t in transactions
            ]
        })
        
    except Exception as e:
        print(f"Check payment error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
