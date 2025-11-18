import os
import uuid
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker, Session as DBSession
from typing import Optional, List
from models import (
    Base, User, Transaction, Budget, Goal, Bill,
    UpsertUserSchema, InsertTransactionSchema, InsertBudgetSchema,
    InsertGoalSchema, InsertBillSchema
)
from datetime import datetime

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class InMemoryStorage:
    """In-memory storage implementation for demo mode when DATABASE_URL is not set"""
    
    def __init__(self):
        self.users = {}
        self.transactions = {}
        self.budgets = {}
        self.goals = {}
        self.bills = {}
    
    def get_user(self, user_id: str) -> Optional[User]:
        return self.users.get(user_id)
    
    def upsert_user(self, user_data: UpsertUserSchema) -> User:
        user_id = user_data.id
        if user_id in self.users:
            user = self.users[user_id]
            for key, value in user_data.model_dump(exclude_unset=True).items():
                if key != 'updated_at':
                    setattr(user, key, value)
            user.updated_at = datetime.now()
        else:
            user_dict = user_data.model_dump()
            user_dict['created_at'] = datetime.now()
            user_dict['updated_at'] = datetime.now()
            user = User(**user_dict)
            self.users[user_id] = user
        return user
    
    def create_transaction(self, transaction_data: InsertTransactionSchema) -> Transaction:
        transaction_dict = transaction_data.model_dump()
        transaction_dict['id'] = str(uuid.uuid4())
        transaction_dict['created_at'] = datetime.now()
        transaction = Transaction(**transaction_dict)
        self.transactions[transaction.id] = transaction
        return transaction
    
    def get_transactions_by_user_id(self, user_id: str) -> List[Transaction]:
        transactions = [t for t in self.transactions.values() if t.user_id == user_id]
        return sorted(transactions, key=lambda x: x.date, reverse=True)
    
    def get_transaction_by_id(self, transaction_id: str) -> Optional[Transaction]:
        return self.transactions.get(transaction_id)
    
    def update_transaction(self, transaction_id: str, transaction_data: dict) -> Optional[Transaction]:
        transaction = self.transactions.get(transaction_id)
        if transaction:
            for key, value in transaction_data.items():
                if hasattr(transaction, key):
                    setattr(transaction, key, value)
        return transaction
    
    def delete_transaction(self, transaction_id: str) -> None:
        if transaction_id in self.transactions:
            del self.transactions[transaction_id]
    
    def bulk_create_transactions(self, user_id: str, transactions_list: List[InsertTransactionSchema]) -> List[Transaction]:
        created_transactions = []
        existing_external_ids = {
            t.external_id for t in self.transactions.values()
            if t.user_id == user_id and t.external_id
        }
        
        for transaction_data in transactions_list:
            if transaction_data.external_id and transaction_data.external_id in existing_external_ids:
                continue
            
            transaction_dict = transaction_data.model_dump()
            transaction_dict['id'] = str(uuid.uuid4())
            transaction_dict['created_at'] = datetime.now()
            transaction = Transaction(**transaction_dict)
            self.transactions[transaction.id] = transaction
            created_transactions.append(transaction)
        
        return created_transactions
    
    def create_budget(self, budget_data: InsertBudgetSchema) -> Budget:
        budget_dict = budget_data.model_dump()
        budget_dict['id'] = str(uuid.uuid4())
        budget_dict['created_at'] = datetime.now()
        budget = Budget(**budget_dict)
        self.budgets[budget.id] = budget
        return budget
    
    def get_budgets_by_user_id(self, user_id: str, month: Optional[str] = None) -> List[Budget]:
        budgets = [b for b in self.budgets.values() if b.user_id == user_id]
        if month:
            budgets = [b for b in budgets if b.month == month]
        return budgets
    
    def get_budget_by_id(self, budget_id: str) -> Optional[Budget]:
        return self.budgets.get(budget_id)
    
    def update_budget(self, budget_id: str, budget_data: dict) -> Optional[Budget]:
        budget = self.budgets.get(budget_id)
        if budget:
            for key, value in budget_data.items():
                if hasattr(budget, key):
                    setattr(budget, key, value)
        return budget
    
    def delete_budget(self, budget_id: str) -> None:
        if budget_id in self.budgets:
            del self.budgets[budget_id]
    
    def create_goal(self, goal_data: InsertGoalSchema) -> Goal:
        goal_dict = goal_data.model_dump()
        goal_dict['id'] = str(uuid.uuid4())
        goal_dict['created_at'] = datetime.now()
        goal = Goal(**goal_dict)
        self.goals[goal.id] = goal
        return goal
    
    def get_goals_by_user_id(self, user_id: str) -> List[Goal]:
        goals = [g for g in self.goals.values() if g.user_id == user_id]
        return sorted(goals, key=lambda x: x.created_at, reverse=True)
    
    def get_goal_by_id(self, goal_id: str) -> Optional[Goal]:
        return self.goals.get(goal_id)
    
    def update_goal(self, goal_id: str, goal_data: dict) -> Optional[Goal]:
        goal = self.goals.get(goal_id)
        if goal:
            for key, value in goal_data.items():
                if hasattr(goal, key):
                    setattr(goal, key, value)
        return goal
    
    def delete_goal(self, goal_id: str) -> None:
        if goal_id in self.goals:
            del self.goals[goal_id]
    
    def create_bill(self, bill_data: InsertBillSchema) -> Bill:
        bill_dict = bill_data.model_dump()
        bill_dict['id'] = str(uuid.uuid4())
        bill_dict['created_at'] = datetime.now()
        bill = Bill(**bill_dict)
        self.bills[bill.id] = bill
        return bill
    
    def get_bills_by_user_id(self, user_id: str) -> List[Bill]:
        bills = [b for b in self.bills.values() if b.user_id == user_id]
        return sorted(bills, key=lambda x: x.due_date)
    
    def get_bill_by_id(self, bill_id: str) -> Optional[Bill]:
        return self.bills.get(bill_id)
    
    def update_bill(self, bill_id: str, bill_data: dict) -> Optional[Bill]:
        bill = self.bills.get(bill_id)
        if bill:
            for key, value in bill_data.items():
                if hasattr(bill, key):
                    setattr(bill, key, value)
        return bill
    
    def delete_bill(self, bill_id: str) -> None:
        if bill_id in self.bills:
            del self.bills[bill_id]

class Storage:
    def __init__(self):
        self.engine = engine
        if not engine:
            print("WARNING: Storage initialized without database connection")
    
    def _get_session(self) -> Optional[DBSession]:
        if not SessionLocal:
            raise RuntimeError("Database not configured. Set DATABASE_URL environment variable.")
        return SessionLocal()
    
    def get_user(self, user_id: str) -> Optional[User]:
        db = self._get_session()
        try:
            return db.query(User).filter(User.id == user_id).first()
        finally:
            db.close()
    
    def upsert_user(self, user_data: UpsertUserSchema) -> User:
        db = self._get_session()
        try:
            user = db.query(User).filter(User.id == user_data.id).first()
            if user:
                for key, value in user_data.model_dump(exclude_unset=True).items():
                    if key != 'updated_at':
                        setattr(user, key, value)
                setattr(user, 'updated_at', datetime.now())
            else:
                user = User(**user_data.model_dump())
                db.add(user)
            db.commit()
            db.refresh(user)
            return user
        finally:
            db.close()
    
    def create_transaction(self, transaction_data: InsertTransactionSchema) -> Transaction:
        db = self._get_session()
        try:
            transaction = Transaction(**transaction_data.model_dump())
            db.add(transaction)
            db.commit()
            db.refresh(transaction)
            return transaction
        finally:
            db.close()
    
    def get_transactions_by_user_id(self, user_id: str) -> List[Transaction]:
        db = self._get_session()
        try:
            return db.query(Transaction).filter(
                Transaction.user_id == user_id
            ).order_by(desc(Transaction.date)).all()
        finally:
            db.close()
    
    def get_transaction_by_id(self, transaction_id: str) -> Optional[Transaction]:
        db = self._get_session()
        try:
            return db.query(Transaction).filter(Transaction.id == transaction_id).first()
        finally:
            db.close()
    
    def update_transaction(self, transaction_id: str, transaction_data: dict) -> Optional[Transaction]:
        db = self._get_session()
        try:
            transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
            if transaction:
                for key, value in transaction_data.items():
                    if hasattr(transaction, key):
                        setattr(transaction, key, value)
                db.commit()
                db.refresh(transaction)
            return transaction
        finally:
            db.close()
    
    def delete_transaction(self, transaction_id: str) -> None:
        db = self._get_session()
        try:
            transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
            if transaction:
                db.delete(transaction)
                db.commit()
        finally:
            db.close()
    
    def bulk_create_transactions(self, user_id: str, transactions_list: List[InsertTransactionSchema]) -> List[Transaction]:
        db = self._get_session()
        try:
            created_transactions = []
            existing_external_ids = set()
            
            transactions_with_external_id = [t for t in transactions_list if t.external_id]
            if transactions_with_external_id:
                external_ids = [t.external_id for t in transactions_with_external_id]
                existing = db.query(Transaction.external_id).filter(
                    Transaction.user_id == user_id,
                    Transaction.external_id.in_(external_ids)
                ).all()
                existing_external_ids = {e[0] for e in existing}
            
            for transaction_data in transactions_list:
                if transaction_data.external_id and transaction_data.external_id in existing_external_ids:
                    continue
                
                transaction = Transaction(**transaction_data.model_dump())
                db.add(transaction)
                created_transactions.append(transaction)
            
            db.commit()
            for transaction in created_transactions:
                db.refresh(transaction)
            
            return created_transactions
        finally:
            db.close()
    
    def create_budget(self, budget_data: InsertBudgetSchema) -> Budget:
        db = self._get_session()
        try:
            budget = Budget(**budget_data.model_dump())
            db.add(budget)
            db.commit()
            db.refresh(budget)
            return budget
        finally:
            db.close()
    
    def get_budgets_by_user_id(self, user_id: str, month: Optional[str] = None) -> List[Budget]:
        db = self._get_session()
        try:
            query = db.query(Budget).filter(Budget.user_id == user_id)
            if month:
                query = query.filter(Budget.month == month)
            return query.all()
        finally:
            db.close()
    
    def get_budget_by_id(self, budget_id: str) -> Optional[Budget]:
        db = self._get_session()
        try:
            return db.query(Budget).filter(Budget.id == budget_id).first()
        finally:
            db.close()
    
    def update_budget(self, budget_id: str, budget_data: dict) -> Optional[Budget]:
        db = self._get_session()
        try:
            budget = db.query(Budget).filter(Budget.id == budget_id).first()
            if budget:
                for key, value in budget_data.items():
                    if hasattr(budget, key):
                        setattr(budget, key, value)
                db.commit()
                db.refresh(budget)
            return budget
        finally:
            db.close()
    
    def delete_budget(self, budget_id: str) -> None:
        db = self._get_session()
        try:
            budget = db.query(Budget).filter(Budget.id == budget_id).first()
            if budget:
                db.delete(budget)
                db.commit()
        finally:
            db.close()
    
    def create_goal(self, goal_data: InsertGoalSchema) -> Goal:
        db = self._get_session()
        try:
            goal = Goal(**goal_data.model_dump())
            db.add(goal)
            db.commit()
            db.refresh(goal)
            return goal
        finally:
            db.close()
    
    def get_goals_by_user_id(self, user_id: str) -> List[Goal]:
        db = self._get_session()
        try:
            return db.query(Goal).filter(
                Goal.user_id == user_id
            ).order_by(desc(Goal.created_at)).all()
        finally:
            db.close()
    
    def get_goal_by_id(self, goal_id: str) -> Optional[Goal]:
        db = self._get_session()
        try:
            return db.query(Goal).filter(Goal.id == goal_id).first()
        finally:
            db.close()
    
    def update_goal(self, goal_id: str, goal_data: dict) -> Optional[Goal]:
        db = self._get_session()
        try:
            goal = db.query(Goal).filter(Goal.id == goal_id).first()
            if goal:
                for key, value in goal_data.items():
                    if hasattr(goal, key):
                        setattr(goal, key, value)
                db.commit()
                db.refresh(goal)
            return goal
        finally:
            db.close()
    
    def delete_goal(self, goal_id: str) -> None:
        db = self._get_session()
        try:
            goal = db.query(Goal).filter(Goal.id == goal_id).first()
            if goal:
                db.delete(goal)
                db.commit()
        finally:
            db.close()
    
    def create_bill(self, bill_data: InsertBillSchema) -> Bill:
        db = self._get_session()
        try:
            bill = Bill(**bill_data.model_dump())
            db.add(bill)
            db.commit()
            db.refresh(bill)
            return bill
        finally:
            db.close()
    
    def get_bills_by_user_id(self, user_id: str) -> List[Bill]:
        db = self._get_session()
        try:
            return db.query(Bill).filter(
                Bill.user_id == user_id
            ).order_by(Bill.due_date).all()
        finally:
            db.close()
    
    def get_bill_by_id(self, bill_id: str) -> Optional[Bill]:
        db = self._get_session()
        try:
            return db.query(Bill).filter(Bill.id == bill_id).first()
        finally:
            db.close()
    
    def update_bill(self, bill_id: str, bill_data: dict) -> Optional[Bill]:
        db = self._get_session()
        try:
            bill = db.query(Bill).filter(Bill.id == bill_id).first()
            if bill:
                for key, value in bill_data.items():
                    if hasattr(bill, key):
                        setattr(bill, key, value)
                db.commit()
                db.refresh(bill)
            return bill
        finally:
            db.close()
    
    def delete_bill(self, bill_id: str) -> None:
        db = self._get_session()
        try:
            bill = db.query(Bill).filter(Bill.id == bill_id).first()
            if bill:
                db.delete(bill)
                db.commit()
        finally:
            db.close()

# Initialize storage based on DATABASE_URL availability
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    # Use PostgreSQL database
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    storage = Storage()
    print("Using database storage (PostgreSQL)")
else:
    # Use in-memory storage
    engine = None
    SessionLocal = None
    storage = InMemoryStorage()
    print("Using in-memory storage (demo mode)")
