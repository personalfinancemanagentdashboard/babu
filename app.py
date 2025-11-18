import os
import json
import csv
import io
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import date, datetime
from flask import Flask, request, jsonify, session, redirect, send_from_directory, make_response
from flask_cors import CORS
from flask_session import Session
from functools import wraps
from authlib.integrations.flask_client import OAuth
from authlib.common.security import generate_token
from pydantic import ValidationError
from openai import OpenAI
import re
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
import openpyxl
from dateutil import parser as date_parser

from storage import storage
from models import (
    InsertTransactionSchema, InsertBudgetSchema, InsertGoalSchema, InsertBillSchema,
    TransactionSchema, BudgetSchema, GoalSchema, BillSchema, UserSchema, UpsertUserSchema
)
from health_score import calculate_health_score
from ocr import extract_transaction_from_image

app = Flask(__name__, static_folder='dist/public', static_url_path='')
app.config['SECRET_KEY'] = os.environ.get('SESSION_SECRET', 'dev-secret-key')
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

Session(app)
CORS(app, supports_credentials=True)

oauth = OAuth(app)

ISSUER_URL = os.environ.get('ISSUER_URL', 'https://replit.com/oidc')
CLIENT_ID = os.environ.get('REPL_ID')

replit_auth_configured = False
if CLIENT_ID:
    try:
        oauth.register(
            name='replit',
            client_id=CLIENT_ID,
            server_metadata_url=f'{ISSUER_URL}/.well-known/openid-configuration',
            client_kwargs={
                'scope': 'openid email profile offline_access'
            }
        )
        replit_auth_configured = True
    except Exception as e:
        print(f"WARNING: Failed to configure Replit Auth: {e}")
else:
    print("WARNING: REPL_ID not set. Authentication will not work.")

openai_client = None
if os.environ.get('OPENAI_API_KEY'):
    openai_client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
else:
    print("OPENAI_API_KEY not set. AI chat and OCR features will be disabled.")

def is_authenticated(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return jsonify({"message": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated_function

def get_user_id() -> Optional[str]:
    user = session.get('user')
    if user and isinstance(user, dict):
        return user.get('sub')
    return None

def model_to_dict(obj):
    if hasattr(obj, '__dict__'):
        result = {}
        for key, value in obj.__dict__.items():
            if key.startswith('_'):
                continue
            if isinstance(value, Decimal):
                result[key] = str(value)
            elif isinstance(value, (date, datetime)):
                result[key] = value.isoformat()
            else:
                result[key] = value
        return result
    return obj

def models_to_dicts(objects):
    return [model_to_dict(obj) for obj in objects]

@app.route('/api/login')
def login():
    if not replit_auth_configured:
        return jsonify({"message": "Authentication not configured. Set REPL_ID environment variable."}), 503
    redirect_uri = request.url_root.rstrip('/') + '/api/callback'
    return oauth.replit.authorize_redirect(redirect_uri)

@app.route('/api/callback')
def callback():
    if not replit_auth_configured:
        return jsonify({"message": "Authentication not configured."}), 503
    try:
        token = oauth.replit.authorize_access_token()
        user_info = token.get('userinfo') if token else None
        
        if user_info:
            session['user'] = {
                'sub': user_info.get('sub'),
                'email': user_info.get('email'),
                'first_name': user_info.get('first_name'),
                'last_name': user_info.get('last_name'),
                'profile_image_url': user_info.get('profile_image_url')
            }
            
            storage.upsert_user(UpsertUserSchema(
                id=user_info.get('sub'),
                email=user_info.get('email'),
                first_name=user_info.get('first_name'),
                last_name=user_info.get('last_name'),
                profile_image_url=user_info.get('profile_image_url')
            ))
        
        return redirect('/')
    except Exception as e:
        print(f"Auth callback error: {e}")
        return redirect('/api/login')

@app.route('/api/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/api/demo-login', methods=['POST'])
def demo_login():
    try:
        demo_user_id = 'demo-user-123'
        session['user'] = {
            'sub': demo_user_id,
            'email': 'demo@smartfinance.ai',
            'first_name': 'Demo',
            'last_name': 'User',
            'profile_image_url': None
        }
        
        storage.upsert_user(UpsertUserSchema(
            id=demo_user_id,
            email='demo@smartfinance.ai',
            first_name='Demo',
            last_name='User',
            profile_image_url=None
        ))
        
        return jsonify({"success": True, "message": "Demo login successful"})
    except Exception as e:
        print(f"Demo login error: {e}")
        return jsonify({"success": False, "message": "Failed to create demo session"}), 500

@app.route('/api/auth/user')
@is_authenticated
def get_auth_user():
    try:
        user_id = get_user_id()
        if not user_id:
            return jsonify({"message": "User ID not found in session"}), 401
        user = storage.get_user(user_id)
        if user:
            return jsonify(model_to_dict(user))
        return jsonify({"message": "User not found"}), 404
    except Exception as e:
        print(f"Error fetching user: {e}")
        return jsonify({"message": "Failed to fetch user"}), 500

@app.route('/api/user/preferences', methods=['GET'])
@is_authenticated
def get_user_preferences():
    try:
        user_id = get_user_id()
        if not user_id:
            return jsonify({"message": "User ID not found in session"}), 401
        
        preferences_file = f'user_preferences/{user_id}.json'
        
        default_preferences = {
            'theme': 'system',
            'customCategories': [
                'Food & Dining', 'Transportation', 'Shopping', 'Entertainment',
                'Bills & Utilities', 'Healthcare', 'Education', 'Travel',
                'Personal Care', 'Groceries', 'Rent', 'Insurance', 'Other'
            ]
        }
        
        try:
            if os.path.exists(preferences_file):
                with open(preferences_file, 'r') as f:
                    preferences = json.load(f)
                    return jsonify(preferences)
        except:
            pass
        
        return jsonify(default_preferences)
    except Exception as e:
        print(f"Error fetching preferences: {e}")
        return jsonify({"message": "Failed to fetch preferences"}), 500

@app.route('/api/user/preferences', methods=['PUT'])
@is_authenticated
def update_user_preferences():
    try:
        user_id = get_user_id()
        if not user_id:
            return jsonify({"message": "User ID not found in session"}), 401
        
        data = request.json
        
        if not data:
            return jsonify({"message": "No preferences data provided"}), 400
        
        os.makedirs('user_preferences', exist_ok=True)
        preferences_file = f'user_preferences/{user_id}.json'
        
        with open(preferences_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        return jsonify({"success": True, "message": "Preferences updated successfully", "preferences": data})
    except Exception as e:
        print(f"Error updating preferences: {e}")
        return jsonify({"message": "Failed to update preferences"}), 500

@app.route('/api/transactions', methods=['POST'])
@is_authenticated
def create_transaction():
    try:
        user_id = get_user_id()
        data = request.json
        data['user_id'] = user_id
        validated_data = InsertTransactionSchema(**data)
        transaction = storage.create_transaction(validated_data)
        return jsonify(model_to_dict(transaction))
    except ValidationError as e:
        return jsonify({"message": "Validation error", "errors": e.errors()}), 400
    except Exception as e:
        print(f"Error creating transaction: {e}")
        return jsonify({"message": "Failed to create transaction"}), 500

@app.route('/api/transactions', methods=['GET'])
@is_authenticated
def get_transactions():
    try:
        user_id = get_user_id()
        if not user_id:
            return jsonify({"message": "User ID not found in session"}), 401
        transactions = storage.get_transactions_by_user_id(user_id)
        return jsonify(models_to_dicts(transactions))
    except Exception as e:
        print(f"Error fetching transactions: {e}")
        return jsonify({"message": "Failed to fetch transactions"}), 500

@app.route('/api/transactions/detail/<transaction_id>', methods=['GET'])
@is_authenticated
def get_transaction_detail(transaction_id):
    try:
        user_id = get_user_id()
        transaction = storage.get_transaction_by_id(transaction_id)
        if not transaction or transaction.user_id != user_id:
            return jsonify({"message": "Transaction not found"}), 404
        return jsonify(model_to_dict(transaction))
    except Exception as e:
        print(f"Error fetching transaction: {e}")
        return jsonify({"message": "Failed to fetch transaction"}), 500

@app.route('/api/transactions/<transaction_id>', methods=['PATCH'])
@is_authenticated
def update_transaction(transaction_id):
    try:
        user_id = get_user_id()
        existing = storage.get_transaction_by_id(transaction_id)
        if not existing or existing.user_id != user_id:
            return jsonify({"message": "Transaction not found"}), 404
        
        data = request.json
        transaction = storage.update_transaction(transaction_id, data)
        return jsonify(model_to_dict(transaction))
    except ValidationError as e:
        return jsonify({"message": "Validation error", "errors": e.errors()}), 400
    except Exception as e:
        print(f"Error updating transaction: {e}")
        return jsonify({"message": "Failed to update transaction"}), 500

@app.route('/api/transactions/<transaction_id>', methods=['DELETE'])
@is_authenticated
def delete_transaction(transaction_id):
    try:
        user_id = get_user_id()
        existing = storage.get_transaction_by_id(transaction_id)
        if not existing or existing.user_id != user_id:
            return jsonify({"message": "Transaction not found"}), 404
        
        storage.delete_transaction(transaction_id)
        return jsonify({"message": "Transaction deleted successfully"})
    except Exception as e:
        print(f"Error deleting transaction: {e}")
        return jsonify({"message": "Failed to delete transaction"}), 500

@app.route('/api/transactions/ocr', methods=['POST'])
@is_authenticated
def ocr_transaction():
    try:
        if not openai_client:
            return jsonify({"message": "OCR is currently unavailable. Please configure OPENAI_API_KEY environment variable."}), 503
        
        data = request.json
        image = data.get('image')
        
        if not image or not isinstance(image, str):
            return jsonify({"message": "Invalid image data. Please provide base64 encoded image."}), 400
        
        image_data = re.sub(r'^data:image/\w+;base64,', '', image)
        
        extracted_data = extract_transaction_from_image(image_data, openai_client)
        
        return jsonify(extracted_data.to_dict())
    except Exception as e:
        print(f"OCR error: {e}")
        return jsonify({"message": str(e) or "Failed to extract transaction from image"}), 500

@app.route('/api/imports/transactions', methods=['POST'])
@is_authenticated
def import_transactions():
    try:
        user_id = get_user_id()
        if not user_id:
            return jsonify({"message": "User ID not found in session"}), 401
        
        if 'file' not in request.files:
            return jsonify({"message": "No file uploaded"}), 400
        
        file = request.files['file']
        if not file.filename:
            return jsonify({"message": "No file selected"}), 400
        
        filename = file.filename.lower()
        column_mapping = json.loads(request.form.get('columnMapping', '{}'))
        
        rows = []
        if filename.endswith('.csv'):
            content = io.StringIO(file.read().decode('utf-8'))
            reader = csv.DictReader(content)
            rows = list(reader)
        elif filename.endswith('.xlsx'):
            workbook = openpyxl.load_workbook(file, read_only=True)
            sheet = workbook.active
            headers = [cell.value for cell in sheet[1]]
            for row in sheet.iter_rows(min_row=2, values_only=True):
                rows.append(dict(zip(headers, row)))
        else:
            return jsonify({"message": "Unsupported file format. Please upload CSV or XLSX file."}), 400
        
        if not rows:
            return jsonify({"message": "No data found in file"}), 400
        
        auto_detected_mapping = {}
        if rows:
            first_row_keys = list(rows[0].keys())
            for key in first_row_keys:
                key_lower = str(key).lower() if key else ""
                if any(term in key_lower for term in ['date', 'transaction date', 'posted date']):
                    auto_detected_mapping['date'] = key
                elif any(term in key_lower for term in ['description', 'title', 'memo', 'details', 'payee']):
                    auto_detected_mapping['description'] = key
                elif any(term in key_lower for term in ['amount', 'value', 'total']):
                    auto_detected_mapping['amount'] = key
                elif any(term in key_lower for term in ['category', 'type']):
                    auto_detected_mapping['category'] = key
                elif any(term in key_lower for term in ['debit', 'withdrawal']):
                    auto_detected_mapping['debit'] = key
                elif any(term in key_lower for term in ['credit', 'deposit']):
                    auto_detected_mapping['credit'] = key
        
        mapping = {**auto_detected_mapping, **column_mapping}
        
        transactions_to_create = []
        errors = []
        skipped = 0
        
        for idx, row in enumerate(rows):
            try:
                date_str = str(row.get(mapping.get('date', ''), '')).strip()
                if not date_str or date_str == 'None':
                    errors.append({"row": idx + 2, "message": "Missing date"})
                    continue
                
                try:
                    parsed_date = date_parser.parse(date_str).date()
                except:
                    errors.append({"row": idx + 2, "message": f"Invalid date format: {date_str}"})
                    continue
                
                description = str(row.get(mapping.get('description', ''), '')).strip()
                if not description or description == 'None':
                    errors.append({"row": idx + 2, "message": "Missing description"})
                    continue
                
                amount = None
                transaction_type = None
                
                if mapping.get('debit') and mapping.get('credit'):
                    debit_str = str(row.get(mapping.get('debit', ''), '')).strip()
                    credit_str = str(row.get(mapping.get('credit', ''), '')).strip()
                    
                    if debit_str and debit_str != 'None':
                        amount_str = re.sub(r'[^\d.-]', '', debit_str)
                        amount = Decimal(amount_str) if amount_str else Decimal(0)
                        transaction_type = 'expense'
                    elif credit_str and credit_str != 'None':
                        amount_str = re.sub(r'[^\d.-]', '', credit_str)
                        amount = Decimal(amount_str) if amount_str else Decimal(0)
                        transaction_type = 'income'
                    else:
                        errors.append({"row": idx + 2, "message": "Missing amount in debit/credit columns"})
                        continue
                else:
                    amount_str = str(row.get(mapping.get('amount', ''), '')).strip()
                    if not amount_str or amount_str == 'None':
                        errors.append({"row": idx + 2, "message": "Missing amount"})
                        continue
                    
                    amount_str = re.sub(r'[^\d.-]', '', amount_str)
                    try:
                        amount = Decimal(amount_str)
                        transaction_type = 'expense' if amount < 0 else 'income'
                        amount = abs(amount)
                    except:
                        errors.append({"row": idx + 2, "message": f"Invalid amount: {amount_str}"})
                        continue
                
                category = str(row.get(mapping.get('category', ''), 'Other')).strip()
                if not category or category == 'None':
                    category = 'Other'
                
                external_id = f"{user_id}_{parsed_date}_{description}_{amount}"
                
                transaction_data = InsertTransactionSchema(
                    user_id=user_id,
                    title=description,
                    amount=amount,
                    category=category,
                    type=transaction_type,
                    date=parsed_date,
                    external_id=external_id,
                    source='excel' if filename.endswith('.xlsx') else 'csv'
                )
                transactions_to_create.append(transaction_data)
                
            except ValidationError as e:
                errors.append({"row": idx + 2, "message": f"Validation error: {str(e)}"})
            except Exception as e:
                errors.append({"row": idx + 2, "message": str(e)})
        
        imported_count = 0
        if transactions_to_create:
            created = storage.bulk_create_transactions(user_id, transactions_to_create)
            imported_count = len(created)
            skipped = len(transactions_to_create) - imported_count
        
        return jsonify({
            "imported": imported_count,
            "skipped": skipped,
            "errors": errors[:100]
        })
        
    except Exception as e:
        print(f"Import error: {e}")
        return jsonify({"message": f"Failed to import transactions: {str(e)}"}), 500

@app.route('/api/budgets', methods=['POST'])
@is_authenticated
def create_budget():
    try:
        user_id = get_user_id()
        if not user_id:
            return jsonify({"message": "User ID not found in session"}), 401
        data = request.json
        data['user_id'] = user_id
        validated_data = InsertBudgetSchema(**data)
        budget = storage.create_budget(validated_data)
        return jsonify(model_to_dict(budget))
    except ValidationError as e:
        return jsonify({"message": "Validation error", "errors": e.errors()}), 400
    except Exception as e:
        print(f"Error creating budget: {e}")
        return jsonify({"message": "Failed to create budget"}), 500

@app.route('/api/budgets', methods=['GET'])
@is_authenticated
def get_budgets():
    try:
        user_id = get_user_id()
        if not user_id:
            return jsonify({"message": "User ID not found in session"}), 401
        month = request.args.get('month')
        budgets = storage.get_budgets_by_user_id(user_id, month)
        return jsonify(models_to_dicts(budgets))
    except Exception as e:
        print(f"Error fetching budgets: {e}")
        return jsonify({"message": "Failed to fetch budgets"}), 500

@app.route('/api/budgets/<budget_id>', methods=['PATCH'])
@is_authenticated
def update_budget(budget_id):
    try:
        user_id = get_user_id()
        existing = storage.get_budget_by_id(budget_id)
        if not existing or existing.user_id != user_id:
            return jsonify({"message": "Budget not found"}), 404
        
        data = request.json
        budget = storage.update_budget(budget_id, data)
        return jsonify(model_to_dict(budget))
    except ValidationError as e:
        return jsonify({"message": "Validation error", "errors": e.errors()}), 400
    except Exception as e:
        print(f"Error updating budget: {e}")
        return jsonify({"message": "Failed to update budget"}), 500

@app.route('/api/budgets/<budget_id>', methods=['DELETE'])
@is_authenticated
def delete_budget(budget_id):
    try:
        user_id = get_user_id()
        existing = storage.get_budget_by_id(budget_id)
        if not existing or existing.user_id != user_id:
            return jsonify({"message": "Budget not found"}), 404
        
        storage.delete_budget(budget_id)
        return jsonify({"message": "Budget deleted successfully"})
    except Exception as e:
        print(f"Error deleting budget: {e}")
        return jsonify({"message": "Failed to delete budget"}), 500

@app.route('/api/goals', methods=['POST'])
@is_authenticated
def create_goal():
    try:
        user_id = get_user_id()
        if not user_id:
            return jsonify({"message": "User ID not found in session"}), 401
        data = request.json
        data['user_id'] = user_id
        validated_data = InsertGoalSchema(**data)
        goal = storage.create_goal(validated_data)
        return jsonify(model_to_dict(goal))
    except ValidationError as e:
        return jsonify({"message": "Validation error", "errors": e.errors()}), 400
    except Exception as e:
        print(f"Error creating goal: {e}")
        return jsonify({"message": "Failed to create goal"}), 500

@app.route('/api/goals', methods=['GET'])
@is_authenticated
def get_goals():
    try:
        user_id = get_user_id()
        if not user_id:
            return jsonify({"message": "User ID not found in session"}), 401
        goals = storage.get_goals_by_user_id(user_id)
        return jsonify(models_to_dicts(goals))
    except Exception as e:
        print(f"Error fetching goals: {e}")
        return jsonify({"message": "Failed to fetch goals"}), 500

@app.route('/api/goals/<goal_id>', methods=['PATCH'])
@is_authenticated
def update_goal(goal_id):
    try:
        user_id = get_user_id()
        existing = storage.get_goal_by_id(goal_id)
        if not existing or existing.user_id != user_id:
            return jsonify({"message": "Goal not found"}), 404
        
        data = request.json
        goal = storage.update_goal(goal_id, data)
        return jsonify(model_to_dict(goal))
    except ValidationError as e:
        return jsonify({"message": "Validation error", "errors": e.errors()}), 400
    except Exception as e:
        print(f"Error updating goal: {e}")
        return jsonify({"message": "Failed to update goal"}), 500

@app.route('/api/goals/<goal_id>', methods=['DELETE'])
@is_authenticated
def delete_goal(goal_id):
    try:
        user_id = get_user_id()
        existing = storage.get_goal_by_id(goal_id)
        if not existing or existing.user_id != user_id:
            return jsonify({"message": "Goal not found"}), 404
        
        storage.delete_goal(goal_id)
        return jsonify({"message": "Goal deleted successfully"})
    except Exception as e:
        print(f"Error deleting goal: {e}")
        return jsonify({"message": "Failed to delete goal"}), 500

@app.route('/api/bills', methods=['POST'])
@is_authenticated
def create_bill():
    try:
        user_id = get_user_id()
        if not user_id:
            return jsonify({"message": "User ID not found in session"}), 401
        data = request.json
        data['user_id'] = user_id
        validated_data = InsertBillSchema(**data)
        bill = storage.create_bill(validated_data)
        return jsonify(model_to_dict(bill))
    except ValidationError as e:
        return jsonify({"message": "Validation error", "errors": e.errors()}), 400
    except Exception as e:
        print(f"Error creating bill: {e}")
        return jsonify({"message": "Failed to create bill"}), 500

@app.route('/api/bills', methods=['GET'])
@is_authenticated
def get_bills():
    try:
        user_id = get_user_id()
        if not user_id:
            return jsonify({"message": "User ID not found in session"}), 401
        bills = storage.get_bills_by_user_id(user_id)
        return jsonify(models_to_dicts(bills))
    except Exception as e:
        print(f"Error fetching bills: {e}")
        return jsonify({"message": "Failed to fetch bills"}), 500

@app.route('/api/bills/<bill_id>', methods=['PATCH'])
@is_authenticated
def update_bill(bill_id):
    try:
        user_id = get_user_id()
        existing = storage.get_bill_by_id(bill_id)
        if not existing or existing.user_id != user_id:
            return jsonify({"message": "Bill not found"}), 404
        
        data = request.json
        bill = storage.update_bill(bill_id, data)
        return jsonify(model_to_dict(bill))
    except ValidationError as e:
        return jsonify({"message": "Validation error", "errors": e.errors()}), 400
    except Exception as e:
        print(f"Error updating bill: {e}")
        return jsonify({"message": "Failed to update bill"}), 500

@app.route('/api/bills/<bill_id>', methods=['DELETE'])
@is_authenticated
def delete_bill(bill_id):
    try:
        user_id = get_user_id()
        existing = storage.get_bill_by_id(bill_id)
        if not existing or existing.user_id != user_id:
            return jsonify({"message": "Bill not found"}), 404
        
        storage.delete_bill(bill_id)
        return jsonify({"message": "Bill deleted successfully"})
    except Exception as e:
        print(f"Error deleting bill: {e}")
        return jsonify({"message": "Failed to delete bill"}), 500

@app.route('/api/health-score', methods=['GET'])
@is_authenticated
def get_health_score():
    try:
        user_id = get_user_id()
        if not user_id:
            return jsonify({"message": "User ID not found in session"}), 401
        
        transactions = storage.get_transactions_by_user_id(user_id)
        budgets = storage.get_budgets_by_user_id(user_id)
        goals = storage.get_goals_by_user_id(user_id)
        bills = storage.get_bills_by_user_id(user_id)
        
        health_score = calculate_health_score(transactions, budgets, goals, bills)
        
        return jsonify(health_score.to_dict())
    except Exception as e:
        print(f"Health score calculation error: {e}")
        return jsonify({"message": "Failed to calculate health score"}), 500

@app.route('/api/ai/chat', methods=['POST'])
@is_authenticated
def ai_chat():
    try:
        if not openai_client:
            return jsonify({"message": "AI chat is currently unavailable. Please configure OPENAI_API_KEY environment variable."}), 503
        
        user_id = get_user_id()
        if not user_id:
            return jsonify({"message": "User ID not found in session"}), 401
        data = request.json
        messages = data.get('messages', [])
        
        if not messages or not isinstance(messages, list):
            return jsonify({"message": "Invalid messages format"}), 400
        
        transactions = storage.get_transactions_by_user_id(user_id)
        budgets = storage.get_budgets_by_user_id(user_id)
        goals = storage.get_goals_by_user_id(user_id)
        bills = storage.get_bills_by_user_id(user_id)
        
        spending_by_category = {}
        for t in transactions:
            if t.type == "expense":
                category = t.category
                spending_by_category[category] = spending_by_category.get(category, 0) + float(t.amount)
        
        now = datetime.now()
        current_month = f"{now.year}-{str(now.month).zfill(2)}"
        last_month_date = datetime(now.year, now.month - 1 if now.month > 1 else 12, 1)
        last_month_str = f"{last_month_date.year}-{str(last_month_date.month).zfill(2)}"
        
        current_month_expenses = sum(float(t.amount) for t in transactions if t.type == "expense" and str(t.date).startswith(current_month))
        last_month_expenses = sum(float(t.amount) for t in transactions if t.type == "expense" and str(t.date).startswith(last_month_str))
        
        total_income = sum(float(t.amount) for t in transactions if t.type == "income")
        total_expenses = sum(float(t.amount) for t in transactions if t.type == "expense")
        
        category_breakdown = "\n".join([f"  - {cat}: ₹{amt:,.2f}" for cat, amt in spending_by_category.items()]) or "  No expenses recorded"
        
        recent_transactions = "\n".join([f"  - {t.date}: {t.title} ({t.category}) - ₹{float(t.amount):,.2f} [{t.type}]" for t in transactions[:10]]) or "  No transactions yet"
        
        upcoming_bills_list = [b for b in bills if b.due_date >= date.today()][:5]
        upcoming_bills = "\n".join([f"  - {b.name}: ₹{float(b.amount):,.0f} due on {b.due_date}" for b in upcoming_bills_list]) or "  No upcoming bills"
        
        goals_info = "\n".join([f"  - {g.title}: ₹{float(g.current_amount):,.0f} / ₹{float(g.target_amount):,.0f} ({(float(g.current_amount) / float(g.target_amount) * 100):.0f}%)" for g in goals[:5]]) or "  No active goals"
        
        system_message = {
            "role": "system",
            "content": f"""You are SmartFinance.AI, a helpful personal finance assistant for Indian users. Analyze the user's actual financial data and provide clear, actionable advice using Indian Rupees (₹).

IMPORTANT FORMATTING RULES:
- ALWAYS use ₹ (Indian Rupee) symbol for all amounts
- NEVER use asterisks (*) for bold or emphasis
- NEVER use markdown formatting symbols
- Use simple bullet points with dashes (-)
- Use plain text only
- Use line breaks for clarity
- Use emojis sparingly (💰 📊 ✅ ⚠️ 💡)

USER'S FINANCIAL DATA:

Summary:
  Total Income: ₹{total_income:,.2f}
  Total Expenses: ₹{total_expenses:,.2f}
  Net Balance: ₹{(total_income - total_expenses):,.2f}
  
Monthly Comparison:
  Current Month Spending: ₹{current_month_expenses:,.2f}
  Last Month Spending: ₹{last_month_expenses:,.2f}
  Change: {'+' if current_month_expenses > last_month_expenses else ''}₹{abs(current_month_expenses - last_month_expenses):,.2f}

Spending by Category:
{category_breakdown}

Active Budgets: {len(budgets)}
Savings Goals: {len(goals)}

Goals Progress:
{goals_info}

Upcoming Bills: {len(upcoming_bills_list)}
{upcoming_bills}

Recent Transactions (last 10):
{recent_transactions}

HOW TO RESPOND:
1. Answer questions using the actual data above
2. Be specific - use real numbers from their transactions
3. Always use ₹ symbol for amounts
4. Structure responses with clear sections (use line breaks)
5. Keep it conversational and easy to understand
6. Provide actionable tips based on their spending patterns
7. NO markdown symbols - plain text only
8. Reference their actual budgets, goals, and bills when relevant

Remember: Be helpful, specific, and use their actual data!"""
        }
        
        completion = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[system_message] + messages,
            temperature=0.7,
            max_tokens=500
        )
        
        return jsonify({"message": completion.choices[0].message.content})
    except Exception as e:
        print(f"OpenAI API error: {e}")
        return jsonify({"message": "Failed to get AI response"}), 500

@app.route('/api/ai/categorize', methods=['POST'])
@is_authenticated
def ai_categorize_transaction():
    try:
        if not openai_client:
            return jsonify({"message": "AI categorization is currently unavailable. Please configure OPENAI_API_KEY environment variable."}), 503
        
        data = request.json
        description = data.get('description', '').strip()
        
        if not description:
            return jsonify({"message": "Description is required"}), 400
        
        categories = [
            "Food & Dining", "Transportation", "Shopping", "Entertainment",
            "Bills & Utilities", "Healthcare", "Education", "Travel",
            "Personal Care", "Groceries", "Rent", "Insurance", "Other"
        ]
        
        completion = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": f"""You are a financial categorization assistant. Given a transaction description, 
                    suggest the most appropriate category from this list: {', '.join(categories)}.
                    
                    Respond ONLY with the category name, nothing else."""
                },
                {
                    "role": "user",
                    "content": f"Categorize this transaction: {description}"
                }
            ],
            temperature=0.3,
            max_tokens=50
        )
        
        suggested_category = completion.choices[0].message.content.strip()
        
        if suggested_category not in categories:
            suggested_category = "Other"
        
        return jsonify({"category": suggested_category})
    except Exception as e:
        print(f"AI categorization error: {e}")
        return jsonify({"message": "Failed to categorize transaction"}), 500

@app.route('/api/ai/categorize/batch', methods=['POST'])
@is_authenticated
def ai_categorize_batch():
    try:
        if not openai_client:
            return jsonify({"message": "AI categorization is currently unavailable. Please configure OPENAI_API_KEY environment variable."}), 503
        
        user_id = get_user_id()
        if not user_id:
            return jsonify({"message": "User ID not found in session"}), 401
        
        data = request.json
        transaction_ids = data.get('transaction_ids', [])
        
        if not transaction_ids:
            return jsonify({"message": "No transaction IDs provided"}), 400
        
        categories = [
            "Food & Dining", "Transportation", "Shopping", "Entertainment",
            "Bills & Utilities", "Healthcare", "Education", "Travel",
            "Personal Care", "Groceries", "Rent", "Insurance", "Other"
        ]
        
        suggestions = []
        
        for transaction_id in transaction_ids:
            transaction = storage.get_transaction_by_id(transaction_id)
            
            if not transaction or transaction.user_id != user_id:
                continue
            
            try:
                completion = openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": f"""You are a financial categorization assistant. Given a transaction description, 
                            suggest the most appropriate category from this list: {', '.join(categories)}.
                            
                            Respond ONLY with the category name, nothing else."""
                        },
                        {
                            "role": "user",
                            "content": f"Categorize this transaction: {transaction.title}"
                        }
                    ],
                    temperature=0.3,
                    max_tokens=50
                )
                
                suggested_category = completion.choices[0].message.content.strip()
                
                if suggested_category not in categories:
                    suggested_category = "Other"
                
                suggestions.append({
                    "transaction_id": transaction_id,
                    "current_category": transaction.category,
                    "suggested_category": suggested_category,
                    "title": transaction.title
                })
            except Exception as e:
                print(f"Error categorizing transaction {transaction_id}: {e}")
                continue
        
        return jsonify({"suggestions": suggestions})
    except Exception as e:
        print(f"Batch categorization error: {e}")
        return jsonify({"message": "Failed to categorize transactions"}), 500

@app.route('/api/reports/transactions', methods=['GET'])
@is_authenticated
def export_transactions():
    try:
        user_id = get_user_id()
        if not user_id:
            return jsonify({"message": "User ID not found in session"}), 401
        
        format_type = request.args.get('format', 'csv').lower()
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if format_type not in ['csv', 'pdf']:
            return jsonify({"message": "Invalid format. Use 'csv' or 'pdf'"}), 400
        
        transactions = storage.get_transactions_by_user_id(user_id)
        
        if start_date:
            transactions = [t for t in transactions if str(t.date) >= start_date]
        if end_date:
            transactions = [t for t in transactions if str(t.date) <= end_date]
        
        if format_type == 'csv':
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(['Date', 'Title', 'Category', 'Type', 'Amount'])
            
            for t in transactions:
                writer.writerow([
                    str(t.date),
                    t.title,
                    t.category,
                    t.type,
                    str(t.amount)
                ])
            
            response = make_response(output.getvalue())
            response.headers['Content-Disposition'] = 'attachment; filename=transactions.csv'
            response.headers['Content-Type'] = 'text/csv'
            return response
        
        else:
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            elements = []
            
            styles = getSampleStyleSheet()
            title = Paragraph("Transactions Report", styles['Title'])
            elements.append(title)
            elements.append(Spacer(1, 0.3 * inch))
            
            if start_date or end_date:
                date_range = f"Period: {start_date or 'Beginning'} to {end_date or 'Present'}"
                date_para = Paragraph(date_range, styles['Normal'])
                elements.append(date_para)
                elements.append(Spacer(1, 0.2 * inch))
            
            data = [['Date', 'Title', 'Category', 'Type', 'Amount (₹)']]
            total_income = 0
            total_expense = 0
            
            for t in transactions:
                data.append([
                    str(t.date),
                    t.title,
                    t.category,
                    t.type.capitalize(),
                    f"{float(t.amount):,.2f}"
                ])
                if t.type == 'income':
                    total_income += float(t.amount)
                else:
                    total_expense += float(t.amount)
            
            data.append(['', '', '', 'Total Income:', f"{total_income:,.2f}"])
            data.append(['', '', '', 'Total Expense:', f"{total_expense:,.2f}"])
            data.append(['', '', '', 'Net Balance:', f"{total_income - total_expense:,.2f}"])
            
            table = Table(data, colWidths=[1.2*inch, 2*inch, 1.2*inch, 1*inch, 1.2*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -4), colors.beige),
                ('GRID', (0, 0), (-1, -4), 1, colors.black),
                ('FONTNAME', (0, -3), (-1, -1), 'Helvetica-Bold'),
                ('BACKGROUND', (0, -3), (-1, -1), colors.lightgrey),
                ('ALIGN', (4, 1), (4, -1), 'RIGHT'),
            ]))
            
            elements.append(table)
            doc.build(elements)
            
            buffer.seek(0)
            response = make_response(buffer.getvalue())
            response.headers['Content-Disposition'] = 'attachment; filename=transactions.pdf'
            response.headers['Content-Type'] = 'application/pdf'
            return response
            
    except Exception as e:
        print(f"Error exporting transactions: {e}")
        return jsonify({"message": "Failed to export transactions"}), 500

@app.route('/api/reports/budgets', methods=['GET'])
@is_authenticated
def export_budgets():
    try:
        user_id = get_user_id()
        if not user_id:
            return jsonify({"message": "User ID not found in session"}), 401
        
        format_type = request.args.get('format', 'csv').lower()
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if format_type not in ['csv', 'pdf']:
            return jsonify({"message": "Invalid format. Use 'csv' or 'pdf'"}), 400
        
        budgets = storage.get_budgets_by_user_id(user_id)
        transactions = storage.get_transactions_by_user_id(user_id)
        
        budget_data = []
        for budget in budgets:
            if start_date and budget.month < start_date[:7]:
                continue
            if end_date and budget.month > end_date[:7]:
                continue
            
            spent = sum(
                float(t.amount) for t in transactions
                if t.type == 'expense' 
                and t.category == budget.category 
                and str(t.date).startswith(budget.month)
            )
            
            budget_data.append({
                'month': budget.month,
                'category': budget.category,
                'budget': float(budget.amount),
                'spent': spent,
                'remaining': float(budget.amount) - spent,
                'percentage': (spent / float(budget.amount) * 100) if float(budget.amount) > 0 else 0
            })
        
        if format_type == 'csv':
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(['Month', 'Category', 'Budget Amount', 'Spent', 'Remaining', 'Usage %'])
            
            for b in budget_data:
                writer.writerow([
                    b['month'],
                    b['category'],
                    f"{b['budget']:.2f}",
                    f"{b['spent']:.2f}",
                    f"{b['remaining']:.2f}",
                    f"{b['percentage']:.1f}%"
                ])
            
            response = make_response(output.getvalue())
            response.headers['Content-Disposition'] = 'attachment; filename=budgets.csv'
            response.headers['Content-Type'] = 'text/csv'
            return response
        
        else:
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            elements = []
            
            styles = getSampleStyleSheet()
            title = Paragraph("Budget Report", styles['Title'])
            elements.append(title)
            elements.append(Spacer(1, 0.3 * inch))
            
            if start_date or end_date:
                date_range = f"Period: {start_date or 'Beginning'} to {end_date or 'Present'}"
                date_para = Paragraph(date_range, styles['Normal'])
                elements.append(date_para)
                elements.append(Spacer(1, 0.2 * inch))
            
            data = [['Month', 'Category', 'Budget (₹)', 'Spent (₹)', 'Remaining (₹)', 'Usage %']]
            
            total_budget = 0
            total_spent = 0
            
            for b in budget_data:
                data.append([
                    b['month'],
                    b['category'],
                    f"{b['budget']:,.2f}",
                    f"{b['spent']:,.2f}",
                    f"{b['remaining']:,.2f}",
                    f"{b['percentage']:.1f}%"
                ])
                total_budget += b['budget']
                total_spent += b['spent']
            
            data.append(['', 'TOTAL', f"{total_budget:,.2f}", f"{total_spent:,.2f}", 
                        f"{total_budget - total_spent:,.2f}", 
                        f"{(total_spent/total_budget*100) if total_budget > 0 else 0:.1f}%"])
            
            table = Table(data, colWidths=[1*inch, 1.5*inch, 1.2*inch, 1.2*inch, 1.2*inch, 1*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
                ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
            ]))
            
            elements.append(table)
            doc.build(elements)
            
            buffer.seek(0)
            response = make_response(buffer.getvalue())
            response.headers['Content-Disposition'] = 'attachment; filename=budgets.pdf'
            response.headers['Content-Type'] = 'application/pdf'
            return response
            
    except Exception as e:
        print(f"Error exporting budgets: {e}")
        return jsonify({"message": "Failed to export budgets"}), 500

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('NODE_ENV') != 'production')
