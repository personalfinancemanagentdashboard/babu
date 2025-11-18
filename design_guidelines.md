# SmartFinance.AI Design Guidelines

## Design Approach

**Selected Approach**: Reference-Based + Design System Hybrid

**Primary References**: 
- Linear (clean, modern dashboard aesthetics)
- Stripe (data clarity and trust)
- Notion (information hierarchy)
- Mercury (fintech polish)

**Core Principles**:
- Data clarity over decoration
- Scannable information hierarchy
- Trust through professionalism
- Calm, focused user experience

---

## Typography

**Font Stack**: 
- Primary: Inter (UI, data, buttons)
- Monospace: JetBrains Mono (numbers, currency values)

**Hierarchy**:
- Page Titles: text-4xl font-bold (Dashboard, Transactions)
- Section Headers: text-2xl font-semibold (Monthly Overview, Recent Activity)
- Card Titles: text-lg font-semibold
- Body Text: text-base font-normal
- Data Labels: text-sm font-medium text-muted-foreground
- Currency/Numbers: font-mono text-2xl font-bold (for prominent values)
- Small Meta: text-xs font-normal text-muted-foreground

---

## Layout System

**Spacing Primitives**: Use Tailwind units of 4, 6, 8, 12, 16 (e.g., p-4, gap-6, mb-8, py-12, mt-16)

**Grid System**:
- Dashboard: 3-column grid on desktop (lg:grid-cols-3), 1-column mobile
- Metrics Cards: 2 or 4-column grid (md:grid-cols-2 lg:grid-cols-4)
- Transaction List: Single column with max-w-4xl
- Charts: 2-column on desktop (lg:grid-cols-2)

**Container Widths**:
- Main Content: max-w-7xl mx-auto px-6
- Forms/Modals: max-w-2xl
- Chat Interface: max-w-3xl

---

## Component Library

### Navigation
- **Sidebar** (desktop): Fixed left, w-64, full height with logo at top, main nav items with icons, user profile at bottom
- **Mobile Nav**: Bottom tab bar with 4-5 primary actions, or collapsible hamburger menu

### Dashboard Cards
- **Stat Cards**: Rounded corners (rounded-xl), shadow (shadow-sm), padding (p-6), white background
  - Icon in top-left (w-10 h-10)
  - Label above value
  - Large number display (font-mono text-3xl)
  - Percentage change indicator with up/down arrow
  
### Charts
- **Container**: Card wrapper with p-6, title with text-lg font-semibold mb-4
- **Chart Types**: Bar (monthly spending), Pie (category breakdown), Line (trends over time)
- **Legend**: Below chart, horizontal layout with dot indicators

### Transaction Components
- **Transaction Row**: Flex layout with icon, details (left), amount (right)
  - Category icon in circle (w-10 h-10 rounded-full)
  - Title + date stacked
  - Amount right-aligned (font-mono)
  - Separator border-b between rows
  
- **Add Transaction Form**: 
  - Single column layout
  - Input fields with labels above
  - Category dropdown with visual icons
  - Amount input with currency symbol prefix
  - Date picker
  - Primary action button at bottom

### Budgets & Goals
- **Budget Card**: 
  - Category name + icon
  - Spent/Total display (₹X / ₹Y)
  - Progress bar (h-2 rounded-full)
  - Alert badge when >80%

- **Goal Card**:
  - Goal title + target amount
  - Current savings amount
  - Circular or linear progress indicator
  - Time remaining text

### AI Chat Interface
- **Chat Container**: max-w-3xl, centered, full height flex column
- **Message Bubbles**: 
  - User: Right-aligned, rounded-2xl, p-4, max-w-[80%]
  - AI: Left-aligned, rounded-2xl, p-4, max-w-[80%]
- **Input Area**: Fixed bottom, flex with textarea + send button, backdrop blur

### Voice Assistant
- **Voice Button**: Large circular button (w-16 h-16) with microphone icon, pulsing animation when listening
- **Status Indicator**: Text below button showing "Listening...", "Processing...", "Ready"
- **Transcript Display**: Speech-to-text shown in real-time above button

### Buttons
- **Primary**: Solid fill, rounded-lg, px-6 py-3, font-medium
- **Secondary**: Border only, rounded-lg, px-6 py-3
- **Icon Buttons**: w-10 h-10, rounded-md, centered icon
- **Buttons on Images**: Backdrop blur effect (backdrop-blur-md), semi-transparent background

### Forms
- **Input Fields**: rounded-md, border, px-4 py-2.5, focus ring
- **Labels**: text-sm font-medium mb-2 block
- **Error States**: Red border, error text below (text-sm text-red-600)
- **Dropdowns**: Custom styled with chevron icon, matches input height

### Modals/Dialogs
- **Overlay**: Semi-transparent backdrop
- **Dialog**: Centered, max-w-md, rounded-xl, p-6, shadow-2xl
- **Header**: Title with close button (×) top-right
- **Footer**: Buttons right-aligned, gap-3

### Bills & Reminders
- **Bill Card**: Compact horizontal layout
  - Bill name + company icon left
  - Due date center
  - Amount right
  - Alert indicator (red dot) if due <5 days

---

## Animations

Use sparingly, only for:
- **Micro-interactions**: Button hover scale (scale-105), transition-transform
- **Page Transitions**: Fade-in on mount (fade-in 0.2s)
- **Voice Pulse**: Gentle pulsing animation for active listening state
- **Data Updates**: Brief highlight flash when numbers change

No elaborate scroll animations or complex transitions.

---

## Images

**Hero Image**: None - This is a data-focused dashboard, not a marketing page. Lead directly with functional dashboard upon login.

**Illustrations**:
- Empty states: Minimal line illustrations for "No transactions yet", "No goals set"
- Category icons: Use icon library (Heroicons) for food, transport, entertainment, etc.
- User avatar: Circle avatar (w-10 h-10 rounded-full) in nav/profile areas

**Charts**: Generated dynamically via Chart.js - no static images needed

---

## Responsive Behavior

- **Desktop (lg+)**: Sidebar navigation, multi-column grids, side-by-side chart layouts
- **Tablet (md)**: 2-column grids, collapsible sidebar
- **Mobile**: Single column, bottom tab navigation, full-width cards, stacked charts

Stack all multi-column layouts to single column below md breakpoint.