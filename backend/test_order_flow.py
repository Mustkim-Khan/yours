"""
Test script for PharmacistAgent - verbose output
"""
import requests
import json

base_url = 'http://localhost:8000'

def test_order_flow():
    session_id = 'test_verbose_001'
    
    print('=' * 70)
    print('TEST 1: Order request')
    print('=' * 70)
    
    response = requests.post(f'{base_url}/chat', json={
        'message': 'I need 10 tablets of Paracetamol 500mg',
        'session_id': session_id,
        'patient_id': 'P001'
    })
    data = response.json()
    
    print(f'Full Response:\n{data.get("response", "")}')
    print(f'\nUI Card Type: {data.get("ui_card_type")}')
    print(f'Order Preview: {json.dumps(data.get("order_preview"), indent=2) if data.get("order_preview") else "None"}')
    print()
    
    print('=' * 70)
    print('TEST 2: User says "confirm"')
    print('=' * 70)
    
    response = requests.post(f'{base_url}/chat', json={
        'message': 'confirm',
        'session_id': session_id,
        'patient_id': 'P001'
    })
    data = response.json()
    
    print(f'Full Response:\n{data.get("response", "")}')
    print(f'\nUI Card Type: {data.get("ui_card_type")}')
    print(f'Order Confirmation: {json.dumps(data.get("order_confirmation"), indent=2) if data.get("order_confirmation") else "None"}')

if __name__ == '__main__':
    test_order_flow()
