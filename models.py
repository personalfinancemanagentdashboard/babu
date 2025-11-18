from sqlalchemy import Column, String, Numeric, Text, DateTime, Date, ForeignKey, Index, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from pydantic import BaseModel, ConfigDict
from datetime import date, datetime
from typing import Optional
from decimal import Decimal

Base = declarative_base()

class Session(Base):
    __tablename__ = 'sessions'
    
    sid = Column(String, primary_key=True)
    sess = Column(JSON, nullable=False)
    expire = Column(DateTime, nullable=False)
    
    __table_args__ = (
        Index('IDX_session_expire', 'expire'),
    )

class User(Base):
    __tablename__ = 'users'
    
    id = Column(String, primary_key=True, server_default=func.gen_random_uuid())
    email = Column(String, unique=True)
    first_name = Column('first_name', String)
    last_name = Column('last_name', String)
    profile_image_url = Column('profile_image_url', String)
    created_at = Column('created_at', DateTime, server_default=func.now())
    updated_at = Column('updated_at', DateTime, server_default=func.now(), onupdate=func.now())

class Transaction(Base):
    __tablename__ = 'transactions'
    
    id = Column(String, primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column('user_id', String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    title = Column(Text, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    category = Column(Text, nullable=False)
    type = Column(Text, nullable=False)
    date = Column(Date, nullable=False)
    external_id = Column('external_id', String, nullable=True)
    source = Column(String, nullable=True)
    created_at = Column('created_at', DateTime, server_default=func.now(), nullable=False)

class Budget(Base):
    __tablename__ = 'budgets'
    
    id = Column(String, primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column('user_id', String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    category = Column(Text, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    month = Column(Text, nullable=False)
    created_at = Column('created_at', DateTime, server_default=func.now(), nullable=False)

class Goal(Base):
    __tablename__ = 'goals'
    
    id = Column(String, primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column('user_id', String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    title = Column(Text, nullable=False)
    target_amount = Column('target_amount', Numeric(10, 2), nullable=False)
    current_amount = Column('current_amount', Numeric(10, 2), nullable=False, server_default='0')
    deadline = Column(Date)
    created_at = Column('created_at', DateTime, server_default=func.now(), nullable=False)

class Bill(Base):
    __tablename__ = 'bills'
    
    id = Column(String, primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column('user_id', String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    name = Column(Text, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    category = Column(Text, nullable=False)
    due_date = Column('due_date', Date, nullable=False)
    created_at = Column('created_at', DateTime, server_default=func.now(), nullable=False)

CATEGORIES = ["Food", "Rent", "Bills", "Transport", "Entertainment", "Other"]

class UserSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    profile_image_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class UpsertUserSchema(BaseModel):
    id: str
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    profile_image_url: Optional[str] = None

class TransactionSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    user_id: str
    title: str
    amount: Decimal
    category: str
    type: str
    date: date
    external_id: Optional[str] = None
    source: Optional[str] = None
    created_at: datetime

class InsertTransactionSchema(BaseModel):
    user_id: str
    title: str
    amount: Decimal
    category: str
    type: str
    date: date
    external_id: Optional[str] = None
    source: Optional[str] = None

class BudgetSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    user_id: str
    category: str
    amount: Decimal
    month: str
    created_at: datetime

class InsertBudgetSchema(BaseModel):
    user_id: str
    category: str
    amount: Decimal
    month: str

class GoalSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    user_id: str
    title: str
    target_amount: Decimal
    current_amount: Decimal
    deadline: Optional[date] = None
    created_at: datetime

class InsertGoalSchema(BaseModel):
    user_id: str
    title: str
    target_amount: Decimal
    current_amount: Decimal
    deadline: Optional[date] = None

class BillSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    user_id: str
    name: str
    amount: Decimal
    category: str
    due_date: date
    created_at: datetime

class InsertBillSchema(BaseModel):
    user_id: str
    name: str
    amount: Decimal
    category: str
    due_date: date
