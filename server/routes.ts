import type { Express } from "express";
import { createServer, type Server } from "http";
import { storage } from "./storage";
import { setupAuth, isAuthenticated } from "./replitAuth";
import {
  insertTransactionSchema,
  insertBudgetSchema,
  insertGoalSchema,
  insertBillSchema,
} from "@shared/schema";
import { z } from "zod";
import OpenAI from "openai";
import { calculateHealthScore } from "./lib/healthScore";
import { extractTransactionFromImage } from "./lib/ocr";

let openai: OpenAI | null = null;

if (process.env.OPENAI_API_KEY) {
  openai = new OpenAI({
    apiKey: process.env.OPENAI_API_KEY,
  });
} else {
  console.warn("OPENAI_API_KEY not set. AI chat and OCR features will be disabled.");
}

export async function registerRoutes(app: Express): Promise<Server> {
  await setupAuth(app);

  app.get('/api/auth/user', isAuthenticated, async (req: any, res) => {
    try {
      const userId = req.user.claims.sub;
      const user = await storage.getUser(userId);
      res.json(user);
    } catch (error) {
      console.error("Error fetching user:", error);
      res.status(500).json({ message: "Failed to fetch user" });
    }
  });

  // Transaction routes
  app.post("/api/transactions", isAuthenticated, async (req: any, res) => {
    try {
      const userId = req.user.claims.sub;
      const validatedData = insertTransactionSchema.omit({ userId: true }).parse(req.body);
      const transaction = await storage.createTransaction({ ...validatedData, userId });
      res.json(transaction);
    } catch (error) {
      if (error instanceof z.ZodError) {
        res.status(400).json({ message: "Validation error", errors: error.errors });
      } else {
        res.status(500).json({ message: "Failed to create transaction" });
      }
    }
  });

  app.get("/api/transactions", isAuthenticated, async (req: any, res) => {
    try {
      const userId = req.user.claims.sub;
      const transactions = await storage.getTransactionsByUserId(userId);
      res.json(transactions);
    } catch (error) {
      res.status(500).json({ message: "Failed to fetch transactions" });
    }
  });

  app.get("/api/transactions/detail/:id", isAuthenticated, async (req: any, res) => {
    try {
      const userId = req.user.claims.sub;
      const transaction = await storage.getTransactionById(req.params.id);
      if (!transaction || transaction.userId !== userId) {
        res.status(404).json({ message: "Transaction not found" });
        return;
      }
      res.json(transaction);
    } catch (error) {
      res.status(500).json({ message: "Failed to fetch transaction" });
    }
  });

  app.patch("/api/transactions/:id", isAuthenticated, async (req: any, res) => {
    try {
      const userId = req.user.claims.sub;
      const validatedData = insertTransactionSchema.partial().omit({ userId: true }).parse(req.body);
      const existing = await storage.getTransactionById(req.params.id);
      if (!existing || existing.userId !== userId) {
        res.status(404).json({ message: "Transaction not found" });
        return;
      }
      const transaction = await storage.updateTransaction(req.params.id, validatedData);
      res.json(transaction);
    } catch (error) {
      if (error instanceof z.ZodError) {
        res.status(400).json({ message: "Validation error", errors: error.errors });
      } else {
        res.status(500).json({ message: "Failed to update transaction" });
      }
    }
  });

  app.delete("/api/transactions/:id", isAuthenticated, async (req: any, res) => {
    try {
      const userId = req.user.claims.sub;
      const existing = await storage.getTransactionById(req.params.id);
      if (!existing || existing.userId !== userId) {
        res.status(404).json({ message: "Transaction not found" });
        return;
      }
      await storage.deleteTransaction(req.params.id);
      res.json({ message: "Transaction deleted successfully" });
    } catch (error) {
      res.status(500).json({ message: "Failed to delete transaction" });
    }
  });

  app.post("/api/transactions/ocr", isAuthenticated, async (req: any, res) => {
    try {
      if (!openai) {
        res.status(503).json({ 
          message: "OCR is currently unavailable. Please configure OPENAI_API_KEY environment variable." 
        });
        return;
      }

      const { image } = req.body;

      if (!image || typeof image !== "string") {
        res.status(400).json({ message: "Invalid image data. Please provide base64 encoded image." });
        return;
      }

      const imageData = image.replace(/^data:image\/\w+;base64,/, "");

      const extractedData = await extractTransactionFromImage(imageData, openai);
      
      res.json(extractedData);
    } catch (error: any) {
      console.error("OCR error:", error);
      res.status(500).json({ message: error.message || "Failed to extract transaction from image" });
    }
  });

  // Budget routes
  app.post("/api/budgets", isAuthenticated, async (req: any, res) => {
    try {
      const userId = req.user.claims.sub;
      const validatedData = insertBudgetSchema.omit({ userId: true }).parse(req.body);
      const budget = await storage.createBudget({ ...validatedData, userId });
      res.json(budget);
    } catch (error) {
      if (error instanceof z.ZodError) {
        res.status(400).json({ message: "Validation error", errors: error.errors });
      } else {
        res.status(500).json({ message: "Failed to create budget" });
      }
    }
  });

  app.get("/api/budgets", isAuthenticated, async (req: any, res) => {
    try {
      const userId = req.user.claims.sub;
      const { month } = req.query;
      const budgets = await storage.getBudgetsByUserId(userId, month as string | undefined);
      res.json(budgets);
    } catch (error) {
      res.status(500).json({ message: "Failed to fetch budgets" });
    }
  });

  app.patch("/api/budgets/:id", isAuthenticated, async (req: any, res) => {
    try {
      const userId = req.user.claims.sub;
      const validatedData = insertBudgetSchema.partial().omit({ userId: true }).parse(req.body);
      const existing = await storage.getBudgetById(req.params.id);
      if (!existing || existing.userId !== userId) {
        res.status(404).json({ message: "Budget not found" });
        return;
      }
      const budget = await storage.updateBudget(req.params.id, validatedData);
      res.json(budget);
    } catch (error) {
      if (error instanceof z.ZodError) {
        res.status(400).json({ message: "Validation error", errors: error.errors });
      } else {
        res.status(500).json({ message: "Failed to update budget" });
      }
    }
  });

  app.delete("/api/budgets/:id", isAuthenticated, async (req: any, res) => {
    try {
      const userId = req.user.claims.sub;
      const existing = await storage.getBudgetById(req.params.id);
      if (!existing || existing.userId !== userId) {
        res.status(404).json({ message: "Budget not found" });
        return;
      }
      await storage.deleteBudget(req.params.id);
      res.json({ message: "Budget deleted successfully" });
    } catch (error) {
      res.status(500).json({ message: "Failed to delete budget" });
    }
  });

  // Goal routes
  app.post("/api/goals", isAuthenticated, async (req: any, res) => {
    try {
      const userId = req.user.claims.sub;
      const validatedData = insertGoalSchema.omit({ userId: true }).parse(req.body);
      const goal = await storage.createGoal({ ...validatedData, userId });
      res.json(goal);
    } catch (error) {
      if (error instanceof z.ZodError) {
        res.status(400).json({ message: "Validation error", errors: error.errors });
      } else {
        res.status(500).json({ message: "Failed to create goal" });
      }
    }
  });

  app.get("/api/goals", isAuthenticated, async (req: any, res) => {
    try {
      const userId = req.user.claims.sub;
      const goals = await storage.getGoalsByUserId(userId);
      res.json(goals);
    } catch (error) {
      res.status(500).json({ message: "Failed to fetch goals" });
    }
  });

  app.patch("/api/goals/:id", isAuthenticated, async (req: any, res) => {
    try {
      const userId = req.user.claims.sub;
      const validatedData = insertGoalSchema.partial().omit({ userId: true }).parse(req.body);
      const existing = await storage.getGoalById(req.params.id);
      if (!existing || existing.userId !== userId) {
        res.status(404).json({ message: "Goal not found" });
        return;
      }
      const goal = await storage.updateGoal(req.params.id, validatedData);
      res.json(goal);
    } catch (error) {
      if (error instanceof z.ZodError) {
        res.status(400).json({ message: "Validation error", errors: error.errors });
      } else {
        res.status(500).json({ message: "Failed to update goal" });
      }
    }
  });

  app.delete("/api/goals/:id", isAuthenticated, async (req: any, res) => {
    try {
      const userId = req.user.claims.sub;
      const existing = await storage.getGoalById(req.params.id);
      if (!existing || existing.userId !== userId) {
        res.status(404).json({ message: "Goal not found" });
        return;
      }
      await storage.deleteGoal(req.params.id);
      res.json({ message: "Goal deleted successfully" });
    } catch (error) {
      res.status(500).json({ message: "Failed to delete goal" });
    }
  });

  // Bill routes
  app.post("/api/bills", isAuthenticated, async (req: any, res) => {
    try {
      const userId = req.user.claims.sub;
      const validatedData = insertBillSchema.omit({ userId: true }).parse(req.body);
      const bill = await storage.createBill({ ...validatedData, userId });
      res.json(bill);
    } catch (error) {
      if (error instanceof z.ZodError) {
        res.status(400).json({ message: "Validation error", errors: error.errors });
      } else {
        res.status(500).json({ message: "Failed to create bill" });
      }
    }
  });

  app.get("/api/bills", isAuthenticated, async (req: any, res) => {
    try {
      const userId = req.user.claims.sub;
      const bills = await storage.getBillsByUserId(userId);
      res.json(bills);
    } catch (error) {
      res.status(500).json({ message: "Failed to fetch bills" });
    }
  });

  app.patch("/api/bills/:id", isAuthenticated, async (req: any, res) => {
    try {
      const userId = req.user.claims.sub;
      const validatedData = insertBillSchema.partial().omit({ userId: true }).parse(req.body);
      const existing = await storage.getBillById(req.params.id);
      if (!existing || existing.userId !== userId) {
        res.status(404).json({ message: "Bill not found" });
        return;
      }
      const bill = await storage.updateBill(req.params.id, validatedData);
      res.json(bill);
    } catch (error) {
      if (error instanceof z.ZodError) {
        res.status(400).json({ message: "Validation error", errors: error.errors });
      } else {
        res.status(500).json({ message: "Failed to update bill" });
      }
    }
  });

  app.delete("/api/bills/:id", isAuthenticated, async (req: any, res) => {
    try {
      const userId = req.user.claims.sub;
      const existing = await storage.getBillById(req.params.id);
      if (!existing || existing.userId !== userId) {
        res.status(404).json({ message: "Bill not found" });
        return;
      }
      await storage.deleteBill(req.params.id);
      res.json({ message: "Bill deleted successfully" });
    } catch (error) {
      res.status(500).json({ message: "Failed to delete bill" });
    }
  });

  app.get("/api/health-score", isAuthenticated, async (req: any, res) => {
    try {
      const userId = req.user.claims.sub;

      const [transactions, budgets, goals, bills] = await Promise.all([
        storage.getTransactionsByUserId(userId),
        storage.getBudgetsByUserId(userId),
        storage.getGoalsByUserId(userId),
        storage.getBillsByUserId(userId),
      ]);

      const healthScore = calculateHealthScore(transactions, budgets, goals, bills);
      
      res.json(healthScore);
    } catch (error) {
      console.error("Health score calculation error:", error);
      res.status(500).json({ message: "Failed to calculate health score" });
    }
  });

  // AI Chat route
  app.post("/api/ai/chat", isAuthenticated, async (req: any, res) => {
    try {
      if (!openai) {
        res.status(503).json({ 
          message: "AI chat is currently unavailable. Please configure OPENAI_API_KEY environment variable." 
        });
        return;
      }

      const userId = req.user.claims.sub;
      const { messages } = req.body;

      if (!messages || !Array.isArray(messages)) {
        res.status(400).json({ message: "Invalid messages format" });
        return;
      }

      // Fetch user's financial data for context
      const [transactions, budgets, goals, bills] = await Promise.all([
        storage.getTransactionsByUserId(userId),
        storage.getBudgetsByUserId(userId),
        storage.getGoalsByUserId(userId),
        storage.getBillsByUserId(userId),
      ]);

      // Calculate spending by category
      const spendingByCategory = transactions
        .filter((t) => t.type === "expense")
        .reduce((acc, t) => {
          const category = t.category;
          if (!acc[category]) {
            acc[category] = 0;
          }
          acc[category] += parseFloat(t.amount);
          return acc;
        }, {} as Record<string, number>);

      // Calculate monthly trends
      const now = new Date();
      const currentMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
      const lastMonth = new Date(now.getFullYear(), now.getMonth() - 1, 1);
      const lastMonthStr = `${lastMonth.getFullYear()}-${String(lastMonth.getMonth() + 1).padStart(2, '0')}`;

      const currentMonthExpenses = transactions
        .filter((t) => t.type === "expense" && t.date.startsWith(currentMonth))
        .reduce((sum, t) => sum + parseFloat(t.amount), 0);

      const lastMonthExpenses = transactions
        .filter((t) => t.type === "expense" && t.date.startsWith(lastMonthStr))
        .reduce((sum, t) => sum + parseFloat(t.amount), 0);

      // Prepare detailed financial context for AI
      const totalIncome = transactions
        .filter((t) => t.type === "income")
        .reduce((sum, t) => sum + parseFloat(t.amount), 0);
      
      const totalExpenses = transactions
        .filter((t) => t.type === "expense")
        .reduce((sum, t) => sum + parseFloat(t.amount), 0);

      // Format category breakdown for AI
      const categoryBreakdown = Object.entries(spendingByCategory)
        .map(([category, amount]) => `  - ${category}: ₹${amount.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`)
        .join('\n') || '  No expenses recorded';

      // Format recent transactions
      const recentTransactions = transactions
        .slice(0, 10)
        .map((t) => `  - ${t.date}: ${t.title} (${t.category}) - ₹${parseFloat(t.amount).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} [${t.type}]`)
        .join('\n') || '  No transactions yet';

      // Format upcoming bills
      const upcomingBills = bills
        .filter(b => new Date(b.dueDate) >= new Date())
        .slice(0, 5)
        .map((b) => `  - ${b.name}: ₹${parseFloat(b.amount).toLocaleString('en-IN')} due on ${b.dueDate}`)
        .join('\n') || '  No upcoming bills';

      // Format goals
      const goalsInfo = goals
        .slice(0, 5)
        .map((g) => {
          const progress = (parseFloat(g.currentAmount) / parseFloat(g.targetAmount)) * 100;
          return `  - ${g.title}: ₹${parseFloat(g.currentAmount).toLocaleString('en-IN')} / ₹${parseFloat(g.targetAmount).toLocaleString('en-IN')} (${progress.toFixed(0)}%)`;
        })
        .join('\n') || '  No active goals';

      const systemMessage = {
        role: "system",
        content: `You are SmartFinance.AI, a helpful personal finance assistant for Indian users. Analyze the user's actual financial data and provide clear, actionable advice using Indian Rupees (₹).

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
  Total Income: ₹${totalIncome.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
  Total Expenses: ₹${totalExpenses.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
  Net Balance: ₹${(totalIncome - totalExpenses).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
  
Monthly Comparison:
  Current Month Spending: ₹${currentMonthExpenses.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
  Last Month Spending: ₹${lastMonthExpenses.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
  Change: ${currentMonthExpenses > lastMonthExpenses ? '+' : ''}₹${Math.abs(currentMonthExpenses - lastMonthExpenses).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}

Spending by Category:
${categoryBreakdown}

Active Budgets: ${budgets.length}
Savings Goals: ${goals.length}

Goals Progress:
${goalsInfo}

Upcoming Bills: ${bills.filter(b => new Date(b.dueDate) >= new Date()).length}
${upcomingBills}

Recent Transactions (last 10):
${recentTransactions}

HOW TO RESPOND:
1. Answer questions using the actual data above
2. Be specific - use real numbers from their transactions
3. Always use ₹ symbol for amounts
4. Structure responses with clear sections (use line breaks)
5. Keep it conversational and easy to understand
6. Provide actionable tips based on their spending patterns
7. NO markdown symbols - plain text only
8. Reference their actual budgets, goals, and bills when relevant

Example good response format:

Your Spending This Month 📊

You spent ₹45,230 this month across these categories:
- Food: ₹12,500
- Transportation: ₹8,000
- Entertainment: ₹5,000

Compared to last month, you're spending ₹3,200 more.

Here's my recommendation 💡
- Your food spending is high. Try meal planning to save ₹2,000-3,000 monthly.
- Consider budgeting ₹10,000 for food next month.

Remember: Be helpful, specific, and use their actual data!`,
      };

      const completion = await openai.chat.completions.create({
        model: "gpt-4o-mini",
        messages: [systemMessage, ...messages],
        temperature: 0.7,
        max_tokens: 500,
      });

      res.json({
        message: completion.choices[0].message.content,
      });
    } catch (error) {
      console.error("OpenAI API error:", error);
      res.status(500).json({ message: "Failed to get AI response" });
    }
  });

  const httpServer = createServer(app);

  return httpServer;
}
