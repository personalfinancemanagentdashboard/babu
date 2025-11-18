# SmartFinance.AI - AI-Powered Personal Finance Dashboard

## Overview

SmartFinance.AI is a full-stack personal finance management application that helps users track expenses, manage budgets, set savings goals, and receive AI-powered financial insights. The application features voice interaction capabilities, comprehensive transaction management, and real-time financial health scoring.

**Core Purpose**: Provide users with an intelligent, interactive platform to manage their personal finances through modern UI, AI assistance, and voice commands.

**Key Features**:
- Transaction tracking with categorization (income/expense)
- Budget management and monitoring
- Savings goals with progress tracking
- Bill reminders and payment tracking
- AI-powered financial insights and chat assistance
- Voice command support for hands-free interaction
- Financial health score calculation
- Visual data analytics with charts and graphs

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture

**Framework**: React with TypeScript
- **UI Library**: shadcn/ui components built on Radix UI primitives
- **Styling**: Tailwind CSS with custom design system
- **State Management**: TanStack Query (React Query) for server state
- **Routing**: Wouter (lightweight client-side routing)
- **Build Tool**: Vite

**Design System**:
- **Typography**: Inter for UI/data, JetBrains Mono for currency/numbers
- **Theme**: Custom HSL-based color system with light/dark mode support
- **Layout**: Responsive grid system (mobile-first, 3-column desktop layouts)
- **Component Library**: Full shadcn/ui implementation with custom extensions
- **Design Philosophy**: Reference-based approach inspired by Linear, Stripe, Notion, and Mercury - prioritizing data clarity, scannable hierarchy, and professional trust

**Key Frontend Patterns**:
- Component-based architecture with reusable UI components
- Custom hooks for auth (`useAuth`), voice recognition (`useVoiceRecognition`), and toast notifications
- Separation of concerns: pages, components, lib utilities, and hooks
- Query-based data fetching with automatic caching and invalidation

### Backend Architecture

**Framework**: Express.js with TypeScript
- **Runtime**: Node.js
- **API Design**: RESTful endpoints with `/api` prefix
- **Session Management**: express-session with PostgreSQL store
- **Authentication**: Replit Auth (OpenID Connect/OAuth)

**API Structure**:
- `/api/auth/*` - Authentication endpoints (login, logout, user info)
- `/api/transactions` - Transaction CRUD operations
- `/api/budgets` - Budget management
- `/api/goals` - Savings goals tracking
- `/api/bills` - Bill reminders
- `/api/ai/chat` - AI assistant chat interface

**Middleware Stack**:
- JSON body parsing with raw body preservation
- URL-encoded form data support
- Request logging with duration tracking
- Session authentication middleware
- CORS handling via Replit Auth

**Error Handling**:
- Zod schema validation for request payloads
- HTTP status code-based error responses
- Centralized error handling with descriptive messages

### Data Storage

**Database**: PostgreSQL (via Neon serverless)
- **ORM**: Drizzle ORM for type-safe database operations
- **Migration Strategy**: Schema-first approach with drizzle-kit

**Schema Design**:

1. **Users Table**
   - Stores user profile from Replit Auth (email, name, profile image)
   - UUID primary key with automatic generation
   - Timestamps for creation and updates

2. **Transactions Table**
   - Core financial records with title, amount, category, type (income/expense), date
   - Foreign key to users with cascade delete
   - Decimal precision for monetary values (10,2)

3. **Budgets Table**
   - Category-based monthly budgets
   - Tracks allocated amount and month/year
   - User-specific with cascade delete

4. **Goals Table**
   - Savings targets with current progress
   - Includes target amount, current amount, deadline, and category
   - User-specific tracking

5. **Bills Table**
   - Recurring payment reminders
   - Due dates, amounts, and payment status
   - User-specific with cascade delete

6. **Sessions Table**
   - PostgreSQL-backed session store
   - Automatic expiration handling

**Data Access Patterns**:
- Repository pattern via storage interface (`IStorage`)
- Type-safe queries with Drizzle's query builder
- Automatic connection pooling with Neon serverless

### Authentication & Authorization

**Provider**: Replit Auth (OpenID Connect)
- OAuth 2.0 flow with PKCE
- JWT-based session tokens
- Automatic token refresh handling

**Session Management**:
- PostgreSQL-backed sessions via connect-pg-simple
- 7-day session TTL
- HTTP-only, secure cookies
- CSRF protection through session validation

**Authorization Pattern**:
- `isAuthenticated` middleware guards all protected routes
- User ID extraction from session claims
- Resource ownership validation (users can only access their own data)

### External Dependencies

**AI Integration**: OpenAI GPT API
- Chat completion endpoint for financial insights
- Conversation history maintained client-side
- Optional integration (gracefully degrades if API key not set)
- Error handling for rate limits and API failures

**Voice Recognition**: Web Speech API
- Browser-native speech-to-text (SpeechRecognition/webkitSpeechRecognition)
- Client-side voice command parsing
- Natural language processing for transaction commands
- Fallback UI when browser doesn't support API

**Charts & Visualization**: Recharts
- Bar charts for income vs. expenses
- Pie charts for category breakdown
- Responsive chart containers
- Custom tooltips with theme-aware styling

**UI Components**: Radix UI
- Accessible primitives for dialogs, dropdowns, tooltips, etc.
- Headless component architecture
- Full keyboard navigation support
- ARIA compliance built-in

**Database Hosting**: Neon (PostgreSQL)
- Serverless PostgreSQL with WebSocket support
- Automatic connection pooling
- Branch-based development workflows
- Environment variable-based connection (`DATABASE_URL`)

**Development Tools**:
- Replit-specific plugins for dev experience (error overlay, cartographer, dev banner)
- TypeScript for type safety across stack
- ESBuild for server bundling
- Vite for frontend development and production builds

**Deployment Considerations**:
- Environment variables: `DATABASE_URL`, `OPENAI_API_KEY`, `SESSION_SECRET`, `REPL_ID`, `ISSUER_URL`
- Build process: Vite for client, ESBuild for server
- Production mode detection via `NODE_ENV`
- Static file serving from `dist/public`