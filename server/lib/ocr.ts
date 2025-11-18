import OpenAI from "openai";
import { CATEGORIES } from "@shared/schema";

export interface OCRResult {
  title: string;
  amount: string;
  category: string;
  date: string;
  type: "income" | "expense";
}

export async function extractTransactionFromImage(
  imageBase64: string,
  openaiClient: OpenAI
): Promise<OCRResult> {
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
          content: systemPrompt,
        },
        {
          role: "user",
          content: [
            {
              type: "text",
              text: "Extract the transaction details from this receipt/bill image:",
            },
            {
              type: "image_url",
              image_url: {
                url: `data:image/jpeg;base64,${imageBase64}`,
              },
            },
          ],
        },
      ],
      max_tokens: 500,
      temperature: 0.2,
    });

    const content = response.choices[0]?.message?.content;
    if (!content) {
      throw new Error("No response from OpenAI");
    }

    const jsonMatch = content.match(/\{[\s\S]*\}/);
    if (!jsonMatch) {
      throw new Error("Could not parse JSON from response");
    }

    const result = JSON.parse(jsonMatch[0]) as OCRResult;

    if (!result.title || !result.amount || !result.category || !result.date || !result.type) {
      throw new Error("Incomplete transaction data extracted");
    }

    if (!CATEGORIES.includes(result.category as any)) {
      result.category = "Other";
    }

    if (!["income", "expense"].includes(result.type)) {
      result.type = "expense";
    }

    return result;
  } catch (error: any) {
    console.error("OCR extraction error:", error);
    throw new Error(`Failed to extract transaction from image: ${error.message}`);
  }
}
