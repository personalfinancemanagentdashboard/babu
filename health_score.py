from typing import List, Dict
from models import Transaction, Budget, Goal, Bill
from datetime import date, datetime

class HealthScoreBreakdown:
    def __init__(self, total_score: int, rating: str, savings_ratio: Dict, 
                 budget_adherence: Dict, goal_progress: Dict, bill_management: Dict):
        self.total_score = total_score
        self.rating = rating
        self.savings_ratio = savings_ratio
        self.budget_adherence = budget_adherence
        self.goal_progress = goal_progress
        self.bill_management = bill_management
    
    def to_dict(self):
        return {
            "totalScore": self.total_score,
            "rating": self.rating,
            "savingsRatio": self.savings_ratio,
            "budgetAdherence": self.budget_adherence,
            "goalProgress": self.goal_progress,
            "billManagement": self.bill_management
        }

def calculate_health_score(transactions: List[Transaction], budgets: List[Budget],
                          goals: List[Goal], bills: List[Bill]) -> HealthScoreBreakdown:
    savings_ratio_score = calculate_savings_ratio(transactions)
    budget_adherence_score = calculate_budget_adherence(transactions, budgets)
    goal_progress_score = calculate_goal_progress(goals)
    bill_management_score = calculate_bill_management(bills)
    
    total_score = (savings_ratio_score["score"] + budget_adherence_score["score"] + 
                  goal_progress_score["score"] + bill_management_score["score"])
    rating = get_rating(total_score)
    
    return HealthScoreBreakdown(
        total_score=total_score,
        rating=rating,
        savings_ratio=savings_ratio_score,
        budget_adherence=budget_adherence_score,
        goal_progress=goal_progress_score,
        bill_management=bill_management_score
    )

def calculate_savings_ratio(transactions: List[Transaction]) -> Dict:
    max_score = 40
    
    total_income = sum(float(t.amount) for t in transactions if t.type == "income")
    total_expenses = sum(float(t.amount) for t in transactions if t.type == "expense")
    
    if total_income == 0:
        return {"score": 0, "maxScore": max_score, "label": "Savings Ratio"}
    
    savings_rate = ((total_income - total_expenses) / total_income) * 100
    
    score = 0
    if savings_rate >= 50:
        score = max_score
    elif savings_rate >= 30:
        score = round((savings_rate / 50) * max_score * 0.9)
    elif savings_rate >= 20:
        score = round((savings_rate / 50) * max_score * 0.7)
    elif savings_rate >= 10:
        score = round((savings_rate / 50) * max_score * 0.5)
    elif savings_rate > 0:
        score = round((savings_rate / 50) * max_score * 0.3)
    
    return {"score": min(max_score, max(0, score)), "maxScore": max_score, "label": "Savings Ratio"}

def calculate_budget_adherence(transactions: List[Transaction], budgets: List[Budget]) -> Dict:
    max_score = 25
    
    if len(budgets) == 0:
        return {"score": round(max_score * 0.5), "maxScore": max_score, "label": "Budget Adherence"}
    
    current_month = datetime.now().strftime("%Y-%m")
    current_month_budgets = [b for b in budgets if b.month == current_month]
    
    if len(current_month_budgets) == 0:
        return {"score": round(max_score * 0.5), "maxScore": max_score, "label": "Budget Adherence"}
    
    category_spending = {}
    for t in transactions:
        if t.type == "expense" and str(t.date).startswith(current_month):
            category = t.category
            category_spending[category] = category_spending.get(category, 0) + float(t.amount)
    
    total_adherence = 0
    budget_count = 0
    
    for budget in current_month_budgets:
        spent = category_spending.get(budget.category, 0)
        budget_amount = float(budget.amount)
        
        if budget_amount > 0:
            adherence_rate = 1 - min(spent / budget_amount, 1.5)
            total_adherence += max(0, adherence_rate)
            budget_count += 1
    
    average_adherence = total_adherence / budget_count if budget_count > 0 else 0.5
    score = round(average_adherence * max_score)
    
    return {"score": min(max_score, max(0, score)), "maxScore": max_score, "label": "Budget Adherence"}

def calculate_goal_progress(goals: List[Goal]) -> Dict:
    max_score = 25
    
    if len(goals) == 0:
        return {"score": round(max_score * 0.5), "maxScore": max_score, "label": "Goal Progress"}
    
    total_progress = 0
    
    for goal in goals:
        target = float(goal.target_amount)
        current = float(goal.current_amount)
        if target > 0:
            progress = min(current / target, 1)
            total_progress += progress
    
    average_progress = total_progress / len(goals)
    score = round(average_progress * max_score)
    
    return {"score": min(max_score, max(0, score)), "maxScore": max_score, "label": "Goal Progress"}

def calculate_bill_management(bills: List[Bill]) -> Dict:
    max_score = 10
    
    if len(bills) == 0:
        return {"score": max_score, "maxScore": max_score, "label": "Bill Management"}
    
    today = date.today()
    
    overdue_bills = [b for b in bills if b.due_date < today]
    
    score = max_score
    score -= len(overdue_bills) * 3
    score = max(0, score)
    
    return {"score": min(max_score, score), "maxScore": max_score, "label": "Bill Management"}

def get_rating(score: int) -> str:
    if score >= 90:
        return "Excellent"
    elif score >= 75:
        return "Very Good"
    elif score >= 60:
        return "Good"
    elif score >= 45:
        return "Fair"
    else:
        return "Needs Improvement"
