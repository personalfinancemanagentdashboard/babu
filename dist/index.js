var __defProp = Object.defineProperty;
var __export = (target, all) => {
  for (var name in all)
    __defProp(target, name, { get: all[name], enumerable: true });
};

// server/index.ts
import express2 from "express";

// server/routes.ts
import { createServer } from "http";

// server/storage.ts
import { eq, and, desc } from "drizzle-orm";

// server/db.ts
import { Pool, neonConfig } from "@neondatabase/serverless";
import { drizzle } from "drizzle-orm/neon-serverless";
import ws from "ws";

// shared/schema.ts
var schema_exports = {};
__export(schema_exports, {
  CATEGORIES: () => CATEGORIES,
  bills: () => bills,
  budgets: () => budgets,
  goals: () => goals,
  insertBillSchema: () => insertBillSchema,
  insertBudgetSchema: () => insertBudgetSchema,
  insertGoalSchema: () => insertGoalSchema,
  insertTransactionSchema: () => insertTransactionSchema,
  sessions: () => sessions,
  transactions: () => transactions,
  users: () => users
});
import { sql } from "drizzle-orm";
import { pgTable, text, varchar, decimal, timestamp, date, index, jsonb } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
var sessions = pgTable(
  "sessions",
  {
    sid: varchar("sid").primaryKey(),
    sess: jsonb("sess").notNull(),
    expire: timestamp("expire").notNull()
  },
  (table) => [index("IDX_session_expire").on(table.expire)]
);
var users = pgTable("users", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  email: varchar("email").unique(),
  firstName: varchar("first_name"),
  lastName: varchar("last_name"),
  profileImageUrl: varchar("profile_image_url"),
  createdAt: timestamp("created_at").defaultNow(),
  updatedAt: timestamp("updated_at").defaultNow()
});
var transactions = pgTable("transactions", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  userId: varchar("user_id").notNull().references(() => users.id, { onDelete: "cascade" }),
  title: text("title").notNull(),
  amount: decimal("amount", { precision: 10, scale: 2 }).notNull(),
  category: text("category").notNull(),
  type: text("type").notNull(),
  // "income" or "expense"
  date: date("date").notNull(),
  createdAt: timestamp("created_at").defaultNow().notNull()
});
var insertTransactionSchema = createInsertSchema(transactions).omit({
  id: true,
  createdAt: true
});
var budgets = pgTable("budgets", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  userId: varchar("user_id").notNull().references(() => users.id, { onDelete: "cascade" }),
  category: text("category").notNull(),
  amount: decimal("amount", { precision: 10, scale: 2 }).notNull(),
  month: text("month").notNull(),
  // Format: "YYYY-MM"
  createdAt: timestamp("created_at").defaultNow().notNull()
});
var insertBudgetSchema = createInsertSchema(budgets).omit({
  id: true,
  createdAt: true
});
var goals = pgTable("goals", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  userId: varchar("user_id").notNull().references(() => users.id, { onDelete: "cascade" }),
  title: text("title").notNull(),
  targetAmount: decimal("target_amount", { precision: 10, scale: 2 }).notNull(),
  currentAmount: decimal("current_amount", { precision: 10, scale: 2 }).notNull().default("0"),
  deadline: date("deadline"),
  createdAt: timestamp("created_at").defaultNow().notNull()
});
var insertGoalSchema = createInsertSchema(goals).omit({
  id: true,
  createdAt: true
});
var bills = pgTable("bills", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  userId: varchar("user_id").notNull().references(() => users.id, { onDelete: "cascade" }),
  name: text("name").notNull(),
  amount: decimal("amount", { precision: 10, scale: 2 }).notNull(),
  category: text("category").notNull(),
  dueDate: date("due_date").notNull(),
  createdAt: timestamp("created_at").defaultNow().notNull()
});
var insertBillSchema = createInsertSchema(bills).omit({
  id: true,
  createdAt: true
});
var CATEGORIES = ["Food", "Rent", "Bills", "Transport", "Entertainment", "Other"];

// server/db.ts
neonConfig.webSocketConstructor = ws;
if (!process.env.DATABASE_URL) {
  throw new Error(
    "DATABASE_URL must be set. Did you forget to provision a database?"
  );
}
var pool = new Pool({ connectionString: process.env.DATABASE_URL });
var db = drizzle({ client: pool, schema: schema_exports });

// server/storage.ts
var DbStorage = class {
  // User methods (required for Replit Auth)
  async getUser(id) {
    const [user] = await db.select().from(users).where(eq(users.id, id));
    return user;
  }
  async upsertUser(userData) {
    const [user] = await db.insert(users).values(userData).onConflictDoUpdate({
      target: users.id,
      set: {
        ...userData,
        updatedAt: /* @__PURE__ */ new Date()
      }
    }).returning();
    return user;
  }
  // Transaction methods
  async createTransaction(transaction) {
    const [newTransaction] = await db.insert(transactions).values(transaction).returning();
    return newTransaction;
  }
  async getTransactionsByUserId(userId) {
    return await db.select().from(transactions).where(eq(transactions.userId, userId)).orderBy(desc(transactions.date));
  }
  async getTransactionById(id) {
    const [transaction] = await db.select().from(transactions).where(eq(transactions.id, id));
    return transaction;
  }
  async updateTransaction(id, transaction) {
    const [updated] = await db.update(transactions).set(transaction).where(eq(transactions.id, id)).returning();
    return updated;
  }
  async deleteTransaction(id) {
    await db.delete(transactions).where(eq(transactions.id, id));
  }
  // Budget methods
  async createBudget(budget) {
    const [newBudget] = await db.insert(budgets).values(budget).returning();
    return newBudget;
  }
  async getBudgetsByUserId(userId, month) {
    if (month) {
      return await db.select().from(budgets).where(and(eq(budgets.userId, userId), eq(budgets.month, month)));
    }
    return await db.select().from(budgets).where(eq(budgets.userId, userId));
  }
  async getBudgetById(id) {
    const [budget] = await db.select().from(budgets).where(eq(budgets.id, id));
    return budget;
  }
  async updateBudget(id, budget) {
    const [updated] = await db.update(budgets).set(budget).where(eq(budgets.id, id)).returning();
    return updated;
  }
  async deleteBudget(id) {
    await db.delete(budgets).where(eq(budgets.id, id));
  }
  // Goal methods
  async createGoal(goal) {
    const [newGoal] = await db.insert(goals).values(goal).returning();
    return newGoal;
  }
  async getGoalsByUserId(userId) {
    return await db.select().from(goals).where(eq(goals.userId, userId)).orderBy(desc(goals.createdAt));
  }
  async getGoalById(id) {
    const [goal] = await db.select().from(goals).where(eq(goals.id, id));
    return goal;
  }
  async updateGoal(id, goal) {
    const [updated] = await db.update(goals).set(goal).where(eq(goals.id, id)).returning();
    return updated;
  }
  async deleteGoal(id) {
    await db.delete(goals).where(eq(goals.id, id));
  }
  // Bill methods
  async createBill(bill) {
    const [newBill] = await db.insert(bills).values(bill).returning();
    return newBill;
  }
  async getBillsByUserId(userId) {
    return await db.select().from(bills).where(eq(bills.userId, userId)).orderBy(bills.dueDate);
  }
  async getBillById(id) {
    const [bill] = await db.select().from(bills).where(eq(bills.id, id));
    return bill;
  }
  async updateBill(id, bill) {
    const [updated] = await db.update(bills).set(bill).where(eq(bills.id, id)).returning();
    return updated;
  }
  async deleteBill(id) {
    await db.delete(bills).where(eq(bills.id, id));
  }
};
var storage = new DbStorage();

// server/replitAuth.ts
import * as client from "openid-client";
import { Strategy } from "openid-client/passport";
import passport from "passport";
import session from "express-session";
import memoize from "memoizee";
import connectPg from "connect-pg-simple";
var getOidcConfig = memoize(
  async () => {
    return await client.discovery(
      new URL(process.env.ISSUER_URL ?? "https://replit.com/oidc"),
      process.env.REPL_ID
    );
  },
  { maxAge: 3600 * 1e3 }
);
function getSession() {
  const sessionTtl = 7 * 24 * 60 * 60 * 1e3;
  const pgStore = connectPg(session);
  const sessionStore = new pgStore({
    conString: process.env.DATABASE_URL,
    createTableIfMissing: false,
    ttl: sessionTtl,
    tableName: "sessions"
  });
  return session({
    secret: process.env.SESSION_SECRET,
    store: sessionStore,
    resave: false,
    saveUninitialized: false,
    cookie: {
      httpOnly: true,
      secure: true,
      maxAge: sessionTtl
    }
  });
}
function updateUserSession(user, tokens) {
  user.claims = tokens.claims();
  user.access_token = tokens.access_token;
  user.refresh_token = tokens.refresh_token;
  user.expires_at = user.claims?.exp;
}
async function upsertUser(claims) {
  await storage.upsertUser({
    id: claims["sub"],
    email: claims["email"],
    firstName: claims["first_name"],
    lastName: claims["last_name"],
    profileImageUrl: claims["profile_image_url"]
  });
}
async function setupAuth(app2) {
  app2.set("trust proxy", 1);
  app2.use(getSession());
  app2.use(passport.initialize());
  app2.use(passport.session());
  const config = await getOidcConfig();
  const verify = async (tokens, verified) => {
    const user = {};
    updateUserSession(user, tokens);
    await upsertUser(tokens.claims());
    verified(null, user);
  };
  const registeredStrategies = /* @__PURE__ */ new Set();
  const ensureStrategy = (domain) => {
    const strategyName = `replitauth:${domain}`;
    if (!registeredStrategies.has(strategyName)) {
      const strategy = new Strategy(
        {
          name: strategyName,
          config,
          scope: "openid email profile offline_access",
          callbackURL: `https://${domain}/api/callback`
        },
        verify
      );
      passport.use(strategy);
      registeredStrategies.add(strategyName);
    }
  };
  passport.serializeUser((user, cb) => cb(null, user));
  passport.deserializeUser((user, cb) => cb(null, user));
  app2.get("/api/login", (req, res, next) => {
    ensureStrategy(req.hostname);
    passport.authenticate(`replitauth:${req.hostname}`, {
      prompt: "login consent",
      scope: ["openid", "email", "profile", "offline_access"]
    })(req, res, next);
  });
  app2.get("/api/callback", (req, res, next) => {
    ensureStrategy(req.hostname);
    passport.authenticate(`replitauth:${req.hostname}`, {
      successReturnToOrRedirect: "/",
      failureRedirect: "/api/login"
    })(req, res, next);
  });
  app2.get("/api/logout", (req, res) => {
    req.logout(() => {
      res.redirect(
        client.buildEndSessionUrl(config, {
          client_id: process.env.REPL_ID,
          post_logout_redirect_uri: `${req.protocol}://${req.hostname}`
        }).href
      );
    });
  });
}
var isAuthenticated = async (req, res, next) => {
  const user = req.user;
  if (!req.isAuthenticated() || !user.expires_at) {
    return res.status(401).json({ message: "Unauthorized" });
  }
  const now = Math.floor(Date.now() / 1e3);
  if (now <= user.expires_at) {
    return next();
  }
  const refreshToken = user.refresh_token;
  if (!refreshToken) {
    res.status(401).json({ message: "Unauthorized" });
    return;
  }
  try {
    const config = await getOidcConfig();
    const tokenResponse = await client.refreshTokenGrant(config, refreshToken);
    updateUserSession(user, tokenResponse);
    return next();
  } catch (error) {
    res.status(401).json({ message: "Unauthorized" });
    return;
  }
};

// server/routes.ts
import { z } from "zod";
import OpenAI from "openai";

// server/lib/healthScore.ts
function calculateHealthScore(transactions2, budgets2, goals2, bills2) {
  const savingsRatioScore = calculateSavingsRatio(transactions2);
  const budgetAdherenceScore = calculateBudgetAdherence(transactions2, budgets2);
  const goalProgressScore = calculateGoalProgress(goals2);
  const billManagementScore = calculateBillManagement(bills2);
  const totalScore = savingsRatioScore.score + budgetAdherenceScore.score + goalProgressScore.score + billManagementScore.score;
  const rating = getRating(totalScore);
  return {
    totalScore,
    rating,
    savingsRatio: savingsRatioScore,
    budgetAdherence: budgetAdherenceScore,
    goalProgress: goalProgressScore,
    billManagement: billManagementScore
  };
}
function calculateSavingsRatio(transactions2) {
  const maxScore = 40;
  const totalIncome = transactions2.filter((t) => t.type === "income").reduce((sum, t) => sum + parseFloat(t.amount), 0);
  const totalExpenses = transactions2.filter((t) => t.type === "expense").reduce((sum, t) => sum + parseFloat(t.amount), 0);
  if (totalIncome === 0) {
    return { score: 0, maxScore, label: "Savings Ratio" };
  }
  const savingsRate = (totalIncome - totalExpenses) / totalIncome * 100;
  let score = 0;
  if (savingsRate >= 50) {
    score = maxScore;
  } else if (savingsRate >= 30) {
    score = Math.round(savingsRate / 50 * maxScore * 0.9);
  } else if (savingsRate >= 20) {
    score = Math.round(savingsRate / 50 * maxScore * 0.7);
  } else if (savingsRate >= 10) {
    score = Math.round(savingsRate / 50 * maxScore * 0.5);
  } else if (savingsRate > 0) {
    score = Math.round(savingsRate / 50 * maxScore * 0.3);
  }
  return { score: Math.min(maxScore, Math.max(0, score)), maxScore, label: "Savings Ratio" };
}
function calculateBudgetAdherence(transactions2, budgets2) {
  const maxScore = 25;
  if (budgets2.length === 0) {
    return { score: Math.round(maxScore * 0.5), maxScore, label: "Budget Adherence" };
  }
  const currentMonth = (/* @__PURE__ */ new Date()).toISOString().slice(0, 7);
  const currentMonthBudgets = budgets2.filter((b) => b.month === currentMonth);
  if (currentMonthBudgets.length === 0) {
    return { score: Math.round(maxScore * 0.5), maxScore, label: "Budget Adherence" };
  }
  const categorySpending = {};
  transactions2.filter((t) => t.type === "expense" && t.date.startsWith(currentMonth)).forEach((t) => {
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
function calculateGoalProgress(goals2) {
  const maxScore = 25;
  if (goals2.length === 0) {
    return { score: Math.round(maxScore * 0.5), maxScore, label: "Goal Progress" };
  }
  let totalProgress = 0;
  goals2.forEach((goal) => {
    const target = parseFloat(goal.targetAmount);
    const current = parseFloat(goal.currentAmount);
    if (target > 0) {
      const progress = Math.min(current / target, 1);
      totalProgress += progress;
    }
  });
  const averageProgress = totalProgress / goals2.length;
  const score = Math.round(averageProgress * maxScore);
  return { score: Math.min(maxScore, Math.max(0, score)), maxScore, label: "Goal Progress" };
}
function calculateBillManagement(bills2) {
  const maxScore = 10;
  if (bills2.length === 0) {
    return { score: maxScore, maxScore, label: "Bill Management" };
  }
  const today = /* @__PURE__ */ new Date();
  const upcomingBills = bills2.filter((bill) => {
    const dueDate = new Date(bill.dueDate);
    return dueDate >= today;
  });
  const overdueBills = bills2.filter((bill) => {
    const dueDate = new Date(bill.dueDate);
    return dueDate < today;
  });
  let score = maxScore;
  score -= overdueBills.length * 3;
  score = Math.max(0, score);
  return { score: Math.min(maxScore, score), maxScore, label: "Bill Management" };
}
function getRating(score) {
  if (score >= 90) return "Excellent";
  if (score >= 75) return "Very Good";
  if (score >= 60) return "Good";
  if (score >= 45) return "Fair";
  return "Needs Improvement";
}

// server/lib/ocr.ts
async function extractTransactionFromImage(imageBase64, openaiClient) {
  const systemPrompt = `You are a financial receipt/bill analyzer. Extract transaction information from images and return it in JSON format.

Extract the following:
- title: A brief description of the transaction (e.g., "Grocery Shopping at Walmart", "Electricity Bill")
- amount: The total amount as a number (no currency symbols, just the number)
- category: One of these categories: ${CATEGORIES.join(", ")}
- date: The transaction date in YYYY-MM-DD format (if not visible, use today's date)
- type: Either "income" or "expense" (receipts are usually expenses)

Rules:
1. Be accurate with the amount - look for "Total", "Amount Due", or similar
2. Choose the most appropriate category
3. For bills, use "Bills" category
4. For shopping receipts, categorize based on items (Food for groceries, etc.)
5. If you can't determine something, make a reasonable guess

Return ONLY valid JSON in this exact format:
{
  "title": "Description here",
  "amount": "1234.56",
  "category": "Food",
  "date": "2024-01-15",
  "type": "expense"
}`;
  try {
    const response = await openaiClient.chat.completions.create({
      model: "gpt-4o",
      messages: [
        {
          role: "system",
          content: systemPrompt
        },
        {
          role: "user",
          content: [
            {
              type: "text",
              text: "Extract the transaction details from this receipt/bill image:"
            },
            {
              type: "image_url",
              image_url: {
                url: `data:image/jpeg;base64,${imageBase64}`
              }
            }
          ]
        }
      ],
      max_tokens: 500,
      temperature: 0.2
    });
    const content = response.choices[0]?.message?.content;
    if (!content) {
      throw new Error("No response from OpenAI");
    }
    const jsonMatch = content.match(/\{[\s\S]*\}/);
    if (!jsonMatch) {
      throw new Error("Could not parse JSON from response");
    }
    const result = JSON.parse(jsonMatch[0]);
    if (!result.title || !result.amount || !result.category || !result.date || !result.type) {
      throw new Error("Incomplete transaction data extracted");
    }
    if (!CATEGORIES.includes(result.category)) {
      result.category = "Other";
    }
    if (!["income", "expense"].includes(result.type)) {
      result.type = "expense";
    }
    return result;
  } catch (error) {
    console.error("OCR extraction error:", error);
    throw new Error(`Failed to extract transaction from image: ${error.message}`);
  }
}

// server/routes.ts
var openai = null;
if (process.env.OPENAI_API_KEY) {
  openai = new OpenAI({
    apiKey: process.env.OPENAI_API_KEY
  });
} else {
  console.warn("OPENAI_API_KEY not set. AI chat and OCR features will be disabled.");
}
async function registerRoutes(app2) {
  await setupAuth(app2);
  app2.get("/api/auth/user", isAuthenticated, async (req, res) => {
    try {
      const userId = req.user.claims.sub;
      const user = await storage.getUser(userId);
      res.json(user);
    } catch (error) {
      console.error("Error fetching user:", error);
      res.status(500).json({ message: "Failed to fetch user" });
    }
  });
  app2.post("/api/transactions", isAuthenticated, async (req, res) => {
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
  app2.get("/api/transactions", isAuthenticated, async (req, res) => {
    try {
      const userId = req.user.claims.sub;
      const transactions2 = await storage.getTransactionsByUserId(userId);
      res.json(transactions2);
    } catch (error) {
      res.status(500).json({ message: "Failed to fetch transactions" });
    }
  });
  app2.get("/api/transactions/detail/:id", isAuthenticated, async (req, res) => {
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
  app2.patch("/api/transactions/:id", isAuthenticated, async (req, res) => {
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
  app2.delete("/api/transactions/:id", isAuthenticated, async (req, res) => {
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
  app2.post("/api/transactions/ocr", isAuthenticated, async (req, res) => {
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
    } catch (error) {
      console.error("OCR error:", error);
      res.status(500).json({ message: error.message || "Failed to extract transaction from image" });
    }
  });
  app2.post("/api/budgets", isAuthenticated, async (req, res) => {
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
  app2.get("/api/budgets", isAuthenticated, async (req, res) => {
    try {
      const userId = req.user.claims.sub;
      const { month } = req.query;
      const budgets2 = await storage.getBudgetsByUserId(userId, month);
      res.json(budgets2);
    } catch (error) {
      res.status(500).json({ message: "Failed to fetch budgets" });
    }
  });
  app2.patch("/api/budgets/:id", isAuthenticated, async (req, res) => {
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
  app2.delete("/api/budgets/:id", isAuthenticated, async (req, res) => {
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
  app2.post("/api/goals", isAuthenticated, async (req, res) => {
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
  app2.get("/api/goals", isAuthenticated, async (req, res) => {
    try {
      const userId = req.user.claims.sub;
      const goals2 = await storage.getGoalsByUserId(userId);
      res.json(goals2);
    } catch (error) {
      res.status(500).json({ message: "Failed to fetch goals" });
    }
  });
  app2.patch("/api/goals/:id", isAuthenticated, async (req, res) => {
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
  app2.delete("/api/goals/:id", isAuthenticated, async (req, res) => {
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
  app2.post("/api/bills", isAuthenticated, async (req, res) => {
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
  app2.get("/api/bills", isAuthenticated, async (req, res) => {
    try {
      const userId = req.user.claims.sub;
      const bills2 = await storage.getBillsByUserId(userId);
      res.json(bills2);
    } catch (error) {
      res.status(500).json({ message: "Failed to fetch bills" });
    }
  });
  app2.patch("/api/bills/:id", isAuthenticated, async (req, res) => {
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
  app2.delete("/api/bills/:id", isAuthenticated, async (req, res) => {
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
  app2.get("/api/health-score", isAuthenticated, async (req, res) => {
    try {
      const userId = req.user.claims.sub;
      const [transactions2, budgets2, goals2, bills2] = await Promise.all([
        storage.getTransactionsByUserId(userId),
        storage.getBudgetsByUserId(userId),
        storage.getGoalsByUserId(userId),
        storage.getBillsByUserId(userId)
      ]);
      const healthScore = calculateHealthScore(transactions2, budgets2, goals2, bills2);
      res.json(healthScore);
    } catch (error) {
      console.error("Health score calculation error:", error);
      res.status(500).json({ message: "Failed to calculate health score" });
    }
  });
  app2.post("/api/ai/chat", isAuthenticated, async (req, res) => {
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
      const [transactions2, budgets2, goals2, bills2] = await Promise.all([
        storage.getTransactionsByUserId(userId),
        storage.getBudgetsByUserId(userId),
        storage.getGoalsByUserId(userId),
        storage.getBillsByUserId(userId)
      ]);
      const spendingByCategory = transactions2.filter((t) => t.type === "expense").reduce((acc, t) => {
        const category = t.category;
        if (!acc[category]) {
          acc[category] = 0;
        }
        acc[category] += parseFloat(t.amount);
        return acc;
      }, {});
      const now = /* @__PURE__ */ new Date();
      const currentMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
      const lastMonth = new Date(now.getFullYear(), now.getMonth() - 1, 1);
      const lastMonthStr = `${lastMonth.getFullYear()}-${String(lastMonth.getMonth() + 1).padStart(2, "0")}`;
      const currentMonthExpenses = transactions2.filter((t) => t.type === "expense" && t.date.startsWith(currentMonth)).reduce((sum, t) => sum + parseFloat(t.amount), 0);
      const lastMonthExpenses = transactions2.filter((t) => t.type === "expense" && t.date.startsWith(lastMonthStr)).reduce((sum, t) => sum + parseFloat(t.amount), 0);
      const totalIncome = transactions2.filter((t) => t.type === "income").reduce((sum, t) => sum + parseFloat(t.amount), 0);
      const totalExpenses = transactions2.filter((t) => t.type === "expense").reduce((sum, t) => sum + parseFloat(t.amount), 0);
      const categoryBreakdown = Object.entries(spendingByCategory).map(([category, amount]) => `  - ${category}: \u20B9${amount.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`).join("\n") || "  No expenses recorded";
      const recentTransactions = transactions2.slice(0, 10).map((t) => `  - ${t.date}: ${t.title} (${t.category}) - \u20B9${parseFloat(t.amount).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} [${t.type}]`).join("\n") || "  No transactions yet";
      const upcomingBills = bills2.filter((b) => new Date(b.dueDate) >= /* @__PURE__ */ new Date()).slice(0, 5).map((b) => `  - ${b.name}: \u20B9${parseFloat(b.amount).toLocaleString("en-IN")} due on ${b.dueDate}`).join("\n") || "  No upcoming bills";
      const goalsInfo = goals2.slice(0, 5).map((g) => {
        const progress = parseFloat(g.currentAmount) / parseFloat(g.targetAmount) * 100;
        return `  - ${g.title}: \u20B9${parseFloat(g.currentAmount).toLocaleString("en-IN")} / \u20B9${parseFloat(g.targetAmount).toLocaleString("en-IN")} (${progress.toFixed(0)}%)`;
      }).join("\n") || "  No active goals";
      const systemMessage = {
        role: "system",
        content: `You are SmartFinance.AI, a helpful personal finance assistant for Indian users. Analyze the user's actual financial data and provide clear, actionable advice using Indian Rupees (\u20B9).

IMPORTANT FORMATTING RULES:
- ALWAYS use \u20B9 (Indian Rupee) symbol for all amounts
- NEVER use asterisks (*) for bold or emphasis
- NEVER use markdown formatting symbols
- Use simple bullet points with dashes (-)
- Use plain text only
- Use line breaks for clarity
- Use emojis sparingly (\u{1F4B0} \u{1F4CA} \u2705 \u26A0\uFE0F \u{1F4A1})

USER'S FINANCIAL DATA:

Summary:
  Total Income: \u20B9${totalIncome.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
  Total Expenses: \u20B9${totalExpenses.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
  Net Balance: \u20B9${(totalIncome - totalExpenses).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
  
Monthly Comparison:
  Current Month Spending: \u20B9${currentMonthExpenses.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
  Last Month Spending: \u20B9${lastMonthExpenses.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
  Change: ${currentMonthExpenses > lastMonthExpenses ? "+" : ""}\u20B9${Math.abs(currentMonthExpenses - lastMonthExpenses).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}

Spending by Category:
${categoryBreakdown}

Active Budgets: ${budgets2.length}
Savings Goals: ${goals2.length}

Goals Progress:
${goalsInfo}

Upcoming Bills: ${bills2.filter((b) => new Date(b.dueDate) >= /* @__PURE__ */ new Date()).length}
${upcomingBills}

Recent Transactions (last 10):
${recentTransactions}

HOW TO RESPOND:
1. Answer questions using the actual data above
2. Be specific - use real numbers from their transactions
3. Always use \u20B9 symbol for amounts
4. Structure responses with clear sections (use line breaks)
5. Keep it conversational and easy to understand
6. Provide actionable tips based on their spending patterns
7. NO markdown symbols - plain text only
8. Reference their actual budgets, goals, and bills when relevant

Example good response format:

Your Spending This Month \u{1F4CA}

You spent \u20B945,230 this month across these categories:
- Food: \u20B912,500
- Transportation: \u20B98,000
- Entertainment: \u20B95,000

Compared to last month, you're spending \u20B93,200 more.

Here's my recommendation \u{1F4A1}
- Your food spending is high. Try meal planning to save \u20B92,000-3,000 monthly.
- Consider budgeting \u20B910,000 for food next month.

Remember: Be helpful, specific, and use their actual data!`
      };
      const completion = await openai.chat.completions.create({
        model: "gpt-4o-mini",
        messages: [systemMessage, ...messages],
        temperature: 0.7,
        max_tokens: 500
      });
      res.json({
        message: completion.choices[0].message.content
      });
    } catch (error) {
      console.error("OpenAI API error:", error);
      res.status(500).json({ message: "Failed to get AI response" });
    }
  });
  const httpServer = createServer(app2);
  return httpServer;
}

// server/vite.ts
import express from "express";
import fs from "fs";
import path2 from "path";
import { createServer as createViteServer, createLogger } from "vite";

// vite.config.ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";
import runtimeErrorOverlay from "@replit/vite-plugin-runtime-error-modal";
var vite_config_default = defineConfig({
  plugins: [
    react(),
    runtimeErrorOverlay(),
    ...process.env.NODE_ENV !== "production" && process.env.REPL_ID !== void 0 ? [
      await import("@replit/vite-plugin-cartographer").then(
        (m) => m.cartographer()
      ),
      await import("@replit/vite-plugin-dev-banner").then(
        (m) => m.devBanner()
      )
    ] : []
  ],
  resolve: {
    alias: {
      "@": path.resolve(import.meta.dirname, "client", "src"),
      "@shared": path.resolve(import.meta.dirname, "shared"),
      "@assets": path.resolve(import.meta.dirname, "attached_assets")
    }
  },
  root: path.resolve(import.meta.dirname, "client"),
  build: {
    outDir: path.resolve(import.meta.dirname, "dist/public"),
    emptyOutDir: true
  },
  server: {
    fs: {
      strict: true,
      deny: ["**/.*"]
    }
  }
});

// server/vite.ts
import { nanoid } from "nanoid";
var viteLogger = createLogger();
function log(message, source = "express") {
  const formattedTime = (/* @__PURE__ */ new Date()).toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
    hour12: true
  });
  console.log(`${formattedTime} [${source}] ${message}`);
}
async function setupVite(app2, server) {
  const serverOptions = {
    middlewareMode: true,
    hmr: { server },
    allowedHosts: true
  };
  const vite = await createViteServer({
    ...vite_config_default,
    configFile: false,
    customLogger: {
      ...viteLogger,
      error: (msg, options) => {
        viteLogger.error(msg, options);
        process.exit(1);
      }
    },
    server: serverOptions,
    appType: "custom"
  });
  app2.use(vite.middlewares);
  app2.use("*", async (req, res, next) => {
    const url = req.originalUrl;
    try {
      const clientTemplate = path2.resolve(
        import.meta.dirname,
        "..",
        "client",
        "index.html"
      );
      let template = await fs.promises.readFile(clientTemplate, "utf-8");
      template = template.replace(
        `src="/src/main.tsx"`,
        `src="/src/main.tsx?v=${nanoid()}"`
      );
      const page = await vite.transformIndexHtml(url, template);
      res.status(200).set({ "Content-Type": "text/html" }).end(page);
    } catch (e) {
      vite.ssrFixStacktrace(e);
      next(e);
    }
  });
}
function serveStatic(app2) {
  const distPath = path2.resolve(import.meta.dirname, "public");
  if (!fs.existsSync(distPath)) {
    throw new Error(
      `Could not find the build directory: ${distPath}, make sure to build the client first`
    );
  }
  app2.use(express.static(distPath));
  app2.use("*", (_req, res) => {
    res.sendFile(path2.resolve(distPath, "index.html"));
  });
}

// server/index.ts
var app = express2();
app.use(express2.json({
  verify: (req, _res, buf) => {
    req.rawBody = buf;
  }
}));
app.use(express2.urlencoded({ extended: false }));
app.use((req, res, next) => {
  const start = Date.now();
  const path3 = req.path;
  let capturedJsonResponse = void 0;
  const originalResJson = res.json;
  res.json = function(bodyJson, ...args) {
    capturedJsonResponse = bodyJson;
    return originalResJson.apply(res, [bodyJson, ...args]);
  };
  res.on("finish", () => {
    const duration = Date.now() - start;
    if (path3.startsWith("/api")) {
      let logLine = `${req.method} ${path3} ${res.statusCode} in ${duration}ms`;
      if (capturedJsonResponse) {
        logLine += ` :: ${JSON.stringify(capturedJsonResponse)}`;
      }
      if (logLine.length > 80) {
        logLine = logLine.slice(0, 79) + "\u2026";
      }
      log(logLine);
    }
  });
  next();
});
(async () => {
  const server = await registerRoutes(app);
  app.use((err, _req, res, _next) => {
    const status = err.status || err.statusCode || 500;
    const message = err.message || "Internal Server Error";
    res.status(status).json({ message });
    throw err;
  });
  if (app.get("env") === "development") {
    await setupVite(app, server);
  } else {
    serveStatic(app);
  }
  const port = parseInt(process.env.PORT || "5000", 10);
  server.listen({
    port,
    host: "0.0.0.0",
    reusePort: true
  }, () => {
    log(`serving on port ${port}`);
  });
})();
