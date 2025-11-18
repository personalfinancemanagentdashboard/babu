import type { Transaction, Budget, Goal, Bill } from "@shared/schema";

export interface HealthScoreBreakdown {
  totalScore: number;
  rating: string;
  savingsRatio: {
    score: number;
    maxScore: number;
    label: string;
  };
  budgetAdherence: {
    score: number;
    maxScore: number;
    label: string;
  };
  goalProgress: {
    score: number;
    maxScore: number;
    label: string;
  };
  billManagement: {
    score: number;
    maxScore: number;
    label: string;
  };
}

export function calculateHealthScore(
  transactions: Transaction[],
  budgets: Budget[],
  goals: Goal[],
  bills: Bill[]
): HealthScoreBreakdown {
  const savingsRatioScore = calculateSavingsRatio(transactions);
  const budgetAdherenceScore = calculateBudgetAdherence(transactions, budgets);
  const goalProgressScore = calculateGoalProgress(goals);
  const billManagementScore = calculateBillManagement(bills);

  const totalScore = savingsRatioScore.score + budgetAdherenceScore.score + goalProgressScore.score + billManagementScore.score;
  const rating = getRating(totalScore);

  return {
    totalScore,
    rating,
    savingsRatio: savingsRatioScore,
    budgetAdherence: budgetAdherenceScore,
    goalProgress: goalProgressScore,
    billManagement: billManagementScore,
  };
}

function calculateSavingsRatio(transactions: Transaction[]): { score: number; maxScore: number; label: string } {
  const maxScore = 40;
  const totalIncome = transactions
    .filter((t) => t.type === "income")
    .reduce((sum, t) => sum + parseFloat(t.amount), 0);

  const totalExpenses = transactions
    .filter((t) => t.type === "expense")
    .reduce((sum, t) => sum + parseFloat(t.amount), 0);

  if (totalIncome === 0) {
    return { score: 0, maxScore, label: "Savings Ratio" };
  }

  const savingsRate = ((totalIncome - totalExpenses) / totalIncome) * 100;

  let score = 0;
  if (savingsRate >= 50) {
    score = maxScore;
  } else if (savingsRate >= 30) {
    score = Math.round((savingsRate / 50) * maxScore * 0.9);
  } else if (savingsRate >= 20) {
    score = Math.round((savingsRate / 50) * maxScore * 0.7);
  } else if (savingsRate >= 10) {
    score = Math.round((savingsRate / 50) * maxScore * 0.5);
  } else if (savingsRate > 0) {
    score = Math.round((savingsRate / 50) * maxScore * 0.3);
  }

  return { score: Math.min(maxScore, Math.max(0, score)), maxScore, label: "Savings Ratio" };
}

function calculateBudgetAdherence(transactions: Transaction[], budgets: Budget[]): { score: number; maxScore: number; label: string } {
  const maxScore = 25;

  if (budgets.length === 0) {
    return { score: Math.round(maxScore * 0.5), maxScore, label: "Budget Adherence" };
  }

  const currentMonth = new Date().toISOString().slice(0, 7);
  const currentMonthBudgets = budgets.filter((b) => b.month === currentMonth);

  if (currentMonthBudgets.length === 0) {
    return { score: Math.round(maxScore * 0.5), maxScore, label: "Budget Adherence" };
  }

  const categorySpending: Record<string, number> = {};
  transactions
    .filter((t) => t.type === "expense" && t.date.startsWith(currentMonth))
    .forEach((t) => {
      const category = t.category;
      categorySpending[category] = (categorySpending[category] || 0) + parseFloat(t.amount);
    });

  let totalAdherence = 0;
  let budgetCount = 0;

  currentMonthBudgets.forEach((budget) => {
    const spent = categorySpending[budget.category] || 0;
    const budgetAmount = parseFloat(budget.amount);
    
    if (budgetAmount > 0) {
      const adherenceRate = 1 - Math.min(spent / budgetAmount, 1.5);
      totalAdherence += Math.max(0, adherenceRate);
      budgetCount++;
    }
  });

  const averageAdherence = budgetCount > 0 ? totalAdherence / budgetCount : 0.5;
  const score = Math.round(averageAdherence * maxScore);

  return { score: Math.min(maxScore, Math.max(0, score)), maxScore, label: "Budget Adherence" };
}

function calculateGoalProgress(goals: Goal[]): { score: number; maxScore: number; label: string } {
  const maxScore = 25;

  if (goals.length === 0) {
    return { score: Math.round(maxScore * 0.5), maxScore, label: "Goal Progress" };
  }

  let totalProgress = 0;

  goals.forEach((goal) => {
    const target = parseFloat(goal.targetAmount);
    const current = parseFloat(goal.currentAmount);
    if (target > 0) {
      const progress = Math.min(current / target, 1);
      totalProgress += progress;
    }
  });

  const averageProgress = totalProgress / goals.length;
  const score = Math.round(averageProgress * maxScore);

  return { score: Math.min(maxScore, Math.max(0, score)), maxScore, label: "Goal Progress" };
}

function calculateBillManagement(bills: Bill[]): { score: number; maxScore: number; label: string } {
  const maxScore = 10;

  if (bills.length === 0) {
    return { score: maxScore, maxScore, label: "Bill Management" };
  }

  const today = new Date();
  const upcomingBills = bills.filter((bill) => {
    const dueDate = new Date(bill.dueDate);
    return dueDate >= today;
  });

  const overdueBills = bills.filter((bill) => {
    const dueDate = new Date(bill.dueDate);
    return dueDate < today;
  });

  let score = maxScore;
  score -= overdueBills.length * 3;
  score = Math.max(0, score);

  return { score: Math.min(maxScore, score), maxScore, label: "Bill Management" };
}

function getRating(score: number): string {
  if (score >= 90) return "Excellent";
  if (score >= 75) return "Very Good";
  if (score >= 60) return "Good";
  if (score >= 45) return "Fair";
  return "Needs Improvement";
}
