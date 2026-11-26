"""
Interactive CLI Tester for Vani Chatbot
Test Kannada/Kanglish text commands, intent extraction, guardrails, and responses in terminal.
"""
import asyncio
import sys

# Ensure UTF-8 support on Windows terminals for Kannada characters
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stdin, 'reconfigure'):
    sys.stdin.reconfigure(encoding='utf-8')

from backend.services.bot_service import bot_service
from backend.models import BotMessageRequest
from backend.database import db

async def interactive_test():
    print("=" * 65)
    print("  Vani (ವಾಣಿ) - Standalone Chatbot CLI Tester")
    print("  Test voice, text, Kanglish intents & guardrails independently")
    print("=" * 65)
    print("\nQuick Test Examples:")
    print("  1. 'Bellulli rate 80 maadi'        (Price update)")
    print("  2. 'Akki stock mugidide'           (Stock out update)")
    print("  3. 'Order ORD-101 packed maadi'    (Order status update)")
    print("  4. 'Ivattina vyapara eshtu?'       (Sales summary query)")
    print("  5. 'Mysore Pak 500g 220 rs ge add' (Add product)")
    print("  6. 'Neenu yaaru?'                  (Identity guardrail)")
    print("  7. 'Who won the cricket match?'    (Out-of-context guardrail)")
    print("  8. 'Bele maadi'                    (Missing details clarification)")
    print("\nType 'exit' or 'quit' to stop.\n")

    while True:
        try:
            user_input = input("\n[Enter Kannada/Kanglish Command] > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting tester.")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "q"):
            print("Done testing.")
            break

        req = BotMessageRequest(
            inputType="text",
            text=user_input
        )
        
        print("\n⏳ Processing with Chatbot Service...")
        res = await bot_service.process_message(req)

        print("-" * 50)
        print(f"🎯 Detected Intent  : {res.intent}")
        print(f"💬 Bot Kannada Reply: {res.replyKn}")
        print(f"🔄 Needs DB Refresh : {res.refreshRequired}")
        if res.updatedEntity:
            print(f"📦 Entity Data      : {res.updatedEntity}")
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(interactive_test())
